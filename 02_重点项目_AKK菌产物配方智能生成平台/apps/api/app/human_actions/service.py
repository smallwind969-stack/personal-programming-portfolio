from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256

from app.human_actions.contracts import HumanActionCenter, HumanActionItem


class HumanActionCenterService:
    def __init__(
        self, archive_provider, evaluation_source, design_source,
        execution_source, measurement_source, retraining_source,
    ) -> None:
        self.archiveProvider = archive_provider
        self.evaluationSource = evaluation_source
        self.designSource = design_source
        self.executionSource = execution_source
        self.measurementSource = measurement_source
        self.retrainingSource = retraining_source

    def get(
        self,
        *,
        priority: str | None = None,
        stage_key: str | None = None,
        experiment_id: str | None = None,
    ) -> HumanActionCenter:
        items: list[HumanActionItem] = []
        archive = self.archiveProvider()
        for experiment in archive.experiments:
            if experiment_id is not None and experiment.experimentId != experiment_id:
                continue
            items.extend(self._for_experiment(experiment.experimentId, experiment.name))
        if priority is not None:
            items = [item for item in items if item.priority == priority]
        if stage_key is not None:
            items = [item for item in items if item.stageKey == stage_key]
        rank = {"high": 0, "medium": 1, "normal": 2}
        items.sort(key=lambda item: (rank[item.priority], item.experimentName, item.title, item.actionId))
        counts = Counter(item.experimentId for item in items)
        return HumanActionCenter(
            totalCount=len(items),
            highPriorityCount=sum(item.priority == "high" for item in items),
            experimentCount=len(counts),
            experimentActionCounts=dict(counts),
            items=items,
            generatedAt=datetime.now(timezone.utc).isoformat(),
        )

    def _for_experiment(self, experiment_id: str, experiment_name: str) -> list[HumanActionItem]:
        route_base = f"/experiments/{experiment_id}"
        report = self.evaluationSource.latest_report(experiment_id)
        if report is None:
            return []
        if report.recommendedAdmission:
            if report.status == "needsReview" and not report.admissionAllowed:
                return [self._item(
                    experiment_id, experiment_name, "modelEvaluation", "reviewReliability", "high",
                    "复核模型可靠性准入", "模型已达到推荐准入线，等待研发负责人签署适用边界。",
                    f"{route_base}/analysis", f"model-evaluation://{report.reportId}",
                )]
            return []

        designs = self.designSource.list(experiment_id)
        design = next((item for item in reversed(designs) if item.reportId == report.reportId and item.modelVersion == report.modelVersion), None)
        if design is None:
            return [self._item(
                experiment_id, experiment_name, "supplementaryDesign", "generateDesign", "normal",
                "生成可靠性补实验方案", "当前模型未通过可靠性准入，需要基于报告生成定向补实验设计。",
                f"{route_base}/optimization", f"model-evaluation://{report.reportId}",
            )]
        if design.status == "needsReview":
            return [self._item(
                experiment_id, experiment_name, "supplementaryDesign", "reviewDesign", "medium",
                "选择并审批补实验计划", f"已有 {len(design.candidates)} 套候选方案等待人工选择和批准。",
                f"{route_base}/optimization", f"supplementary-design://{design.runId}",
            )]
        if design.status != "approved" or not design.planVersion:
            return []

        actions: list[HumanActionItem] = []
        executions = [
            item for item in self.executionSource.list(experiment_id)
            if item.planVersion == design.planVersion and item.candidateId in design.selectedCandidateIds
        ]
        execution_by_candidate = {item.candidateId: item for item in executions}
        candidate_names = {item.candidateId: item.displayName for item in design.candidates}
        measurements = self.measurementSource.list(experiment_id)
        measurement_by_execution = {item.executionBatchId: item for item in measurements}
        confirmed_versions: set[str] = set()

        for candidate_id in design.selectedCandidateIds:
            execution = execution_by_candidate.get(candidate_id)
            candidate_name = candidate_names.get(candidate_id, candidate_id)
            if execution is None:
                actions.append(self._item(
                    experiment_id, experiment_name, "supplementaryExecution", "createExecution", "normal",
                    f"建立执行批次：{candidate_name}", "该获批候选尚未转换为可追踪的实验执行批次。",
                    f"{route_base}/optimization", f"supplementary-candidate://{candidate_id}",
                ))
                continue
            if execution.status not in {"completed", "cancelled"}:
                priority = "medium" if execution.status in {"awaitingData", "needsReview"} else "normal"
                label = {
                    "planned": "开始补实验执行", "inProgress": "继续补实验执行",
                    "awaitingData": "上传补实验原始数据", "needsReview": "复核补实验执行记录",
                }.get(execution.status, "处理补实验执行批次")
                actions.append(self._item(
                    experiment_id, experiment_name, "supplementaryExecution", "continueExecution", priority,
                    f"{label}：{execution.batchCode}", f"当前执行状态为 {execution.status}。",
                    f"{route_base}/optimization", f"supplementary-execution://{execution.batchId}",
                ))
                continue
            if execution.status == "cancelled":
                continue
            measurement = measurement_by_execution.get(execution.batchId)
            if measurement is None:
                actions.append(self._item(
                    experiment_id, experiment_name, "measurementFeedback", "createMeasurement", "normal",
                    f"建立真实测量任务：{execution.batchCode}", "执行批次已经完成，尚未交接真实测量录入。",
                    f"{route_base}/optimization", f"supplementary-execution://{execution.batchId}",
                ))
            elif measurement.status == "draft":
                actions.append(self._item(
                    experiment_id, experiment_name, "measurementFeedback", "enterMeasurements", "medium",
                    f"录入真实测量：{execution.batchCode}", "测量任务已建立，等待填写真实参数、三个独立重复、单位、方法和来源文件。",
                    f"{route_base}/optimization", f"supplementary-measurement://{measurement.measurementBatchId}",
                ))
            elif measurement.status == "needsReview":
                actions.append(self._item(
                    experiment_id, experiment_name, "measurementFeedback", "reviewMeasurements", "high",
                    f"复核真实测量：{execution.batchCode}", "真实测量已提交质量门禁，等待研发负责人决定。",
                    f"{route_base}/optimization", f"supplementary-measurement://{measurement.measurementBatchId}",
                ))
            elif measurement.status == "confirmed" and measurement.qualityGate is not None:
                version = measurement.qualityGate.feedbackDatasetVersion
                if version:
                    confirmed_versions.add(version)

        retraining_runs = self.retrainingSource.list(experiment_id)
        relevant = [
            item for item in retraining_runs
            if confirmed_versions and confirmed_versions.intersection(item.feedbackDatasetVersions)
        ]
        retraining = relevant[-1] if relevant else None
        if retraining is not None and retraining.status == "needsReview":
            actions.append(self._item(
                experiment_id, experiment_name, "feedbackRetraining", "reviewRetraining", "high",
                "复核反馈重训练候选", "候选模型已通过技术门禁，等待人工晋升决定。",
                f"{route_base}/optimization", f"retraining://{retraining.runId}",
            ))
        elif retraining is None and len(confirmed_versions) >= 3:
            actions.append(self._item(
                experiment_id, experiment_name, "feedbackRetraining", "createRetraining", "normal",
                "创建反馈重训练活动", f"当前计划已有 {len(confirmed_versions)} 份已确认反馈数据，满足建立重训练活动的最低数量。",
                f"{route_base}/optimization", f"supplementary-plan://{design.planVersion}",
            ))
        return actions

    @staticmethod
    def _item(
        experiment_id: str, experiment_name: str, stage_key: str,
        action_type: str, priority: str, title: str, detail: str,
        route: str, source_ref: str, blocked_reasons: list[str] | None = None,
    ) -> HumanActionItem:
        digest = sha256(f"{action_type}|{source_ref}".encode("utf-8")).hexdigest()[:12]
        return HumanActionItem(
            actionId=f"human-action-{digest}", experimentId=experiment_id,
            experimentName=experiment_name, stageKey=stage_key,
            actionType=action_type, priority=priority, title=title, detail=detail,
            route=route, sourceRef=source_ref, blockedReasons=blocked_reasons or [],
        )


from app.feedback_retraining.agent import feedback_retraining_agent
from app.model_evaluation.agent import model_evaluation_agent
from app.services.experiment_service import experiment_service
from app.supplementary_design.agent import supplementary_experiment_design_agent
from app.supplementary_execution.agent import supplementary_experiment_execution_agent
from app.supplementary_measurement.agent import supplementary_measurement_handoff_agent


class _EmptySource:
    @staticmethod
    def list(experiment_id): return []


human_action_center_service = HumanActionCenterService(
    archive_provider=experiment_service.list_workspace_archive,
    evaluation_source=model_evaluation_agent,
    design_source=supplementary_experiment_design_agent or _EmptySource(),
    execution_source=supplementary_experiment_execution_agent or _EmptySource(),
    measurement_source=supplementary_measurement_handoff_agent or _EmptySource(),
    retraining_source=feedback_retraining_agent or _EmptySource(),
)
