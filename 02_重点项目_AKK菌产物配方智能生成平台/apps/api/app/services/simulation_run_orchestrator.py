from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from threading import RLock
from functools import wraps
import os

from app.schemas.simulation import (
    ExperimentSimulationRun,
    SimulationPredictRequest,
    SimulationRunEvent,
    SimulationRunStage,
    SimulationTrialSnapshot,
)
from app.services.experiment_service import experiment_service
from app.services.simulation_service import simulation_service
from app.services.domain_run_store import SqliteDomainRunStore
from app.model_evaluation.agent import model_evaluation_agent
from app.model_registry.runtime import (
    composite_prediction_service,
    feature_binding_service,
)
from app.research.service import promoted_model_registry
from app.demo_models.service import demo_model_admission_service


def durable(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        self.refresh()
        result = method(self, *args, **kwargs)
        if self._store:
            for run in self._runs.values(): self._store.save(run)
        return result
    return wrapped


STAGE_TEMPLATES = (
    ("model-validation", "modelValidation", "模型校验", "模型验证节点", ["模型版本与特征集", "仿真准入阈值"], ["R²、MAE 与数据完整度", "输入分布边界检查"], ["模型依赖校验报告"]),
    ("system-initialization", "systemInitialization", "系统初始化", "控制系统与传感器", ["设备能力模板", "初始仪器参数"], ["参数范围校验", "传感器状态 mock 校验"], ["虚拟设备状态快照"]),
    ("material-preparation", "materialPreparation", "原料/培养基准备", "原料罐与配料单元", ["碳源、浓度与批次", "培养基/基料配置"], ["物料衡算", "投料顺序规则"], ["原料准备状态"]),
    ("core-production", "coreProduction", "核心生产过程", "生物反应/加工设备", ["温度、pH、搅拌与时长", "厌氧水平"], ["规则模型 + 回归预测", "时间步长 10 分钟"], ["过程曲线与中间产物预测"]),
    ("downstream-processing", "downstreamProcessing", "分离/下游处理", "分离与稳定化设备", ["核心过程输出", "压力与预处理参数"], ["收率修正规则", "稳定性窗口检查"], ["下游收率与损失估计"]),
    ("product-collection", "productCollection", "产物收集", "收集罐与包装单元", ["下游产物流", "收集目标"], ["质量守恒检查", "批次聚合"], ["产物数量与质量摘要"]),
    ("result-evaluation", "resultEvaluation", "结果评估", "评估与报告节点", ["全流程事件与预测", "验证指标"], ["置信度聚合", "风险与验证建议生成"], ["研发实验建议快照"]),
)

EXPERIMENT_LINE_TEMPLATES = {
    "exp-akk-018": ("anaerobic-fermentation", (("模型校验", "模型验证节点"), ("厌氧系统初始化", "厌氧控制与传感器"), ("培养基准备", "培养基与接种单元"), ("厌氧发酵过程", "生物反应器"), ("灭活与稳定化", "下游稳定化设备"), ("冻干粉收集", "收集与冻干单元"), ("结果评估", "评估与报告节点"))),
    "exp-algae-017": ("algae-co-culture", (("模型校验", "模型验证节点"), ("光生物系统初始化", "光照与气体控制系统"), ("藻液/培养基准备", "藻液与接种单元"), ("菌藻共培养", "光生物反应器"), ("生物质分离", "膜分离与离心单元"), ("生物质收集", "收集与浓缩单元"), ("结果评估", "评估与报告节点"))),
    "exp-food-012": ("functional-food-processing", (("模型校验", "模型验证节点"), ("加工系统初始化", "混配与温控系统"), ("食品原料准备", "配料与均质单元"), ("核心加工过程", "混合/成型设备"), ("稳定化处理", "冷却与质构控制单元"), ("产品收集", "包装与取样单元"), ("结果评估", "稳定性评估节点"))),
    "exp-culture-009": ("high-density-culture", (("模型校验", "模型验证节点"), ("培养系统初始化", "培养控制与传感器"), ("培养基/种子液准备", "培养基与接种单元"), ("高密度培养", "生物反应器"), ("菌体分离", "离心与洗涤单元"), ("菌体收集", "收集与计量单元"), ("结果评估", "评估与报告节点"))),
}

GENERIC_STAGE_OVERRIDES = (
    ("模型可靠性校验", "模型评估与准入节点"),
    ("仿真系统初始化", "虚拟控制器与传感器"),
    ("原料与培养基准备", "虚拟配料单元"),
    ("核心生产过程", "虚拟生产反应器"),
    ("下游处理", "虚拟分离与稳定化单元"),
    ("产物收集", "虚拟收集与计量单元"),
    ("结果评估", "可靠性与研发报告节点"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


PARAMETER_TEMPLATES = {
    "exp-akk-018": dict(targetProduct="AKK 后生元冻干粉", productFormat="postbiotic-powder", carbonSource="BFP", carbonConcentration=2.0, cultureHours=60, temperatureC=37.0, ph=6.8, anaerobicScore=0.92, pressureMpa=120, stirringRpm=150, pretreated=True),
    "exp-algae-017": dict(targetProduct="菌藻共培养生物质", productFormat="culture-medium", carbonSource="lambdaCarrageenan", carbonConcentration=1.5, cultureHours=72, temperatureC=35.0, ph=7.0, anaerobicScore=0.75, pressureMpa=60, stirringRpm=120, pretreated=True),
    "exp-food-012": dict(targetProduct="功能食品稳定基料", productFormat="fish-ball", carbonSource="UBFP", carbonConcentration=0.8, cultureHours=24, temperatureC=37.0, ph=6.8, anaerobicScore=0.78, pressureMpa=80, stirringRpm=180, pretreated=True),
    "exp-culture-009": dict(targetProduct="高密度培养预实验", productFormat="culture-medium", carbonSource="BFP", carbonConcentration=1.0, cultureHours=48, temperatureC=37.0, ph=6.8, anaerobicScore=0.90, pressureMpa=40, stirringRpm=130, pretreated=False),
}


def _default_parameters(experiment_id: str) -> SimulationPredictRequest:
    template = PARAMETER_TEMPLATES.get(experiment_id)
    if template is None:
        overview = experiment_service.get_workspace_overview(experiment_id)
        target_product = overview.targetProduct if overview else "实验目标产物"
        template = dict(
            targetProduct=target_product,
            productFormat="culture-medium",
            carbonSource="BFP",
            carbonConcentration=1.0,
            cultureHours=48,
            temperatureC=37.0,
            ph=6.9,
            anaerobicScore=0.85,
            pressureMpa=50,
            stirringRpm=180,
            pretreated=False,
        )
    approved = experiment_service.get_official_process_parameters(experiment_id)
    if approved:
        template = {**template, **approved}
    return SimulationPredictRequest(**template, useLlmAdvisor=False)


class SimulationRunConflictError(RuntimeError):
    pass


class SimulationRunNotFoundError(LookupError):
    pass


class SimulationRunOrchestrator:
    def __init__(self, store: SqliteDomainRunStore[ExperimentSimulationRun] | None = None) -> None:
        self._runs: dict[str, ExperimentSimulationRun] = {}
        self._run_ids_by_experiment: dict[str, list[str]] = {}
        self._create_lock = RLock()
        self._store = store
        self.refresh()

    def reset(self) -> None:
        with self._create_lock:
            self._runs.clear()
            self._run_ids_by_experiment.clear()
            if self._store: self._store.reset()

    def refresh(self) -> None:
        if not self._store: return
        with self._create_lock:
            for run in self._store.load_all():
                self._runs[run.runId] = run
                ids = self._run_ids_by_experiment.setdefault(run.experimentId, [])
                if run.runId not in ids:
                    ids.append(run.runId); ids.sort(key=lambda item: self._runs[item].version)

    def peek_latest(self, experiment_id: str) -> ExperimentSimulationRun | None:
        self.refresh()
        run_ids = self._run_ids_by_experiment.get(experiment_id, [])
        return self._runs[run_ids[-1]].model_copy(deep=True) if run_ids else None

    def list_runs(self, experiment_id: str) -> list[ExperimentSimulationRun]:
        self.refresh()
        return [
            self._runs[run_id].model_copy(deep=True)
            for run_id in self._run_ids_by_experiment.get(experiment_id, [])
        ]

    def latest(self, experiment_id: str) -> ExperimentSimulationRun:
        self.refresh()
        run_ids = self._run_ids_by_experiment.get(experiment_id, [])
        if run_ids:
            return self._runs[run_ids[-1]]
        return self._build_run(experiment_id, version=0, preview=True)

    @durable
    def create(self, experiment_id: str, parent_run_id: str | None = None) -> ExperimentSimulationRun:
        allowed, reasons, _, _, _ = self._admission(experiment_id)
        if not allowed:
            raise SimulationRunConflictError("Simulation admission has not passed: " + "; ".join(reasons))
        with self._create_lock:
            run_ids = self._run_ids_by_experiment.setdefault(experiment_id, [])
            self._assert_no_other_active_run(experiment_id)
            run = self._build_run(experiment_id, version=len(run_ids) + 1, preview=False, parent_run_id=parent_run_id)
            self._runs[run.runId] = run
            run_ids.append(run.runId)
            experiment_service.mark_simulation_started(run)
        return run

    @durable
    def advance(self, experiment_id: str, run_id: str) -> ExperimentSimulationRun:
        run = self._get(experiment_id, run_id)
        self._assert_current_admission(run)
        if run.status != "running" or run.currentStageId is None:
            raise SimulationRunConflictError(f"Simulation run in {run.status} state cannot advance")
        index = next(i for i, stage in enumerate(run.stages) if stage.stageId == run.currentStageId)
        now = _now()
        current = run.stages[index]
        current.status = "completed"
        current.progressPercent = 100
        current.completedAt = now
        current.outputSummary = list(STAGE_TEMPLATES[index][6])
        run.events.append(self._event("stageCompleted", current.stageId, f"{current.stageName}已完成", "本环节输出已写入仿真运行记录。"))
        if index == len(run.stages) - 1:
            run.status = "completed"
            run.currentStageId = None
            run.progressPercent = 100
            run.simulatedMinutes = 420
            run.estimatedRemainingMinutes = 0
            run.events.append(self._event("simulationCompleted", None, "仿真运行已完成", "七个环节均已完成，结果仅作为研发实验建议。"))
            run.officialResult = self._result_snapshot(run, run.officialParameters, official=True)
            experiment_service.apply_simulation_result(run)
        else:
            next_stage = run.stages[index + 1]
            next_stage.status = "running"
            next_stage.progressPercent = 8
            next_stage.waitingReason = None
            next_stage.startedAt = now
            run.currentStageId = next_stage.stageId
            run.progressPercent = round(((index + 1.1) / len(run.stages)) * 100)
            run.simulatedMinutes = (index + 1) * 60
            run.estimatedRemainingMinutes = (len(run.stages) - index - 1) * 60
            run.events.append(self._event("stageStarted", next_stage.stageId, f"{next_stage.stageName}已开始", "上游输出校验通过，当前环节开始计算。"))
        run.updatedAt = now
        return run

    @durable
    def stop(self, experiment_id: str, run_id: str) -> ExperimentSimulationRun:
        run = self._get(experiment_id, run_id)
        if run.status != "running":
            raise SimulationRunConflictError(f"Simulation run in {run.status} state cannot stop")
        active = next(stage for stage in run.stages if stage.stageId == run.currentStageId)
        active.status = "stopped"
        run.status = "stopped"
        run.updatedAt = _now()
        run.events.append(self._event("simulationStopped", active.stageId, "仿真已由用户终止", "当前运行与临时试算快照均保留。"))
        return run

    @durable
    def restart(self, experiment_id: str, run_id: str) -> ExperimentSimulationRun:
        run = self._get(experiment_id, run_id)
        if run.status != "stopped":
            raise SimulationRunConflictError("Only a stopped simulation run can restart")
        self._assert_current_admission(run)
        return self.create(experiment_id, parent_run_id=run_id)

    @durable
    def trial(self, experiment_id: str, run_id: str, parameters: SimulationPredictRequest) -> SimulationTrialSnapshot:
        run = self._get(experiment_id, run_id)
        self._assert_current_admission(run)
        if run.status == "stopped":
            raise SimulationRunConflictError("Current simulation run cannot accept a trial")
        snapshot = self._result_snapshot(run, parameters, official=False)
        run.trialSnapshots.append(snapshot)
        run.updatedAt = snapshot.createdAt
        run.events.append(self._event("trialSnapshotCreated", run.currentStageId, "临时试算快照已生成", f"快照 {snapshot.snapshotId}，未写回正式实验版本。"))
        return snapshot

    @durable
    def fail(self, experiment_id: str, run_id: str, reason: str, affected_versions: list[str]) -> ExperimentSimulationRun:
        run = self._get(experiment_id, run_id)
        if run.status != "running" or run.currentStageId is None:
            raise SimulationRunConflictError("Only a running simulation can enter failed state")
        active = next(stage for stage in run.stages if stage.stageId == run.currentStageId)
        active.status = "failed"
        active.waitingReason = reason
        run.status = "failed"
        run.failureReason = reason
        completed = [stage.stageId for stage in run.stages if stage.status == "completed"]
        run.lastSuccessfulStageId = completed[-1] if completed else None
        run.affectedVersions = affected_versions
        run.updatedAt = _now()
        run.events.append(self._event("simulationFailed", active.stageId, "仿真环节异常", f"{reason}；受影响版本：{'、'.join(affected_versions)}"))
        return run

    @durable
    def retry(self, experiment_id: str, run_id: str) -> ExperimentSimulationRun:
        run = self._get(experiment_id, run_id)
        self._assert_current_admission(run)
        with self._create_lock:
            if run.status != "failed" or run.currentStageId is None:
                raise SimulationRunConflictError("Only a failed simulation can retry")
            self._assert_no_other_active_run(experiment_id, exclude_run_id=run_id)
            active = next(stage for stage in run.stages if stage.stageId == run.currentStageId)
            active.status = "running"
            active.waitingReason = None
            run.status = "running"
            run.failureReason = None
            run.affectedVersions = []
            run.updatedAt = _now()
            run.events.append(self._event("simulationRetried", active.stageId, "异常环节已重试", "保留失败事件，从当前环节重新计算。"))
        return run

    def _build_run(self, experiment_id: str, version: int, preview: bool, parent_run_id: str | None = None) -> ExperimentSimulationRun:
        allowed, reasons, confidence, model_version, model_type = self._admission(experiment_id)
        managed_workspace = self._is_formal_workspace(experiment_id)
        now = _now()
        status = "waiting" if preview or not allowed else "running"
        line_template_id, stage_overrides = EXPERIMENT_LINE_TEMPLATES.get(
            experiment_id,
            ("generic-enterprise-process", GENERIC_STAGE_OVERRIDES),
        )
        stages = []
        for index, (stage_id, key, _, _, inputs, model_basis, outputs) in enumerate(STAGE_TEMPLATES):
            name, equipment = stage_overrides[index]
            is_running = status == "running" and index == 0
            stages.append(SimulationRunStage(
                stageId=stage_id,
                stageKey=key,
                stageName=name,
                equipmentName=equipment,
                status="running" if is_running else "waiting",
                progressPercent=10 if is_running else 0,
                waitingReason=None if is_running else ("等待模型准入" if not allowed else "等待上游环节完成"),
                inputSummary=inputs,
                modelBasis=model_basis,
                outputSummary=[],
                startedAt=now if is_running else None,
            ))
        run_id = f"simulation-preview-{experiment_id}" if preview else f"simulation-run-{uuid4().hex[:10]}"
        events = [] if preview else [self._event("simulationStarted", stages[0].stageId, "仿真运行已开始", "模型准入通过，进入模型校验环节。")]
        model_metrics = {"R²": "--", "MAE": "--", "可靠性评分": "--"}
        if self._is_formal_workspace(experiment_id):
            try:
                report = model_evaluation_agent.assert_simulation_ready(experiment_id)
                model_metrics = {
                    "R²": f"{report.performanceMetrics.get('r2', 0):.3f}",
                    "MAE": f"{report.performanceMetrics.get('mae', 0):.4f}",
                    "可靠性评分": f"{report.reliabilityScore * 100:.1f}%",
                }
            except (LookupError, ValueError):
                pass
        elif (overview := experiment_service.get_workspace_overview(experiment_id)) is not None and getattr(overview, "sourceType", None) == "sample":
            admission = demo_model_admission_service.latest(experiment_id)
            if admission is not None:
                model_metrics = {
                    "R²": f"{admission.metrics.get('r2', 0):.3f}",
                    "MAE": f"{admission.metrics.get('mae', 0):.4f}",
                    "演示可靠性": f"{admission.reliabilityScore * 100:.1f}%",
                }
        return ExperimentSimulationRun(
            runId=run_id,
            parentRunId=parent_run_id,
            experimentId=experiment_id,
            version=version,
            status=status,
            admissionAllowed=allowed,
            admissionReasons=reasons,
            reliabilityScore=confidence,
            modelVersion=model_version,
            bindingVersions=self._current_binding_versions(experiment_id),
            modelType=model_type,
            lineTemplateId=line_template_id,
            modelMetrics=model_metrics,
            progressPercent=3 if status == "running" else 0,
            simulatedMinutes=0,
            estimatedRemainingMinutes=420 if allowed else 0,
            currentStageId=stages[0].stageId if status == "running" else None,
            stages=stages,
            events=events,
            officialParameters=_default_parameters(experiment_id),
            trialSnapshots=[],
            createdAt=now,
            updatedAt=now,
            disclaimer=(
                "当前为已晋升模型驱动的数字实验，不向真实设备发送控制指令；"
                "预测区间尚未独立校准，所有输出仅作为研发实验建议。"
                if managed_workspace else
                "当前为确定性规则演示，不控制真实产线；所有输出仅作为研发实验建议。"
            ),
        )

    def _assert_current_admission(self, run: ExperimentSimulationRun) -> None:
        original_model_version = run.modelVersion
        original_binding_versions = list(run.bindingVersions)
        allowed, reasons, confidence, model_version, model_type = self._admission(run.experimentId)
        run.admissionAllowed = allowed
        run.admissionReasons = reasons
        run.reliabilityScore = confidence
        if not allowed:
            raise SimulationRunConflictError("Simulation admission is no longer valid: " + "; ".join(reasons))
        current_bindings = self._current_binding_versions(run.experimentId)
        if run.version > 0 and (
            original_model_version != model_version
            or original_binding_versions != current_bindings
        ):
            run.admissionAllowed = False
            run.admissionReasons = ["模型或特征绑定版本已变化，当前仿真必须新建版本后重新运行"]
            raise SimulationRunConflictError(run.admissionReasons[0])
        run.modelVersion = model_version
        run.modelType = model_type
        run.bindingVersions = current_bindings
        overview = experiment_service.get_workspace_overview(run.experimentId)
        if overview is not None and getattr(overview, "sourceType", None) == "sample":
            admission = demo_model_admission_service.require_active(run.experimentId)
            run.modelMetrics = {
                "R²": f"{admission.metrics.get('r2', 0):.3f}",
                "MAE": f"{admission.metrics.get('mae', 0):.4f}",
                "演示准入评分": f"{admission.reliabilityScore * 100:.1f}%",
            }
        experiment_service.mark_simulation_started(run)

    def _assert_no_other_active_run(self, experiment_id: str, exclude_run_id: str | None = None) -> None:
        active = [
            self._runs[run_id]
            for run_id in self._run_ids_by_experiment.get(experiment_id, [])
            if run_id != exclude_run_id and self._runs[run_id].status == "running"
        ]
        if active:
            raise SimulationRunConflictError(
                f"Active simulation run {active[-1].runId} already exists for this experiment"
            )

    def _result_snapshot(self, run: ExperimentSimulationRun, parameters: SimulationPredictRequest, official: bool) -> SimulationTrialSnapshot:
        result = simulation_service.predict(parameters)
        model_prediction = None
        if self._is_formal_workspace(run.experimentId):
            model_prediction = composite_prediction_service.predict(
                run.experimentId,
                parameters.model_dump(mode="json"),
                allow_extrapolation=False,
            )
            if not model_prediction.targets or model_prediction.unavailableTargets:
                details = "; ".join(
                    f"{target}: {model_prediction.unavailableReasons.get(target, '不可用')}"
                    for target in model_prediction.unavailableTargets
                )
                raise SimulationRunConflictError(
                    "Promoted model prediction is incomplete" + (f": {details}" if details else "")
                )
        differences = []
        for field, unit in (("temperatureC", "℃"), ("ph", ""), ("stirringRpm", "rpm"), ("cultureHours", "小时"), ("carbonConcentration", "g/L"), ("pressureMpa", "MPa")):
            old, new = getattr(run.officialParameters, field), getattr(parameters, field)
            if old != new:
                differences.append(f"{field}: {old}{unit} → {new}{unit}")
        risks = list(result.risks)
        validation_indicators = list(result.validationIndicators)
        if model_prediction:
            report = model_evaluation_agent.assert_simulation_ready(run.experimentId)
            margin = report.predictionInterval.margin
            for target in model_prediction.targets:
                target.interval.lower = target.prediction - margin
                target.interval.upper = target.prediction + margin
                target.interval.method = "empirical_holdout_absolute_error"
                target.interval.coverageClaim = "empirical_holdout"
            validation_indicators.insert(0, "正式模型目标：" + "、".join(item.targetField for item in model_prediction.targets))
            risks.extend(
                f"{item.targetField} 输入超出训练范围：{'、'.join(item.outOfRangeFeatures)}"
                for item in model_prediction.targets if item.extrapolated
            )
        return SimulationTrialSnapshot(
            snapshotId=f"{'official' if official else 'trial'}-{uuid4().hex[:10]}",
            runId=run.runId,
            createdAt=_now(),
            parameters=parameters,
            predictions=result.predictions,
            confidence=result.confidence,
            risks=risks,
            validationIndicators=validation_indicators,
            baselineDifferences=differences or (["正式仿真基线参数"] if official else ["与正式参数一致"]),
            disclaimer="正式仿真结果仍需实际实验验证，仅作为研发实验建议。" if official else "临时试算不会覆盖正式实验参数、模型版本或结果版本，仅作为研发实验建议。",
            predictionSource="promoted_model_composite" if model_prediction else "rule_model",
            modelTargets=model_prediction.targets if model_prediction else [],
            bindingVersions=sorted({item.bindingVersion for item in model_prediction.targets}) if model_prediction else [],
            unavailableTargets=model_prediction.unavailableTargets if model_prediction else [],
            extrapolated=any(item.extrapolated for item in model_prediction.targets) if model_prediction else False,
        )

    def _admission(self, experiment_id: str) -> tuple[bool, list[str], float | None, str, str]:
        overview = experiment_service.get_workspace_overview(experiment_id)
        if overview is None:
            raise SimulationRunNotFoundError(experiment_id)
        if getattr(overview, "sourceType", None) == "sample":
            try:
                admission = demo_model_admission_service.require_active(experiment_id)
                return (
                    True,
                    ["隔离演示模型已人工准入；不会写入企业正式模型注册表"],
                    admission.reliabilityScore,
                    admission.demoModelVersion,
                    f"隔离演示 · {admission.modelType}",
                )
            except ValueError as exc:
                return False, [str(exc)], None, overview.modelVersion, overview.modelType
        if experiment_service.is_persisted_workspace(experiment_id):
            try:
                report = model_evaluation_agent.assert_simulation_ready(experiment_id)
                records = promoted_model_registry.latest_per_target(experiment_id)
                if not records:
                    raise ValueError("尚无已晋升模型，不能启动正式仿真")
                missing_bindings = [
                    record.modelVersion for record in records
                    if feature_binding_service.store.latest(experiment_id, record.modelVersion) is None
                ]
                if missing_bindings:
                    raise ValueError(
                        "模型特征尚未完成设备参数绑定：" + "、".join(sorted(set(missing_bindings)))
                    )
                if report.modelVersion not in {record.modelVersion for record in records}:
                    raise ValueError("可靠性报告对应的模型版本已过期，请重新评估")
                return (
                    True,
                    list(report.admissionReasons),
                    report.reliabilityScore,
                    report.modelVersion,
                    report.modelType,
                )
            except (LookupError, ValueError) as exc:
                return False, [str(exc)], None, overview.modelVersion, overview.modelType
        simulation_stage = next(stage for stage in overview.stages if stage.stage == "simulation")
        reasons = [] if simulation_stage.canRun else [simulation_stage.detail, *overview.validationItems]
        return simulation_stage.canRun, reasons, overview.confidenceScore, overview.modelVersion, overview.modelType

    def _get(self, experiment_id: str, run_id: str) -> ExperimentSimulationRun:
        self.refresh()
        run = self._runs.get(run_id)
        if run is None or run.experimentId != experiment_id:
            raise SimulationRunNotFoundError(run_id)
        return run

    @staticmethod
    def _current_binding_versions(experiment_id: str) -> list[str]:
        if not SimulationRunOrchestrator._is_formal_workspace(experiment_id):
            return []
        versions = []
        for record in promoted_model_registry.latest_per_target(experiment_id):
            binding = feature_binding_service.store.latest(experiment_id, record.modelVersion)
            if binding is not None:
                versions.append(binding.bindingVersion)
        return sorted(set(versions))

    @staticmethod
    def _is_formal_workspace(experiment_id: str) -> bool:
        overview = experiment_service.get_workspace_overview(experiment_id)
        return bool(
            overview is not None
            and getattr(overview, "sourceType", None) != "sample"
            and experiment_service.is_persisted_workspace(experiment_id)
        )

    @staticmethod
    def _event(event_type: str, stage_id: str | None, title: str, detail: str) -> SimulationRunEvent:
        return SimulationRunEvent(eventId=f"simulation-event-{uuid4().hex[:10]}", eventType=event_type, stageId=stage_id, title=title, detail=detail, createdAt=_now())


_domain_store_path = os.getenv("DOMAIN_RUN_STORE_PATH", "").strip()
simulation_run_orchestrator = SimulationRunOrchestrator(
    SqliteDomainRunStore(_domain_store_path, "simulation", ExperimentSimulationRun) if _domain_store_path else None
)
