from __future__ import annotations

from datetime import datetime, timezone

from app.lifecycle.contracts import (
    ExperimentLifecycleOverview,
    ExperimentLifecycleStage,
    ExperimentLifecycleSummary,
)


class ExperimentLifecycleNotFoundError(LookupError):
    pass


_LABELS = {
    "dataAnalysis": "数据分析",
    "modelEvaluation": "模型评估",
    "supplementaryDesign": "补实验设计",
    "supplementaryExecution": "实验执行",
    "measurementFeedback": "真实测量",
    "feedbackRetraining": "反馈重训练",
}


class ExperimentLifecycleProjectionService:
    def __init__(
        self, overview_provider, archive_provider, evaluation_source,
        design_source, execution_source, measurement_source, retraining_source,
    ) -> None:
        self.overviewProvider = overview_provider
        self.archiveProvider = archive_provider
        self.evaluationSource = evaluation_source
        self.designSource = design_source
        self.executionSource = execution_source
        self.measurementSource = measurement_source
        self.retrainingSource = retraining_source

    def get(self, experiment_id: str) -> ExperimentLifecycleOverview:
        overview = self.overviewProvider(experiment_id)
        if overview is None:
            raise ExperimentLifecycleNotFoundError(experiment_id)
        route_base = f"/experiments/{experiment_id}"
        report = self.evaluationSource.latest_report(experiment_id)
        analysis_stage = next((item for item in overview.stages if item.stage == "dataAnalysis"), None)
        raw_analysis_status = getattr(analysis_stage, "status", "waiting")
        analysis_status = (
            "completed" if report is not None
            else "failed" if raw_analysis_status == "stopped"
            else raw_analysis_status
        )
        analysis_progress = {
            "waiting": 0, "running": 50, "needsReview": 85,
            "completed": 100, "failed": 0,
        }.get(analysis_status, 0)
        stages = [ExperimentLifecycleStage(
            stageKey="dataAnalysis", label=_LABELS["dataAnalysis"],
            status=analysis_status, progressPercent=analysis_progress,
            route=f"{route_base}/analysis", actionLabel="进入数据分析",
            canEnter=True,
            summary=getattr(analysis_stage, "detail", "等待上传和整理实验数据"),
            waitingReasons=[] if analysis_status != "waiting" else ["尚未开始数据收集、清洗、特征工程与数学建模"],
            evidenceRefs=[f"workspace://{experiment_id}"],
        )]

        designs = self.designSource.list(experiment_id) if self.designSource is not None else []
        current_design = None
        if report is not None:
            current_design = next((item for item in reversed(designs) if item.reportId == report.reportId and item.modelVersion == report.modelVersion), None)
        if report is None:
            evaluation_status, evaluation_progress = "waiting", 0
            evaluation_summary = "等待数学模型和独立可靠性报告"
            evaluation_reasons = ["数据分析尚未形成可评估的晋升模型"]
            evaluation_evidence = []
        else:
            evaluation_evidence = [f"model-evaluation://{report.reportId}", f"model://{report.modelVersion}"]
            if report.admissionAllowed or current_design is not None:
                evaluation_status, evaluation_progress = "completed", 100
            elif report.status == "rejected":
                evaluation_status, evaluation_progress = "failed", 100
            else:
                evaluation_status, evaluation_progress = "needsReview", 90
            evaluation_summary = (
                f"可靠性 {(report.reliabilityScore * 100):.1f}% · 已准入"
                if report.admissionAllowed else
                f"可靠性 {(report.reliabilityScore * 100):.1f}% · 需要补充证据"
            )
            evaluation_reasons = list(report.admissionReasons) if not report.admissionAllowed else []
        stages.append(ExperimentLifecycleStage(
            stageKey="modelEvaluation", label=_LABELS["modelEvaluation"],
            status=evaluation_status, progressPercent=evaluation_progress,
            route=f"{route_base}/analysis", actionLabel="查看模型评估",
            canEnter=report is not None or analysis_status in {"completed", "needsReview"},
            summary=evaluation_summary, waitingReasons=evaluation_reasons,
            evidenceRefs=evaluation_evidence,
        ))

        if report is not None and report.admissionAllowed:
            stages.extend(self._not_required_branch(route_base, report))
            return self._overview(overview, stages)

        if current_design is None:
            design_status, design_progress = "waiting", 0
            design_summary = "等待基于可靠性缺口生成补实验方案"
            design_reasons = ["需要先完成当前模型可靠性评估"] if report is None else ["尚未生成当前报告对应的补实验设计"]
            design_evidence = []
            selected_ids: list[str] = []
            plan_version = None
        else:
            selected_ids = list(current_design.selectedCandidateIds)
            plan_version = current_design.planVersion
            design_evidence = [f"supplementary-design://{current_design.runId}"]
            if plan_version:
                design_evidence.append(f"supplementary-plan://{plan_version}")
            if current_design.status == "approved":
                design_status, design_progress = "completed", 100
                design_summary = f"已批准 {len(selected_ids)} 个补实验候选"
                design_reasons = []
            elif current_design.status == "rejected":
                design_status, design_progress = "failed", 100
                design_summary = "补实验设计已驳回"
                design_reasons = [current_design.reviewReason or "需要重新生成或调整补实验方案"]
            else:
                design_status, design_progress = "needsReview", 80
                design_summary = f"已生成 {len(current_design.candidates)} 套候选方案，等待选择和批准"
                design_reasons = ["研发负责人尚未批准补实验计划"]
        stages.append(ExperimentLifecycleStage(
            stageKey="supplementaryDesign", label=_LABELS["supplementaryDesign"],
            status=design_status, progressPercent=design_progress,
            route=f"{route_base}/optimization", actionLabel="查看补实验设计",
            canEnter=report is not None, summary=design_summary,
            waitingReasons=design_reasons, evidenceRefs=design_evidence,
            itemCounts={"selected": len(selected_ids)},
        ))

        all_executions = self.executionSource.list(experiment_id) if self.executionSource is not None else []
        executions = [item for item in all_executions if plan_version and item.planVersion == plan_version and item.candidateId in selected_ids]
        execution_by_candidate = {item.candidateId: item for item in executions}
        completed_executions = [item for item in executions if item.status == "completed"]
        total = len(selected_ids)
        completed_count = len(completed_executions)
        failed_count = sum(item.status == "cancelled" for item in executions)
        if design_status != "completed" or total == 0:
            execution_status, execution_progress = "waiting", 0
            execution_summary = "等待已批准补实验计划"
            execution_reasons = ["补实验计划尚未批准"]
        elif completed_count == total:
            execution_status, execution_progress = "completed", 100
            execution_summary = f"{completed_count}/{total} 个补实验执行批次已完成"
            execution_reasons = []
        elif failed_count:
            execution_status = "failed"
            execution_progress = round(completed_count / total * 100)
            execution_summary = f"{completed_count}/{total} 个执行完成，存在取消批次"
            execution_reasons = ["至少一个补实验执行批次已取消"]
        elif executions:
            execution_status = "running"
            execution_progress = round(completed_count / total * 100)
            execution_summary = f"{completed_count}/{total} 个补实验执行批次已完成"
            missing = total - len(execution_by_candidate)
            execution_reasons = ([f"仍有 {missing} 个获批候选尚未建立执行批次"] if missing else ["仍有执行批次尚未完成"])
        else:
            execution_status, execution_progress = "waiting", 0
            execution_summary = f"0/{total} 个补实验执行批次已完成"
            execution_reasons = [f"需要为 {total} 个获批候选建立执行批次"]
        execution_evidence = [f"supplementary-execution://{item.batchId}" for item in executions]
        stages.append(ExperimentLifecycleStage(
            stageKey="supplementaryExecution", label=_LABELS["supplementaryExecution"],
            status=execution_status, progressPercent=execution_progress,
            route=f"{route_base}/optimization", actionLabel="进入实验执行",
            canEnter=design_status == "completed", summary=execution_summary,
            waitingReasons=execution_reasons, evidenceRefs=execution_evidence,
            itemCounts={"total": total, "completed": completed_count, "pending": max(0, total - completed_count)},
        ))

        all_measurements = self.measurementSource.list(experiment_id) if self.measurementSource is not None else []
        execution_ids = {item.batchId for item in executions}
        measurements = [item for item in all_measurements if item.executionBatchId in execution_ids]
        confirmed_measurements = [item for item in measurements if item.status == "confirmed"]
        confirmed_versions = {
            item.qualityGate.feedbackDatasetVersion
            for item in confirmed_measurements
            if item.qualityGate is not None and item.qualityGate.feedbackDatasetVersion
        }
        measurement_total = len(completed_executions)
        measurement_completed = len(confirmed_measurements)
        if execution_status != "completed":
            measurement_status, measurement_progress = "waiting", 0
            measurement_summary = f"{len(measurements)} 个测量任务已建立，等待完成全部执行批次"
            measurement_reasons = ["需要先完成当前计划的全部补实验执行，再汇总真实测量反馈"]
        elif measurement_total and measurement_completed == measurement_total:
            measurement_status, measurement_progress = "completed", 100
            measurement_summary = f"{measurement_completed}/{measurement_total} 个执行批次已形成真实反馈资产"
            measurement_reasons = []
        elif any(item.status == "rejected" for item in measurements):
            measurement_status = "failed"
            measurement_progress = round(measurement_completed / max(1, measurement_total) * 100)
            measurement_summary = "存在已驳回的真实测量任务"
            measurement_reasons = ["需要重新执行实验或建立新的测量证据版本"]
        elif measurements:
            measurement_status, measurement_progress = "needsReview", round(measurement_completed / max(1, measurement_total) * 100)
            measurement_summary = f"{measurement_completed}/{measurement_total} 个执行批次已形成真实反馈资产"
            measurement_reasons = ["存在等待真实测量录入或人工复核的任务"]
        else:
            measurement_status, measurement_progress = "waiting", 0
            measurement_summary = "等待建立真实测量任务"
            measurement_reasons = ["尚未从已完成执行批次建立真实测量任务"]
        measurement_evidence = [f"supplementary-measurement://{item.measurementBatchId}" for item in measurements]
        measurement_evidence.extend(f"feedback-dataset://{version}" for version in sorted(confirmed_versions))
        stages.append(ExperimentLifecycleStage(
            stageKey="measurementFeedback", label=_LABELS["measurementFeedback"],
            status=measurement_status, progressPercent=measurement_progress,
            route=f"{route_base}/optimization", actionLabel="录入真实测量",
            canEnter=bool(completed_executions), summary=measurement_summary,
            waitingReasons=measurement_reasons, evidenceRefs=measurement_evidence,
            itemCounts={"total": measurement_total, "completed": measurement_completed, "pending": max(0, measurement_total - measurement_completed)},
        ))

        all_retraining = self.retrainingSource.list(experiment_id) if self.retrainingSource is not None else []
        relevant_retraining = [item for item in all_retraining if confirmed_versions and confirmed_versions.intersection(item.feedbackDatasetVersions)]
        retraining = relevant_retraining[-1] if relevant_retraining else None
        if not confirmed_versions:
            retraining_status, retraining_progress = "waiting", 0
            retraining_summary = "等待当前补实验计划形成已确认反馈数据"
            retraining_reasons = ["尚无当前计划对应的已确认反馈数据资产"]
            retraining_evidence = []
        elif retraining is None:
            retraining_status, retraining_progress = "waiting", 0
            retraining_summary = f"已有 {len(confirmed_versions)} 份反馈数据，尚未创建重训练活动"
            retraining_reasons = ["需要达到独立反馈批次数要求并由人员创建重训练活动"]
            retraining_evidence = [f"feedback-dataset://{version}" for version in sorted(confirmed_versions)]
        else:
            status_map = {"running": "running", "needsReview": "needsReview", "completed": "completed", "rejected": "failed", "failed": "failed"}
            retraining_status = status_map[retraining.status]
            retraining_progress = retraining.progressPercent
            retraining_summary = f"当前计划反馈已进入重训练活动 {retraining.runId}"
            retraining_reasons = [] if retraining_status == "completed" else (["等待人工晋升与独立可靠性复核"] if retraining_status == "needsReview" else [])
            retraining_evidence = [f"retraining://{retraining.runId}"]
        stages.append(ExperimentLifecycleStage(
            stageKey="feedbackRetraining", label=_LABELS["feedbackRetraining"],
            status=retraining_status, progressPercent=retraining_progress,
            route=f"{route_base}/optimization", actionLabel="查看反馈重训练",
            canEnter=bool(confirmed_versions), summary=retraining_summary,
            waitingReasons=retraining_reasons, evidenceRefs=retraining_evidence,
            itemCounts={"feedbackDatasets": len(confirmed_versions), "retrainingRuns": len(relevant_retraining)},
        ))
        return self._overview(overview, stages)

    def list_summaries(self) -> list[ExperimentLifecycleSummary]:
        archive = self.archiveProvider()
        summaries = []
        for item in archive.experiments:
            lifecycle = self.get(item.experimentId)
            current = next((stage for stage in lifecycle.stages if stage.stageKey == lifecycle.currentStageKey), lifecycle.stages[-1])
            summaries.append(ExperimentLifecycleSummary(
                experimentId=item.experimentId,
                currentStageKey=lifecycle.currentStageKey,
                currentStageLabel=lifecycle.currentStageLabel,
                overallStatus=lifecycle.overallStatus,
                progressPercent=lifecycle.progressPercent,
                nextAction=current.actionLabel,
                route=current.route,
                waitingReasons=current.waitingReasons,
                evidenceRefs=current.evidenceRefs,
            ))
        return summaries

    @staticmethod
    def _not_required_branch(route_base: str, report) -> list[ExperimentLifecycleStage]:
        return [ExperimentLifecycleStage(
            stageKey=key, label=_LABELS[key], status="notRequired", progressPercent=100,
            route=f"{route_base}/optimization", actionLabel="查看准入证据", canEnter=True,
            summary="当前模型已通过可靠性准入，本轮无需进入补实验分支",
            waitingReasons=[], evidenceRefs=[f"model-evaluation://{report.reportId}"],
        ) for key in ("supplementaryDesign", "supplementaryExecution", "measurementFeedback", "feedbackRetraining")]

    @staticmethod
    def _overview(overview, stages: list[ExperimentLifecycleStage]) -> ExperimentLifecycleOverview:
        current = next((stage for stage in stages if stage.status not in {"completed", "notRequired"}), None)
        if current is None:
            overall = "completed"
        elif any(stage.status == "failed" for stage in stages):
            overall = "failed"
        else:
            overall = current.status
        progress = round(sum(stage.progressPercent for stage in stages) / len(stages))
        return ExperimentLifecycleOverview(
            experimentId=overview.experimentId,
            experimentName=overview.name,
            currentStageKey=current.stageKey if current else None,
            currentStageLabel=current.label if current else "闭环已完成",
            overallStatus=overall,
            progressPercent=progress,
            stages=stages,
            generatedAt=datetime.now(timezone.utc).isoformat(),
        )


from app.feedback_retraining.agent import feedback_retraining_agent
from app.model_evaluation.agent import model_evaluation_agent
from app.services.experiment_service import experiment_service
from app.supplementary_design.agent import supplementary_experiment_design_agent
from app.supplementary_execution.agent import supplementary_experiment_execution_agent
from app.supplementary_measurement.agent import supplementary_measurement_handoff_agent


class _EmptySource:
    @staticmethod
    def list(experiment_id):
        return []


experiment_lifecycle_projection_service = ExperimentLifecycleProjectionService(
    overview_provider=experiment_service.get_workspace_overview,
    archive_provider=experiment_service.list_workspace_archive,
    evaluation_source=model_evaluation_agent,
    design_source=supplementary_experiment_design_agent or _EmptySource(),
    execution_source=supplementary_experiment_execution_agent or _EmptySource(),
    measurement_source=supplementary_measurement_handoff_agent or _EmptySource(),
    retraining_source=feedback_retraining_agent or _EmptySource(),
)
