from types import SimpleNamespace

import pytest

from app.demo_models.contracts import DemoModelAdmissionCreate
from app.demo_models.service import DemoModelAdmissionService


class WorkspaceStub:
    def __init__(self, source_type: str = "sample") -> None:
        self.source_type = source_type
        self.applied = None

    def get_workspace_overview(self, experiment_id: str):
        return SimpleNamespace(experimentId=experiment_id, sourceType=self.source_type)

    def activate_sample_demo_model(self, record) -> None:
        self.applied = record


class ResearchStub:
    def __init__(self) -> None:
        trial = SimpleNamespace(
            trialId="trial-best", status="keep", modelCard={"auditable": True, "targetRange": {"min": 0, "max": 3}, "trainRows": 28, "holdoutRows": 8},
            datasetFingerprint="sha256:data", artifactFingerprint="sha256:artifact",
            modelType="RandomForestRegressor", featureNames=["temperature_c", "ph"],
            targetField="od600", metrics={"r2": 0.91, "mae": 0.04},
        )
        self.campaign = SimpleNamespace(
            campaignId="campaign-1", datasetSnapshotId="snapshot-1",
            bestTrialId=trial.trialId, trials=[trial],
        )

    def get(self, experiment_id: str, campaign_id: str):
        assert experiment_id == "exp-sample" and campaign_id == "campaign-1"
        return self.campaign


class ArtifactStub:
    def __init__(self) -> None:
        self.verified = []

    def verify(self, fingerprint: str) -> bool:
        self.verified.append(fingerprint)
        return True


def request() -> DemoModelAdmissionCreate:
    return DemoModelAdmissionCreate(
        campaignId="campaign-1", trialId="trial-best",
        operator="演示负责人", reason="允许进入隔离仿真体验",
    )


def test_sample_demo_admission_locks_lineage_without_formal_promotion() -> None:
    workspace = WorkspaceStub()
    artifacts = ArtifactStub()
    service = DemoModelAdmissionService(workspace, ResearchStub(), artifacts, None)

    record = service.create("exp-sample", request())

    assert record.scope == "isolated_sample_demo"
    assert record.demoModelVersion == "demo-trial-best"
    assert record.artifactVerified is True
    assert record.reliabilityScore == 0.79
    assert record.scoreBreakdown["artifactIntegrity"] == 1.0
    assert workspace.applied.admissionId == record.admissionId
    assert artifacts.verified == ["sha256:artifact"]
    assert "不得晋升为企业正式模型" in record.restrictions


def test_demo_admission_rejects_enterprise_workspace() -> None:
    service = DemoModelAdmissionService(WorkspaceStub("enterprise"), ResearchStub(), ArtifactStub(), None)
    with pytest.raises(ValueError, match="仅适用于"):
        service.create("exp-sample", request())


def test_demo_admission_accepts_retained_auditable_non_best_trial_in_isolated_scope() -> None:
    research = ResearchStub()
    research.campaign.bestTrialId = "trial-other"
    workspace = WorkspaceStub()
    service = DemoModelAdmissionService(workspace, research, ArtifactStub(), None)

    record = service.create("exp-sample", request())

    assert record.scope == "isolated_sample_demo"
    assert record.trialId == "trial-best"
    assert "不得晋升为企业正式模型" in record.restrictions
    assert workspace.applied.admissionId == record.admissionId
