from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from threading import RLock
from uuid import uuid4
import os

from app.schemas.optimization import (
    ExperimentOptimizationRun,
    OptimizationCandidatePlan,
    OptimizationEvent,
    OptimizationHumanDecision,
    OptimizationParameters,
    OptimizationResultSummary,
    OptimizationResponsePoint,
    OptimizationModelEvidence,
    OptimizationSearchMetric,
    OptimizationStage,
    OptimizationTrainingMetric,
)
from app.services.experiment_service import experiment_service
from app.services.product_requirement_registry import product_requirement_registry
from app.services.domain_run_store import SqliteDomainRunStore
from app.services.simulation_run_orchestrator import simulation_run_orchestrator
from app.model_registry.runtime import composite_prediction_service, feature_binding_service
from app.research.service import promoted_model_registry
from app.demo_models.service import demo_model_admission_service
from app.model_evaluation.agent import model_evaluation_agent


STAGES = (
    ("constraint-load", "constraintLoad", "模型与约束装载", "锁定父模型、正式仿真结果、特征绑定和训练范围。"),
    ("candidate-search", "candidateSearch", "多目标候选搜索", "在训练数据边界内计算产出、稳定性与成本目标。"),
    ("candidate-evaluation", "candidateEvaluation", "候选可靠性复核", "复核预测区间、外推状态、成本和设备可执行性。"),
    ("human-review", "humanReview", "人工验收", "由研发负责人决定是否生成正式工艺参数与预测结果版本。"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def synchronized(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return guarded


def durable(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        self.refresh()
        result = method(self, *args, **kwargs)
        if self._store:
            for run in self._runs.values(): self._store.save(run)
        return result
    return wrapped


class OptimizationConflictError(RuntimeError):
    pass


class OptimizationNotFoundError(LookupError):
    pass


class OptimizationOrchestrator:
    def __init__(self, store: SqliteDomainRunStore[ExperimentOptimizationRun] | None = None) -> None:
        self._runs: dict[str, ExperimentOptimizationRun] = {}
        self._run_ids_by_experiment: dict[str, list[str]] = {}
        self._lock = RLock()
        self._store = store
        self.refresh()

    def reset(self) -> None:
        """Reset the deterministic in-memory demo runtime between isolated tests."""
        with self._lock:
            self._runs.clear()
            self._run_ids_by_experiment.clear()
            if self._store: self._store.reset()

    def refresh(self) -> None:
        if not self._store: return
        with self._lock:
            for run in self._store.load_all():
                self._runs[run.runId] = run
                ids = self._run_ids_by_experiment.setdefault(run.experimentId, [])
                if run.runId not in ids:
                    ids.append(run.runId); ids.sort(key=lambda item: self._runs[item].version)

    def latest(self, experiment_id: str) -> ExperimentOptimizationRun:
        self.refresh()
        run_ids = self._run_ids_by_experiment.get(experiment_id, [])
        if run_ids:
            return self._runs[run_ids[-1]]
        return self._build(experiment_id, version=0, preview=True)

    def peek_latest(self, experiment_id: str) -> ExperimentOptimizationRun | None:
        self.refresh()
        run_ids = self._run_ids_by_experiment.get(experiment_id, [])
        return self._runs[run_ids[-1]].model_copy(deep=True) if run_ids else None

    def list_runs(self, experiment_id: str) -> list[ExperimentOptimizationRun]:
        self.refresh()
        return [
            self._runs[run_id].model_copy(deep=True)
            for run_id in self._run_ids_by_experiment.get(experiment_id, [])
        ]

    def get_run(self, experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
        return self._get(experiment_id, run_id).model_copy(deep=True)

    @durable
    def create(self, experiment_id: str) -> ExperimentOptimizationRun:
        allowed, reasons = self._admission(experiment_id)
        if not allowed:
            raise OptimizationConflictError("Optimization admission has not passed: " + "; ".join(reasons))
        with self._lock:
            run_ids = self._run_ids_by_experiment.setdefault(experiment_id, [])
            active = [self._runs[item] for item in run_ids if self._runs[item].status in {"draft", "running", "needsReview"}]
            if active:
                raise OptimizationConflictError(f"Active optimization run {active[-1].runId} already exists")
            run = self._build(experiment_id, version=len(run_ids) + 1, preview=False)
            self._runs[run.runId] = run
            run_ids.append(run.runId)
            experiment_service.mark_optimization_started(run)
        return run

    @durable
    @synchronized
    def restart_demo(self, experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
        overview = experiment_service.get_workspace_overview(experiment_id)
        if overview is None or getattr(overview, "sourceType", None) != "sample":
            raise OptimizationConflictError("Only isolated sample demonstrations can be restarted here")
        current = self._get(experiment_id, run_id)
        now = _now()
        if current.status in {"draft", "running", "needsReview"}:
            current.status = "stopped"
            if current.currentStageId:
                stage = next((item for item in current.retrainingStages if item.stageId == current.currentStageId), None)
                if stage and stage.status in {"running", "needsReview"}:
                    stage.status = "stopped"
                    stage.completedAt = now
        current.updatedAt = now
        current.events.append(self._event(
            "demoRestarted", current.currentStageId, "演示优化已重新开始",
            "旧运行已保留为审计记录；未写入正式模型、结果或设备控制通道。",
        ))
        run_ids = self._run_ids_by_experiment.setdefault(experiment_id, [])
        restarted = self._build(experiment_id, version=len(run_ids) + 1, preview=False)
        self._runs[restarted.runId] = restarted
        run_ids.append(restarted.runId)
        experiment_service.mark_optimization_started(restarted)
        return restarted

    @durable
    @synchronized
    def select(self, experiment_id: str, run_id: str, plan_id: str, parameters: OptimizationParameters) -> ExperimentOptimizationRun:
        run = self._get(experiment_id, run_id)
        if run.status != "draft":
            raise OptimizationConflictError("Only a draft optimization run can be edited")
        if plan_id not in {plan.planId for plan in run.candidatePlans}:
            raise OptimizationNotFoundError(plan_id)
        if run.searchMode == "promoted_model_constrained":
            self._predict_parameters(run, parameters)
        run.selectedPlanId = plan_id
        run.editedParameters = parameters
        run.updatedAt = _now()
        run.events.append(self._event("selectionUpdated", None, "候选方案与参数已更新", f"选择 {plan_id}；仍未写入正式实验版本。"))
        return run

    @durable
    @synchronized
    def submit(self, experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
        run = self._get(experiment_id, run_id)
        self._assert_admission(run)
        if run.status != "draft" or run.selectedPlanId is None or run.editedParameters is None:
            raise OptimizationConflictError("Select a candidate and valid parameters before formal submission")
        now = _now()
        run.status = "running"
        run.submittedParameters = run.editedParameters.model_copy(deep=True)
        overview = experiment_service.get_workspace_overview(experiment_id)
        demo = getattr(overview, "sourceType", None) == "sample"
        if run.searchMode == "promoted_model_constrained":
            run.submittedModelEvidence = self._predict_parameters(run, run.submittedParameters)
            run.trainingDataVersion = None
        else:
            prefix = "demo-dataset-opt" if demo else "dataset-opt"
            run.trainingDataVersion = f"{prefix}-{run.version}-{uuid4().hex[:6]}"
        first = run.retrainingStages[0]
        first.status = "running"
        first.progressPercent = 10
        first.startedAt = now
        run.currentStageId = first.stageId
        run.progressPercent = 5
        run.updatedAt = now
        run.events.append(self._event(
            "optimizationSubmitted", first.stageId, "演示优化任务已提交" if demo else "正式优化任务已提交",
            "已冻结候选参数并锁定父模型与绑定版本；本轮没有新增真实标签，不执行模型重训。"
            if run.searchMode == "promoted_model_constrained" else
            f"创建新训练数据版本 {run.trainingDataVersion}；父模型与父结果保持只读。",
        ))
        return run

    @durable
    @synchronized
    def advance(self, experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
        run = self._get(experiment_id, run_id)
        self._assert_admission(run)
        if run.status != "running" or run.currentStageId is None:
            raise OptimizationConflictError(f"Optimization run in {run.status} state cannot advance")
        index = next(i for i, stage in enumerate(run.retrainingStages) if stage.stageId == run.currentStageId)
        now = _now()
        current = run.retrainingStages[index]
        current.status = "completed"
        current.progressPercent = 100
        current.completedAt = now
        current.outputSummary = self._stage_outputs(index, run)
        run.events.append(self._event("stageCompleted", current.stageId, f"{current.stageName}已完成", "输出已写入优化运行审计记录。"))
        if current.stageId == "candidate-search" and run.searchMode == "rule_demo":
            run.trainingMetrics = [
                OptimizationTrainingMetric(round=round_id, trainingLoss=round(0.42 / round_id, 4), validationScore=round(0.72 + round_id * 0.025, 3), retained=round_id in {3, 4, 5})
                for round_id in range(1, 6)
            ]
        next_stage = run.retrainingStages[index + 1]
        next_stage.status = "needsReview" if next_stage.stageId == "human-review" else "running"
        next_stage.progressPercent = 0 if next_stage.status == "needsReview" else 8
        next_stage.startedAt = now
        run.currentStageId = next_stage.stageId
        run.status = "needsReview" if next_stage.status == "needsReview" else "running"
        run.progressPercent = [25, 55, 82][index]
        run.updatedAt = now
        run.events.append(self._event("stageStarted", next_stage.stageId, f"{next_stage.stageName}已进入", next_stage.detail))
        return run

    @durable
    @synchronized
    def review(self, experiment_id: str, run_id: str, decision: str, reason: str, operator: str, impact_scope: list[str]) -> ExperimentOptimizationRun:
        run = self._get(experiment_id, run_id)
        transaction_snapshot = run.model_copy(deep=True)
        self._assert_admission(run)
        overview = experiment_service.get_workspace_overview(experiment_id)
        if overview is None or overview.modelVersion != run.baseModelVersion:
            raise OptimizationConflictError("Parent model version changed; create a new optimization run")
        if overview.resultVersion != run.baseResultVersion:
            raise OptimizationConflictError("Parent result version changed; create a new optimization run")
        if run.status != "needsReview" or run.currentStageId != "human-review":
            raise OptimizationConflictError("Optimization run is not waiting for human review")
        now = _now()
        record = OptimizationHumanDecision(decisionId=f"opt-decision-{uuid4().hex[:8]}", decision=decision, reason=reason, operator=operator, impactScope=impact_scope, createdAt=now)
        run.humanDecisions.append(record)
        stage = run.retrainingStages[-1]
        stage.status = "completed" if decision == "approved" else "stopped"
        stage.progressPercent = 100
        stage.completedAt = now
        stage.outputSummary = [f"决策：{decision}", f"操作人：{operator}", f"理由：{reason}"]
        run.currentStageId = None
        run.status = "completed" if decision == "approved" else "stopped"
        run.progressPercent = 100 if decision == "approved" else run.progressPercent
        if decision == "approved":
            managed = run.searchMode == "promoted_model_constrained"
            demo = getattr(overview, "sourceType", None) == "sample"
            run.newModelVersion = None if managed or demo else f"model-012-v6-opt{run.version}"
            run.newResultVersion = (
                f"predicted-result-opt-v{run.version}-{uuid4().hex[:6]}"
                if managed else
                f"demo-predicted-result-v{run.version}-{uuid4().hex[:6]}"
                if demo else f"result-012-v{run.version + 5}"
            )
            run.officialParameterVersion = (
                f"process-parameters-v{run.version}-{uuid4().hex[:6]}" if managed else
                f"demo-process-parameters-v{run.version}-{uuid4().hex[:6]}" if demo else None
            )
            selected = next(plan for plan in run.candidatePlans if plan.planId == run.selectedPlanId)
            submitted = run.submittedParameters
            if submitted is None:
                raise OptimizationConflictError("Submitted parameters are missing")
            deviation = abs(submitted.temperatureC - selected.parameters.temperatureC) * 0.4 + abs(submitted.ph - selected.parameters.ph) * 3 + abs(submitted.cultureHours - selected.parameters.cultureHours) * 0.08 + abs(submitted.stirringRpm - selected.parameters.stirringRpm) * 0.01
            evaluated_score = max(0.0, selected.scoreBreakdown["overall"] - deviation)
            evidence = run.submittedModelEvidence
            predicted = evidence[0].prediction if evidence else None
            run.resultSummary = OptimizationResultSummary(
                confidenceScore=min(0.97, selected.confidenceScore + 0.03),
                predictedOutcomes=(
                    [
                        f"{evidence[0].targetField} 模型预测 {predicted:.6g}",
                        f"经验区间 {evidence[0].intervalLower:.6g}–{evidence[0].intervalUpper:.6g}",
                        f"批准参数：{submitted.temperatureC}℃ / pH {submitted.ph} / {submitted.cultureHours}小时 / {submitted.stirringRpm} rpm",
                        "模型版本保持不变；真实实验结果回流前不重训权重",
                    ] if evidence else []
                ) if managed else [
                    f"规则演示综合评分 {evaluated_score:.1f}/100" if demo else f"综合目标评分 {evaluated_score:.1f}/100",
                    f"评估参数：{submitted.temperatureC}℃ / pH {submitted.ph} / {submitted.cultureHours}小时 / {submitted.stirringRpm} rpm",
                    "隔离演示参数与结果版本已生成，不写入正式实验资产" if demo else "正式参数已生成新结果版本，仍需实际实验复核",
                ],
                riskItems=selected.riskItems,
                validationItems=selected.validationItems,
                disclaimer=(
                    "当前批准的是模型预测工艺参数版本，不是重训后的新模型，也不直接作为真实生产指令。"
                    if managed else
                    "隔离演示版本仅用于体验工艺决策流程，不是正式实验资产，也不直接作为真实生产指令。"
                    if demo else "新模型与结果版本仅作为研发实验建议，不直接作为真实生产指令。"
                ),
            )
            try:
                if managed:
                    experiment_service.promote_optimization_result(
                        experiment_id,
                        expected_model_version=run.baseModelVersion,
                        expected_result_version=run.baseResultVersion,
                        new_result_version=run.newResultVersion,
                        parameter_version=run.officialParameterVersion,
                        parameters=submitted.model_dump(mode="json"),
                        source_run_id=run.runId,
                    )
                elif not demo:
                    experiment_service.promote_versions(
                        experiment_id,
                        expected_model_version=run.baseModelVersion,
                        expected_result_version=run.baseResultVersion,
                        new_model_version=run.newModelVersion,
                        new_result_version=run.newResultVersion,
                        source_run_id=run.runId,
                    )
            except RuntimeError as exc:
                self._runs[run_id] = transaction_snapshot
                raise OptimizationConflictError(str(exc)) from exc
        run.updatedAt = now
        run.events.append(self._event("humanDecisionRecorded", "human-review", "人工验收决策已记录", f"{operator}：{reason}"))
        experiment_service.apply_optimization_review(run)
        return run

    def _build(self, experiment_id: str, version: int, preview: bool) -> ExperimentOptimizationRun:
        overview = experiment_service.get_workspace_overview(experiment_id)
        if overview is None:
            raise OptimizationNotFoundError(experiment_id)
        allowed, reasons = self._admission(experiment_id)
        requirement = product_requirement_registry.latest(experiment_id)
        managed = experiment_service.is_persisted_workspace(experiment_id) and getattr(overview, "sourceType", None) != "sample"
        demo = getattr(overview, "sourceType", None) == "sample"
        simulation = simulation_run_orchestrator.peek_latest(experiment_id) if managed or demo else None
        if managed and allowed:
            candidates, evaluation_count, search_metrics = self._model_candidates(experiment_id, simulation)
        elif managed:
            candidates, evaluation_count, search_metrics = [], 0, []
        else:
            candidates, evaluation_count, search_metrics = self._candidates(experiment_id, requirement), 0, []
        now = _now()
        return ExperimentOptimizationRun(
            runId=f"optimization-preview-{experiment_id}" if preview else f"optimization-run-{uuid4().hex[:10]}",
            experimentId=experiment_id,
            version=version,
            status="waiting" if preview else "draft",
            admissionAllowed=allowed,
            admissionReasons=reasons,
            baseModelVersion=overview.modelVersion,
            baseResultVersion=overview.resultVersion or "unavailable",
            baseSimulationRunId=simulation.runId if simulation else None,
            baseBindingVersions=list(simulation.bindingVersions) if simulation else [],
            searchMode="promoted_model_constrained" if managed else "rule_demo",
            searchEvaluations=evaluation_count,
            requirementDriven=requirement is not None,
            productRequirementVersionId=requirement.requirementVersionId if requirement else None,
            productRequirementVersion=requirement.version if requirement else None,
            productRequirementWorkingName=requirement.snapshot.workingName if requirement else None,
            productRequirementSourceRunId=requirement.sourceRunId if requirement else None,
            productRequirementContentHash=requirement.contentHash if requirement else None,
            candidatePlans=candidates,
            retrainingStages=[OptimizationStage(stageId=stage_id, stageKey=key, stageName=name, status="waiting", progressPercent=0, detail=detail, outputSummary=[]) for stage_id, key, name, detail in STAGES],
            progressPercent=0,
            trainingMetrics=[],
            searchMetrics=search_metrics,
            humanDecisions=[],
            events=[] if preview else [self._event("optimizationCreated", None, "工艺优化草案已创建", "三套候选方案已生成，尚未修改正式实验版本。")],
            createdAt=now,
            updatedAt=now,
            disclaimer=(
                "当前为已晋升模型约束下的工艺搜索；未新增真实实验标签，因此不会伪造模型重训。"
                "批准结果仍需小试或中试验证，不直接控制真实产线。"
                if managed else
                "当前为确定性规则工艺优化演示，所有输出仅作为研发实验建议。"
            ),
        )

    def _candidates(self, experiment_id: str, requirement=None) -> list[OptimizationCandidatePlan]:
        common_risks = ["优化结果尚未在扩大批次复测", "参数耦合关系需要实际实验验证"]
        validation = ["产物得率与活性", "批次稳定性", "单位产品能耗", "设备参数可执行性"]
        requirement_name = requirement.snapshot.workingName if requirement else None
        if requirement:
            validation = [
                *[f"需求指标：{metric.metricName}（{metric.targetDescription}）" for metric in requirement.snapshot.targetMetrics[:4]],
                *validation,
            ]
            common_risks = [*requirement.snapshot.risks[:2], *common_risks]
        specs = (
            ("candidate-balanced", "balanced", "综合平衡方案", 36.8, 6.82, 46, 195, 88.2, 0.91),
            ("candidate-yield", "yieldPriority", "产出优先方案", 37.4, 6.70, 52, 230, 91.6, 0.86),
            ("candidate-energy", "energySaving", "低能耗方案", 35.9, 6.95, 40, 165, 84.9, 0.88),
        )
        return [OptimizationCandidatePlan(
            planId=plan_id,
            strategyKey=strategy,
            displayName=name,
            summary=(
                f"面向产品需求“{requirement_name}”与 {strategy} 目标的规则代理多目标方案，"
                f"冻结引用 {requirement.requirementVersionId}。"
                if requirement else
                f"面向 {strategy} 目标的多目标约束方案，基于实验 {experiment_id} 的父模型生成。"
            ),
            parameters=OptimizationParameters(temperatureC=temp, ph=ph, cultureHours=hours, stirringRpm=rpm),
            scoreBreakdown={"overall": score, "yield": score + (3 if strategy == "yieldPriority" else 0), "stability": score - 2, "cost": score + (4 if strategy == "energySaving" else -1)},
            confidenceScore=confidence,
            predictionIntervals=[f"综合评分 95% 区间：{score - 4.2:.1f}–{score + 3.6:.1f}", "产出改善区间：+4.0%–+11.5%"],
            riskItems=list(common_risks),
            validationItems=list(validation),
            explanation=["使用父模型响应面筛选可行窗口", "同时约束产出、稳定性、成本与设备边界", "结果未经过真实产线验证"],
            responseSurface=[OptimizationResponsePoint(temperatureC=round(temp + dt, 1), ph=round(ph + dp, 2), predictedScore=max(0, round(score - abs(dt) * 1.6 - abs(dp) * 8, 1))) for dt, dp in ((-1.0, 0), (-0.5, -0.1), (0, 0), (0.5, 0.1), (1.0, 0))],
            baselineImprovements={"overall": round(score - 78.0, 1), "yield": round(score - 75.0 + (3 if strategy == "yieldPriority" else 0), 1), "energy": round(12.0 if strategy == "energySaving" else 4.0, 1)},
        ) for plan_id, strategy, name, temp, ph, hours, rpm, score, confidence in specs]

    def _model_candidates(self, experiment_id: str, simulation) -> tuple[list[OptimizationCandidatePlan], int, list[OptimizationSearchMetric]]:
        if simulation is None or simulation.status != "completed" or simulation.officialResult is None:
            raise OptimizationConflictError("A completed official digital experiment is required")
        report = model_evaluation_agent.assert_simulation_ready(experiment_id)
        records = promoted_model_registry.latest_per_target(experiment_id)
        if not records:
            raise OptimizationConflictError("No promoted model is available for constrained search")
        record = records[0]
        binding = feature_binding_service.store.latest(experiment_id, record.modelVersion)
        if binding is None:
            raise OptimizationConflictError("Confirmed model feature binding is required")
        base = simulation.officialParameters
        base_parameters = OptimizationParameters(
            temperatureC=base.temperatureC, ph=base.ph,
            cultureHours=base.cultureHours, stirringRpm=base.stirringRpm,
        )
        parameter_ranges: dict[str, tuple[float, float]] = {}
        for entry in binding.entries:
            feature_range = record.featureRanges.get(entry.modelFeature)
            if feature_range is None or entry.scale == 0:
                continue
            low = (feature_range.min - entry.offset) / entry.scale
            high = (feature_range.max - entry.offset) / entry.scale
            parameter_ranges[entry.simulationParameter] = (min(low, high), max(low, high))
        axes = {
            "temperatureC": self._axis(parameter_ranges.get("temperatureC"), base_parameters.temperatureC, .1),
            "ph": self._axis(parameter_ranges.get("ph"), base_parameters.ph, .01),
            "stirringRpm": self._axis(parameter_ranges.get("stirringRpm"), base_parameters.stirringRpm, 1),
        }
        evaluated: list[dict] = []
        for temperature in axes["temperatureC"]:
            for ph_value in axes["ph"]:
                for rpm in axes["stirringRpm"]:
                    params = OptimizationParameters(
                        temperatureC=temperature, ph=ph_value,
                        cultureHours=base_parameters.cultureHours, stirringRpm=rpm,
                    )
                    evidence = self._predict_raw(experiment_id, base, params)
                    self._apply_reliability_interval(evidence, report.predictionInterval.margin)
                    if not evidence or any(item.extrapolated for item in evidence):
                        continue
                    prediction = evidence[0].prediction
                    cost = self._cost_index(params)
                    stability = self._stability_index(params, parameter_ranges)
                    evaluated.append({
                        "parameters": params, "evidence": evidence,
                        "prediction": prediction, "cost": cost, "stability": stability,
                    })
        if len(evaluated) < 3:
            raise OptimizationConflictError("Fewer than three feasible in-range process candidates were found")
        values = [item["prediction"] for item in evaluated]
        lower, upper = min(values), max(values)
        span = max(upper - lower, 1e-12)
        for item in evaluated:
            item["yieldScore"] = (item["prediction"] - lower) / span
            item["objectives"] = {
                "balanced": .60 * item["yieldScore"] + .25 * item["stability"] + .15 * (1 - item["cost"]),
                "yieldPriority": item["yieldScore"],
                "energySaving": .55 * item["yieldScore"] + .45 * (1 - item["cost"]),
            }
        definitions = (
            ("yieldPriority", "产出优先方案", "在训练范围内优先提高模型目标预测"),
            ("balanced", "综合平衡方案", "兼顾模型目标、边界稳健性与资源成本"),
            ("energySaving", "低能耗方案", "在保留目标表现的同时降低温控、时长与搅拌成本"),
        )
        selected: list[dict] = []; used: set[str] = set(); plans: list[OptimizationCandidatePlan] = []
        metrics: list[OptimizationSearchMetric] = []
        baseline_evidence = self._predict_raw(experiment_id, base, base_parameters)
        self._apply_reliability_interval(baseline_evidence, report.predictionInterval.margin)
        baseline_prediction = baseline_evidence[0].prediction
        baseline_cost = self._cost_index(base_parameters)
        for strategy, name, summary in definitions:
            ranked = sorted(evaluated, key=lambda item: item["objectives"][strategy], reverse=True)
            choice = next(item for item in ranked if item["parameters"].model_dump_json() not in used)
            used.add(choice["parameters"].model_dump_json()); selected.append(choice)
            objective = choice["objectives"][strategy]
            evidence = choice["evidence"]
            score = objective * 100
            response = sorted(evaluated, key=lambda item: abs(item["parameters"].stirringRpm - choice["parameters"].stirringRpm))[:9]
            plans.append(OptimizationCandidatePlan(
                planId=f"candidate-{strategy}", strategyKey=strategy, displayName=name,
                summary=summary,
                parameters=choice["parameters"],
                scoreBreakdown={
                    "overall": round(score, 2), "target": round(choice["yieldScore"] * 100, 2),
                    "stability": round(choice["stability"] * 100, 2),
                    "cost": round((1 - choice["cost"]) * 100, 2),
                },
                confidenceScore=round(report.reliabilityScore * (.85 + .15 * choice["stability"]), 6),
                predictionIntervals=[
                    f"{evidence[0].targetField} 经验区间：{evidence[0].intervalLower:.6g}–{evidence[0].intervalUpper:.6g}"
                ],
                riskItems=["候选来自已训练数据范围内的模型搜索，仍可能受未观测变量影响", "批准后必须通过真实小试或中试验证"],
                validationItems=[evidence[0].targetField, "批次稳定性", "单位产品能耗", "设备参数可执行性"],
                explanation=[
                    f"共评估 {len(evaluated)} 个训练范围内组合",
                    f"使用模型 {evidence[0].modelVersion} 与绑定 {evidence[0].bindingVersion}",
                    "没有新增真实实验标签，因此本步骤不重训模型权重",
                ],
                responseSurface=[OptimizationResponsePoint(
                    temperatureC=item["parameters"].temperatureC,
                    ph=item["parameters"].ph,
                    predictedScore=round(item["yieldScore"] * 100, 2),
                    predictedValue=item["prediction"],
                ) for item in response],
                baselineImprovements={
                    "prediction": round(choice["prediction"] - baseline_prediction, 6),
                    "energy": round((baseline_cost - choice["cost"]) * 100, 2),
                    "objective": round(score - 50, 2),
                },
                modelEvidence=evidence, objectiveScore=round(objective, 6),
                costIndex=round(choice["cost"], 6), searchRank=1,
            ))
            metrics.append(OptimizationSearchMetric(
                strategyKey=strategy, evaluatedCount=len(evaluated), feasibleCount=len(evaluated),
                bestObjective=round(objective, 6), bestPrediction=choice["prediction"],
            ))
        display_order = {"balanced": 0, "yieldPriority": 1, "energySaving": 2}
        plans.sort(key=lambda item: display_order[item.strategyKey])
        metrics.sort(key=lambda item: display_order.get(item.strategyKey, 99))
        return plans, len(evaluated), metrics

    @staticmethod
    def _axis(value_range: tuple[float, float] | None, baseline: float, step: float) -> list[float]:
        if value_range is None:
            return [baseline]
        low, high = value_range
        middle = (low + high) / 2
        digits = 2 if step == .01 else 1 if step == .1 else 0
        return sorted({round(low, digits), round(middle, digits), round(high, digits)})

    @staticmethod
    def _cost_index(parameters: OptimizationParameters) -> float:
        value = (
            .35 * max(0, parameters.temperatureC - 20) / 35
            + .25 * parameters.cultureHours / 168
            + .40 * parameters.stirringRpm / 600
        )
        return max(0.0, min(1.0, value))

    @staticmethod
    def _stability_index(parameters: OptimizationParameters, ranges: dict[str, tuple[float, float]]) -> float:
        values = []
        for key in ("temperatureC", "ph", "stirringRpm"):
            if key not in ranges:
                continue
            low, high = ranges[key]; span = max(high - low, 1e-12)
            values.append(abs(getattr(parameters, key) - (low + high) / 2) / (span / 2))
        return max(0.0, 1 - (sum(values) / len(values) if values else 0))

    def _predict_parameters(self, run: ExperimentOptimizationRun, parameters: OptimizationParameters) -> list[OptimizationModelEvidence]:
        simulation = simulation_run_orchestrator.peek_latest(run.experimentId)
        if simulation is None or simulation.officialResult is None:
            raise OptimizationConflictError("Official simulation lineage is missing")
        evidence = self._predict_raw(run.experimentId, simulation.officialParameters, parameters)
        report = model_evaluation_agent.assert_simulation_ready(run.experimentId)
        self._apply_reliability_interval(evidence, report.predictionInterval.margin)
        return evidence

    @staticmethod
    def _apply_reliability_interval(evidence: list[OptimizationModelEvidence], margin: float) -> None:
        for item in evidence:
            item.intervalLower = item.prediction - margin
            item.intervalUpper = item.prediction + margin
            item.intervalMethod = "empirical_holdout_absolute_error"

    @staticmethod
    def _predict_raw(experiment_id: str, base, parameters: OptimizationParameters) -> list[OptimizationModelEvidence]:
        payload = base.model_dump(mode="json")
        payload.update(parameters.model_dump(mode="json"))
        try:
            prediction = composite_prediction_service.predict(
                experiment_id, payload, allow_extrapolation=False,
            )
        except (LookupError, ValueError) as exc:
            raise OptimizationConflictError(str(exc)) from exc
        if not prediction.targets or prediction.unavailableTargets:
            raise OptimizationConflictError("Promoted model prediction is incomplete")
        return [OptimizationModelEvidence(
            targetField=item.targetField, prediction=item.prediction,
            intervalLower=item.interval.lower, intervalUpper=item.interval.upper,
            intervalMethod=item.interval.method, modelVersion=item.modelVersion,
            bindingVersion=item.bindingVersion, artifactFingerprint=item.artifactFingerprint,
            extrapolated=item.extrapolated, outOfRangeFeatures=item.outOfRangeFeatures,
        ) for item in prediction.targets]

    def _admission(self, experiment_id: str) -> tuple[bool, list[str]]:
        overview = experiment_service.get_workspace_overview(experiment_id)
        if overview is None:
            raise OptimizationNotFoundError(experiment_id)
        if getattr(overview, "sourceType", None) == "sample":
            try:
                admission = demo_model_admission_service.require_active(experiment_id)
            except ValueError as exc:
                return False, [str(exc)]
            simulation = simulation_run_orchestrator.peek_latest(experiment_id)
            if simulation is None or simulation.status != "completed" or simulation.officialResult is None:
                return False, ["必须先完成隔离演示仿真并生成演示结果"]
            if simulation.modelVersion != admission.demoModelVersion:
                return False, ["演示仿真引用的模型版本已经过期"]
            if overview.resultVersion != simulation.officialResult.snapshotId:
                return False, ["实验总览尚未引用当前演示仿真结果"]
            return True, ["隔离演示仿真血缘已锁定；优化结果不得用于真实产线控制"]
        if experiment_service.is_persisted_workspace(experiment_id):
            reasons: list[str] = []
            try:
                report = model_evaluation_agent.assert_simulation_ready(experiment_id)
            except (LookupError, ValueError) as exc:
                return False, [str(exc)]
            simulation = simulation_run_orchestrator.peek_latest(experiment_id)
            if simulation is None or simulation.status != "completed" or simulation.officialResult is None:
                reasons.append("必须先完成正式数字实验并生成正式结果")
            else:
                if simulation.modelVersion != report.modelVersion:
                    reasons.append("正式仿真模型与当前可靠性报告不一致")
                current_bindings = sorted({
                    binding.bindingVersion
                    for record in promoted_model_registry.latest_per_target(experiment_id)
                    if (binding := feature_binding_service.store.latest(experiment_id, record.modelVersion)) is not None
                })
                if simulation.bindingVersions != current_bindings:
                    reasons.append("正式仿真的特征绑定版本已经过期")
                if overview.resultVersion != simulation.officialResult.snapshotId:
                    reasons.append("实验总览尚未引用当前正式仿真结果")
            return not reasons, reasons or ["可靠性、模型、绑定和正式仿真结果均已锁定"]
        stage = next(item for item in overview.stages if item.stage == "optimization")
        allowed = stage.canEnter and overview.resultVersion is not None
        reasons = [] if allowed else [stage.detail, *(overview.validationItems if not stage.canEnter else ["缺少已验收的父结果版本"])]
        return allowed, reasons

    def _assert_admission(self, run: ExperimentOptimizationRun) -> None:
        allowed, reasons = self._admission(run.experimentId)
        run.admissionAllowed = allowed
        run.admissionReasons = reasons
        if not allowed:
            raise OptimizationConflictError("Optimization admission is no longer valid: " + "; ".join(reasons))

    def _get(self, experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
        self.refresh()
        run = self._runs.get(run_id)
        if run is None or run.experimentId != experiment_id:
            raise OptimizationNotFoundError(run_id)
        return run

    @staticmethod
    def _stage_outputs(index: int, run: ExperimentOptimizationRun) -> list[str]:
        if run.searchMode == "promoted_model_constrained":
            outputs = (
                [f"父模型 {run.baseModelVersion}", f"绑定版本：{'、'.join(run.baseBindingVersions)}", "父版本保持只读"],
                [f"完成 {run.searchEvaluations} 个可行组合计算", "形成综合、产出、低能耗三套候选"],
                ["预测区间与训练范围已复核", "未发生模型外推", "等待真实实验验证"],
            )
        else:
            outputs = (
                [run.trainingDataVersion or "待生成演示数据版本", "父数据版本保持只读"],
                ["完成 5 组规则代理参数扫描", "保留规则稳定度更高的候选"],
                ["规则代理稳定度 0.845", "具体风险和验证指标已重新计算", "未执行模型权重训练"],
            )
        return list(outputs[index])

    @staticmethod
    def _event(event_type: str, stage_id: str | None, title: str, detail: str) -> OptimizationEvent:
        return OptimizationEvent(eventId=f"opt-event-{uuid4().hex[:9]}", eventType=event_type, stageId=stage_id, title=title, detail=detail, createdAt=_now())


_domain_store_path = os.getenv("DOMAIN_RUN_STORE_PATH", "").strip()
optimization_orchestrator = OptimizationOrchestrator(
    SqliteDomainRunStore(_domain_store_path, "optimization", ExperimentOptimizationRun) if _domain_store_path else None
)
