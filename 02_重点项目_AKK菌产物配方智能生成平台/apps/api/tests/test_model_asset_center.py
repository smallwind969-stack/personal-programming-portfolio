from types import SimpleNamespace

from app.model_assets.service import ModelAssetCenterService
from app.model_registry.bindings import FeatureBindingEntry, FeatureBindingVersion
from app.model_registry.contracts import NumericRange, PromotedModelRecord
from app.enterprise_knowledge.usage import EnterpriseKnowledgeUsage


def _record(version="model-v2", approved_at="2026-07-21T08:00:00+00:00"):
    return PromotedModelRecord(
        modelVersion=version, experimentId="exp-1", campaignId="campaign-1", trialId="trial-1",
        artifactFingerprint=f"sha256:artifact-{version}", artifactUri=f"artifact://{version}",
        datasetSnapshotId="dataset-v3", datasetFingerprint="sha256:dataset-v3", runnerKey="sklearn",
        modelType="RandomForestRegressor", featureNames=["temperature", "ph"], targetField="yield",
        featureRanges={"temperature": NumericRange(min=30, max=40), "ph": NumericRange(min=6, max=8)},
        metrics={"r2": 0.91, "mae": 0.08}, approvedBy="研发负责人", approvalReason="通过留出集复核",
        approvedAt=approved_at, status="approved",
    )


class Registry:
    def __init__(self): self.records = [_record(), _record("model-v1", "2026-07-20T08:00:00+00:00")]
    def list(self, experiment_id): return list(self.records) if experiment_id == "exp-1" else []
    def get(self, experiment_id, model_version): return next((item for item in self.records if item.modelVersion == model_version), None)
    def latest(self, experiment_id): return self.records[0] if experiment_id == "exp-1" else None


class Evaluations:
    def list_reports(self, experiment_id):
        return [SimpleNamespace(
            modelVersion="model-v2", status="confirmed", reliabilityScore=0.88,
            reliabilityGrade="high", reportId="report-2", admissionAllowed=True,
            recommendedAdmission=True, artifactVerified=True,
        )]


class Bindings:
    def latest(self, experiment_id, model_version):
        if model_version != "model-v2": return None
        return FeatureBindingVersion(
            bindingVersion="binding-v2", experimentId=experiment_id, modelVersion=model_version,
            featureNames=["temperature", "ph"], entries=[
                FeatureBindingEntry(modelFeature="temperature", standardField="temperature_c", simulationParameter="temperatureC"),
                FeatureBindingEntry(modelFeature="ph", standardField="ph", simulationParameter="ph"),
            ], confirmedBy="工程师", confirmationReason="字段和单位已复核", createdAt="2026-07-21T09:00:00+00:00",
        )


class Simulations:
    def list_runs(self, experiment_id):
        return [SimpleNamespace(
            runId="simulation-1", experimentId=experiment_id, version=2, status="completed",
            modelVersion="model-v2", bindingVersions=["binding-v2"], reliabilityScore=0.88,
            officialResult=SimpleNamespace(snapshotId="snapshot-1"), updatedAt="2026-07-21T10:00:00+00:00",
        )]


class Artifacts:
    def verify(self, fingerprint): return fingerprint.endswith("model-v2")


def _service():
    return ModelAssetCenterService(
        registry=Registry(), archive_provider=lambda: SimpleNamespace(experiments=[SimpleNamespace(experimentId="exp-1", name="培养工艺")]),
        evaluation_source=Evaluations(), binding_store=Bindings(), simulation_source=Simulations(), artifact_store=Artifacts(),
    )


def test_asset_list_projects_latest_version_evidence_and_usage():
    assets = _service().list_assets()

    assert [item.modelVersion for item in assets] == ["model-v2", "model-v1"]
    assert assets[0].latest is True
    assert assets[0].artifactVerified is True
    assert assets[0].evaluationStatus == "confirmed"
    assert assets[0].bindingVersion == "binding-v2"
    assert assets[0].simulationUsageCount == 1
    assert assets[1].latest is False


def test_asset_detail_preserves_dataset_binding_evaluation_and_simulation_lineage():
    detail = _service().get_detail("exp-1", "model-v2")

    assert detail.record.datasetSnapshotId == "dataset-v3"
    assert detail.evaluationReport.reportId == "report-2"
    assert detail.binding.bindingVersion == "binding-v2"
    assert detail.simulationUsages[0].officialSnapshotId == "snapshot-1"
    assert detail.simulationUsages[0].bindingVersions == ["binding-v2"]


def test_unknown_asset_is_not_synthesized():
    try:
        _service().get_detail("exp-1", "model-missing")
    except LookupError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("missing model asset must not be synthesized")


def test_asset_detail_projects_matching_knowledge_usage_snapshot():
    service = ModelAssetCenterService(
        registry=Registry(),
        archive_provider=lambda: SimpleNamespace(experiments=[SimpleNamespace(experimentId="exp-1", name="training")]),
        evaluation_source=Evaluations(), binding_store=Bindings(), simulation_source=Simulations(), artifact_store=Artifacts(),
        knowledge_usage_source=SimpleNamespace(list=lambda **_: [EnterpriseKnowledgeUsage.model_construct(usageId="usage-1", targetVersion="dataset-v3"), EnterpriseKnowledgeUsage.model_construct(usageId="usage-other", targetVersion="dataset-old")]),
    )
    detail = service.get_detail("exp-1", "model-v2")
    assert [item.usageId for item in detail.knowledgeUsages] == ["usage-1"]
