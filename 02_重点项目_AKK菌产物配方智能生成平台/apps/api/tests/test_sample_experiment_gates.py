import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.routers import experiments as experiments_router


client = TestClient(app)


def create_workspace(service: ExperimentService, source_type: str):
    request = ExperimentCreateRequest(
        name=f"{source_type} source test",
        objective="验证示例证据安全门禁",
        targetProduct="通用培养产物",
        targetMetrics=["OD600"],
        sourceType="blank" if source_type == "sample" else source_type,
    )
    return service.create_workspace(
        request, None,
        source_type=source_type,
        sample_template_version="algae-culture-v1" if source_type == "sample" else None,
    )


@pytest.mark.parametrize("action", ["modelPromotion", "measurementFeedback", "deviceControl"])
def test_sample_workspace_is_rejected_by_formal_evidence_gates(tmp_path, action) -> None:
    service = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    sample = create_workspace(service, "sample")

    with pytest.raises(ValueError, match="示例实验"):
        service.assert_formal_evidence_allowed(sample.experimentId, action)


@pytest.mark.parametrize("source_type", ["enterprise", "blank"])
def test_non_sample_workspace_is_not_rejected_by_source_gate(tmp_path, source_type) -> None:
    service = ExperimentService(SqliteRepository(tmp_path / f"{source_type}.db"))
    workspace = create_workspace(service, source_type)
    service.assert_formal_evidence_allowed(workspace.experimentId, "modelPromotion")


def test_sample_api_blocks_model_promotion_and_measurement_creation(monkeypatch, tmp_path) -> None:
    service = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    sample = create_workspace(service, "sample")
    monkeypatch.setattr(experiments_router, "experiment_service", service)

    promotion = client.post(
        f"/experiments/{sample.experimentId}/research-campaigns/missing/promotion",
        json={"trialId": "trial-1", "decision": "approved", "operator": "owner", "reason": "formal promotion"},
    )
    validation = client.post(
        f"/experiments/{sample.experimentId}/validation-batches",
        json={
            "optimizationRunId": "optimization-1", "parameterVersion": "parameter-v1",
            "predictedResultVersion": "prediction-v1", "batchCode": "SAMPLE-001",
            "scale": "lab", "operator": "owner", "plannedAt": "2026-07-21T10:00:00+08:00",
        },
    )
    measurement = client.post(
        f"/experiments/{sample.experimentId}/supplementary-measurement-batches",
        json={"commandId": "sample-measurement", "executionBatchId": "execution-1", "operator": "owner"},
    )

    assert promotion.status_code == 409
    assert validation.status_code == 409
    assert measurement.status_code == 409
    assert "示例实验" in promotion.json()["detail"]
    assert "示例实验" in validation.json()["detail"]
    assert "示例实验" in measurement.json()["detail"]
