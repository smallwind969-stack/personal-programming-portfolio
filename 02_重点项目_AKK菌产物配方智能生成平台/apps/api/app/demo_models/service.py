from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import os

from app.demo_models.contracts import DemoModelAdmission, DemoModelAdmissionCreate
from app.research.artifacts import ContentAddressedModelArtifactStore
from app.research.service import ResearchCampaignService, research_campaign_service
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import ExperimentService, experiment_service


class DemoModelAdmissionService:
    """Sample-only simulation admission that never writes to the formal registry."""

    def __init__(self, workspace_service: ExperimentService, research_service: ResearchCampaignService,
                 artifacts: ContentAddressedModelArtifactStore, store: SqliteExperimentDataStore | None) -> None:
        self.workspace_service = workspace_service
        self.research_service = research_service
        self.artifacts = artifacts
        self.store = store
        self._records: dict[str, DemoModelAdmission] = {}
        if store is not None:
            for payload in store.list("demo_model_admission"):
                record = DemoModelAdmission.model_validate(payload)
                self._records[record.experimentId] = record

    def create(self, experiment_id: str, request: DemoModelAdmissionCreate) -> DemoModelAdmission:
        overview = self.workspace_service.get_workspace_overview(experiment_id)
        if overview is None:
            raise LookupError(experiment_id)
        if overview.sourceType != "sample":
            raise ValueError("演示模型准入仅适用于隔离的示例实验")
        campaign = self.research_service.get(experiment_id, request.campaignId)
        trial = next((item for item in campaign.trials if item.trialId == request.trialId), None)
        if trial is None:
            raise LookupError(request.trialId)
        if trial.status != "keep" or trial.modelCard is None:
            raise ValueError("只能选择已保留且具有可审计模型卡的训练轮次")
        # The isolated demo lane may select any retained, auditable artifact.
        # Formal promotion still requires the campaign best trial; this branch
        # never writes to the enterprise model registry.
        if not trial.datasetFingerprint or not trial.artifactFingerprint:
            raise ValueError("训练轮次缺少数据集或模型产物指纹")
        self.artifacts.verify(trial.artifactFingerprint)
        card = trial.modelCard
        target_range = card.get("targetRange", {})
        span = max(float(target_range.get("max", 0)) - float(target_range.get("min", 0)), 1e-12)
        normalized_error = max(0.0, min(1.0, 1 - float(trial.metrics.get("mae", span)) / span))
        r2_score = max(0.0, min(1.0, float(trial.metrics.get("r2", 0.0))))
        row_count = int(card.get("trainRows", 0)) + int(card.get("holdoutRows", 0))
        data_adequacy = max(0.0, min(1.0, row_count / 100))
        score_breakdown = {
            "normalizedError": round(normalized_error, 6),
            "r2": round(r2_score, 6),
            "dataAdequacy": round(data_adequacy, 6),
            "artifactIntegrity": 1.0,
        }
        score = min(0.79, round(0.35 * normalized_error + 0.25 * r2_score + 0.20 * data_adequacy + 0.20, 6))
        record = DemoModelAdmission(
            admissionId=f"demo-admission-{uuid4().hex[:12]}", experimentId=experiment_id,
            demoModelVersion=f"demo-{trial.trialId}", campaignId=campaign.campaignId,
            trialId=trial.trialId, datasetSnapshotId=campaign.datasetSnapshotId,
            datasetFingerprint=trial.datasetFingerprint, artifactFingerprint=trial.artifactFingerprint,
            artifactVerified=True, modelType=trial.modelType or "sample-demo-model",
            featureNames=list(trial.featureNames), targetField=trial.targetField or "sample_target",
            metrics=dict(trial.metrics), scoreBreakdown=score_breakdown, reliabilityScore=score, operator=request.operator.strip(),
            reason=request.reason.strip(), createdAt=datetime.now(timezone.utc).isoformat(),
            restrictions=["不得晋升为企业正式模型", "不得登记为真实实验测量", "不得发送设备控制指令", "仅用于平台功能演示和研发流程教学"],
            limitations=["准入评分综合归一化误差、R²、样本量和产物完整性，不是正式模型可靠性结论", "仿真阶段当前使用确定性规则代理，训练产物仅用于血缘与界面演示"],
            disclaimer="隔离演示模型仅用于体验仿真与工艺优化流程，不代表真实产线预测能力。",
        )
        self._records[experiment_id] = record
        if self.store is not None:
            self.store.save("demo_model_admission", record.admissionId, experiment_id, record.model_dump(mode="json"))
        self.workspace_service.activate_sample_demo_model(record)
        return record.model_copy(deep=True)

    def latest(self, experiment_id: str) -> DemoModelAdmission | None:
        record = self._records.get(experiment_id)
        return record.model_copy(deep=True) if record else None

    def require_active(self, experiment_id: str) -> DemoModelAdmission:
        record = self.latest(experiment_id)
        if record is None:
            raise ValueError("示例实验尚未完成人工演示模型准入")
        return record


artifact_root = Path(os.getenv("RESEARCH_ARTIFACT_PATH", "apps/api/data/runtime/model-artifacts"))
demo_model_admission_service = DemoModelAdmissionService(
    experiment_service, research_campaign_service, ContentAddressedModelArtifactStore(artifact_root),
    experiment_file_service.store,
)
