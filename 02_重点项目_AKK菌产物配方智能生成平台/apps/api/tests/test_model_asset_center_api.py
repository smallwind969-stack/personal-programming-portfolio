from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.model_assets.contracts import ModelAssetDetail, ModelAssetSummary
from app.model_registry.contracts import NumericRange, PromotedModelRecord
import app.routers.simulation as simulation_router


client = TestClient(app)


def _record():
    return PromotedModelRecord(
        modelVersion="model-v1", experimentId="exp-1", campaignId="campaign-1", trialId="trial-1",
        artifactFingerprint="sha256:artifact", artifactUri="artifact://v1", datasetSnapshotId="dataset-v1",
        datasetFingerprint="sha256:dataset", runnerKey="sklearn", modelType="ridge", featureNames=["x"],
        targetField="yield", featureRanges={"x": NumericRange(min=0, max=1)}, metrics={"r2": 0.9},
        approvedBy="负责人", approvalReason="人工批准", approvedAt="2026-07-21T00:00:00+00:00",
    )


def test_model_asset_api_lists_and_reads_detail_without_mutation(monkeypatch):
    record = _record()
    summary = ModelAssetSummary(
        experimentId="exp-1", experimentName="实验一", modelVersion="model-v1", targetField="yield",
        modelType="ridge", approvedAt=record.approvedAt, approvedBy="负责人", status="approved", latest=True,
        datasetSnapshotId="dataset-v1", featureCount=1, metrics={"r2": 0.9}, artifactVerified=True,
        simulationUsageCount=0,
    )
    detail = ModelAssetDetail(
        experimentName="实验一", latest=True, artifactVerified=True, record=record, simulationUsages=[],
    )
    service = SimpleNamespace(list_assets=lambda: [summary], get_detail=lambda experiment_id, model_version: detail)
    monkeypatch.setattr(simulation_router, "model_asset_center_service", service, raising=False)

    listed = client.get("/simulation/model-assets")
    fetched = client.get("/simulation/model-assets/exp-1/model-v1")

    assert listed.status_code == 200
    assert listed.json()[0]["modelVersion"] == "model-v1"
    assert fetched.status_code == 200
    assert fetched.json()["record"]["datasetFingerprint"] == "sha256:dataset"


def test_model_asset_detail_api_returns_404_for_unknown_version(monkeypatch):
    def missing(*_): raise LookupError("model asset was not found")
    monkeypatch.setattr(simulation_router, "model_asset_center_service", SimpleNamespace(get_detail=missing), raising=False)

    response = client.get("/simulation/model-assets/exp-1/missing")

    assert response.status_code == 404
