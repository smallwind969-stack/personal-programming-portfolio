from __future__ import annotations

from app.analysis_progress.contracts import DataAnalysisProgress, DataAnalysisProgressStep


class AnalysisProgressNotFoundError(LookupError):
    pass


class DataAnalysisProgressService:
    def __init__(
        self, *, workspace_source, intake_source, cleaning_source,
        snapshot_source, feature_source, campaign_source, evaluation_source,
    ) -> None:
        self.workspaceSource = workspace_source
        self.intakeSource = intake_source
        self.cleaningSource = cleaning_source
        self.snapshotSource = snapshot_source
        self.featureSource = feature_source
        self.campaignSource = campaign_source
        self.evaluationSource = evaluation_source

    def get(self, experiment_id: str) -> DataAnalysisProgress:
        workspace = self.workspaceSource.get_workspace_overview(experiment_id)
        if workspace is None:
            raise AnalysisProgressNotFoundError(experiment_id)

        intake = self.intakeSource.latest_run(experiment_id)
        cleaning = self.cleaningSource.latest_run(experiment_id)
        snapshot = self.snapshotSource.get_latest_dataset_snapshot(experiment_id)
        feature = self.featureSource.latest_run(experiment_id)
        campaigns = self.campaignSource.list(experiment_id)
        campaign = campaigns[-1] if campaigns else None
        report = self.evaluationSource.latest_report(experiment_id)

        intake_exists = intake is not None
        mapping_confirmed = getattr(intake, "status", None) == "confirmed"
        cleaning_status = getattr(cleaning, "status", None)
        cleaning_complete = cleaning_status in {"completed", "confirmed"}
        snapshot_complete = getattr(snapshot, "status", None) == "modeling_ready"
        feature_status = getattr(feature, "status", None)
        feature_complete = feature_status == "confirmed"
        promotion = getattr(campaign, "promotion", None)
        promotion_approved = getattr(promotion, "status", None) == "approved"
        promoted_version = getattr(promotion, "promotedModelVersion", None)
        report_relevant = report is not None and (
            not promoted_version or getattr(report, "modelVersion", None) == promoted_version
        )
        modeling_complete = promotion_approved and report_relevant and getattr(report, "status", None) == "confirmed"
        # Isolated demonstrations may be admitted through a demo model card rather
        # than a formal promotion report.  The lifecycle projection is the source
        # of truth for that gate, so do not leave the six-step progress panel at
        # 88% after the workspace has already opened simulation.
        lifecycle_stages = getattr(workspace, "stages", None) or []
        data_analysis_stage = next(
            (
                stage for stage in lifecycle_stages
                if (stage.get("stage") if isinstance(stage, dict) else getattr(stage, "stage", None)) == "dataAnalysis"
            ),
            None,
        )
        lifecycle_analysis_complete = (
            data_analysis_stage is not None
            and (data_analysis_stage.get("status") if isinstance(data_analysis_stage, dict) else getattr(data_analysis_stage, "status", None)) == "completed"
        )
        modeling_complete = modeling_complete or lifecycle_analysis_complete

        steps = [
            self._step(
                "dataIntake", 1, "数据接入与字段识别",
                "completed" if intake_exists else "running",
                f"已接入资产 {intake.assetId}" if intake_exists else "等待上传首批实验数据",
                "查看字段识别" if intake_exists else "上传实验数据",
                "#data-intake",
                [f"file-asset://{intake.assetId}", f"data-intake://{intake.runId}"] if intake_exists else [],
                [],
            ),
            self._step(
                "mappingReview", 2, "字段和单位人工确认",
                "completed" if mapping_confirmed else "needsReview" if intake_exists else "waiting",
                "字段、单位与换算证据已签署" if mapping_confirmed else f"{getattr(intake, 'pendingReviewCount', 0)} 项等待人工确认" if intake_exists else "等待数据接入",
                "查看已确认映射" if mapping_confirmed else "人工确认字段与单位" if intake_exists else "等待上一步",
                "#mapping-review",
                [f"data-intake://{intake.runId}"] if intake_exists else [],
                [] if intake_exists else ["尚未生成字段识别证据"],
            ),
            self._step(
                "cleaningAlignment", 3, "数据清洗与时间轴对齐",
                "completed" if cleaning_complete else "needsReview" if cleaning_status == "needsReview" else "running" if mapping_confirmed else "waiting",
                f"清洗运行 {cleaning.runId} 已完成" if cleaning_complete else "质量问题等待人工放行" if cleaning_status == "needsReview" else "可创建清洗对齐运行" if mapping_confirmed else "等待字段映射确认",
                "查看清洗证据" if cleaning_complete else "复核并放行" if cleaning_status == "needsReview" else "开始清洗对齐" if mapping_confirmed else "等待上一步",
                "#cleaning-alignment",
                [f"cleaning-alignment://{cleaning.runId}"] if cleaning is not None else [],
                [] if mapping_confirmed else ["字段和单位尚未人工确认"],
            ),
            self._step(
                "datasetSnapshot", 4, "建模数据集快照",
                "completed" if snapshot_complete else "running" if cleaning_complete else "waiting",
                f"快照 {snapshot.snapshotId} 已锁定" if snapshot_complete else "可锁定当前清洗结果" if cleaning_complete else "等待清洗对齐完成",
                "查看数据快照" if snapshot_complete else "创建数据集快照" if cleaning_complete else "等待上一步",
                "#dataset-snapshot",
                [f"dataset-snapshot://{snapshot.snapshotId}"] if snapshot_complete else [],
                [] if cleaning_complete else ["清洗对齐尚未完成"],
            ),
            self._step(
                "featureEngineering", 5, "特征工程与泄漏审计",
                "completed" if feature_complete else "needsReview" if feature is not None else "running" if snapshot_complete else "waiting",
                f"特征集 {feature.featureSetId} 已确认" if feature_complete else "候选特征等待人工确认" if feature is not None else "可配置目标与特征" if snapshot_complete else "等待数据集快照",
                "查看特征集" if feature_complete else "确认特征集" if feature is not None else "创建特征工程运行" if snapshot_complete else "等待上一步",
                "#feature-engineering",
                [f"feature-set://{feature.featureSetId}"] if feature is not None else [],
                [] if snapshot_complete else ["建模数据集快照尚未创建"],
            ),
            self._step(
                "modelingEvaluation", 6, "数学建模与可靠性评估",
                "completed" if modeling_complete else "needsReview" if promotion_approved or report_relevant else "running" if feature_complete else "waiting",
                f"模型 {promoted_version} 与可靠性报告已确认" if modeling_complete else "模型或可靠性报告等待人工复核" if promotion_approved or report_relevant else "可建立固定评测训练活动" if feature_complete else "等待特征集确认",
                "查看模型可靠性" if modeling_complete else "完成人工复核" if promotion_approved or report_relevant else "开始数学建模" if feature_complete else "等待上一步",
                "#modeling-evaluation",
                [
                    *([f"research-campaign://{campaign.campaignId}"] if campaign is not None else []),
                    *([f"model-evaluation://{report.reportId}"] if report_relevant else []),
                    *(["lifecycle://dataAnalysis"] if lifecycle_analysis_complete and not report_relevant else []),
                ],
                [] if feature_complete else ["特征集尚未人工确认"],
            ),
        ]

        current = next((step for step in steps if step.status != "completed"), None)
        if current is not None:
            current.current = True
        completed = sum(step.status == "completed" for step in steps)
        partial = (
            0 if current is None or (current.stepKey == "dataIntake" and not intake_exists)
            else 50 if current.status == "needsReview"
            else 25 if current.status == "running"
            else 0
        )
        progress = round((completed * 100 + partial) / 6)
        return DataAnalysisProgress(
            experimentId=workspace.experimentId,
            experimentName=workspace.name,
            sourceType=workspace.sourceType,
            progressPercent=progress,
            currentStepKey=current.stepKey if current else None,
            currentAction=current.actionLabel if current else "数据分析阶段已完成",
            steps=steps,
            disclaimer="进度只读取当前实验血缘；任何人工确认、模型晋升和质量放行仍需在对应工作台明确提交。",
        )

    @staticmethod
    def _step(key, sequence, label, status, summary, action, anchor, evidence, blockers):
        return DataAnalysisProgressStep(
            stepKey=key, sequence=sequence, label=label, status=status,
            summary=summary, actionLabel=action, anchor=anchor,
            evidenceRefs=evidence, blockedReasons=blockers,
        )


from app.model_evaluation.agent import model_evaluation_agent
from app.research.service import research_campaign_service
from app.services.cleaning_alignment_agent import cleaning_alignment_agent
from app.services.data_collection_localization_agent import data_collection_localization_agent
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import experiment_service
from app.services.feature_engineering_agent import feature_engineering_agent


data_analysis_progress_service = DataAnalysisProgressService(
    workspace_source=experiment_service,
    intake_source=data_collection_localization_agent,
    cleaning_source=cleaning_alignment_agent,
    snapshot_source=experiment_file_service,
    feature_source=feature_engineering_agent,
    campaign_source=research_campaign_service,
    evaluation_source=model_evaluation_agent,
)
