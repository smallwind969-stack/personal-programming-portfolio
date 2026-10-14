from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
import app.routers.experiments as experiments_router
from app.schemas.optimization import OptimizationParameters
from app.supplementary_measurement.contracts import SupplementaryMeasurementBatch


client = TestClient(app)


def _batch():
    return SupplementaryMeasurementBatch(
        measurementBatchId="measurement-api-v1", experimentId="exp-api",
        commandId="command-api", requestFingerprint="sha256:request",
        executionBatchId="execution-api-v1", planVersion="supplement-plan-api-v1",
        candidateId="candidate-api-v1", executionBatchCode="SUP-API-01",
        parentModelVersion="model-v2", reportId="report-v2", targetMetric="od600",
        status="draft",
        frozenParameters=OptimizationParameters(temperatureC=37.8, ph=6.9, cultureHours=48, stirringRpm=200),
        allowedSourceAssetIds=["asset-1"], sourceAssetNames={"asset-1": "device.csv"},
        createdBy="研发负责人", createdAt="2026-07-21T04:00:00+00:00",
    )


def test_supplementary_measurement_api_exposes_handoff_workflow(monkeypatch):
    batch = _batch()
    calls = []
    fake = SimpleNamespace(
        list=lambda experiment_id: [batch],
        get=lambda experiment_id, batch_id: batch,
        create=lambda experiment_id, payload: calls.append(("create", payload.executionBatchId)) or batch,
        submit=lambda experiment_id, batch_id, payload: calls.append(("submit", len(payload.measurements))) or batch,
        review=lambda experiment_id, batch_id, payload: calls.append(("review", payload.decision)) or batch,
    )
    monkeypatch.setattr(experiments_router, "supplementary_measurement_handoff_agent", fake, raising=False)
    base = "/experiments/exp-api/supplementary-measurement-batches"
    measurement = {
        "metricName": "od600", "value": 2.85, "unit": "AU", "replicate": 1,
        "measuredAt": "2026-07-22T10:00:00+08:00", "method": "分光光度计 600 nm",
        "sourceAssetId": "asset-1", "isModelTarget": True,
    }
    responses = [
        client.get(base),
        client.post(base, json={"commandId": "command-api", "executionBatchId": "execution-api-v1", "operator": "研发负责人"}),
        client.get(f"{base}/measurement-api-v1"),
        client.post(f"{base}/measurement-api-v1/submit", json={
            "actualParameters": {"temperatureC": 37.8, "ph": 6.9, "cultureHours": 48, "stirringRpm": 200},
            "measurements": [{**measurement, "replicate": index, "value": 2.8 + index * 0.05} for index in [1, 2, 3]],
            "contaminationObserved": False, "equipmentAbnormalities": [], "notes": "真实测量",
        }),
        client.post(f"{base}/measurement-api-v1/review", json={"decision": "approved", "operator": "复核员", "reason": "来源和重复测量完整"}),
    ]

    assert all(response.status_code == 200 for response in responses)
    assert calls == [("create", "execution-api-v1"), ("submit", 3), ("review", "approved")]
