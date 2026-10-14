from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
import app.routers.experiments as experiments_router
from app.schemas.optimization import OptimizationParameters
from app.supplementary_execution.contracts import (
    SupplementaryExecutionBatch,
    SupplementaryExecutionStep,
)


client = TestClient(app)


def _batch():
    return SupplementaryExecutionBatch(
        batchId="execution-api-v1",
        experimentId="exp-api",
        commandId="command-api",
        requestFingerprint="sha256:request",
        designRunId="design-api-v1",
        planVersion="supplement-plan-api-v1",
        candidateId="candidate-api-v1",
        strategyKey="coverageRecovery",
        candidateName="覆盖缺口修复方案",
        modelVersion="model-v2",
        reportId="report-v2",
        reportInputFingerprint="sha256:report-v2",
        batchCode="SUP-API-01",
        scale="lab",
        status="planned",
        plannedAt="2026-07-22T08:00:00+08:00",
        replicateCount=3,
        samplingRequirements=["至少三个独立重复"],
        frozenParameters=OptimizationParameters(
            temperatureC=37.8, ph=6.9, cultureHours=48, stirringRpm=200,
        ),
        modelFeatureValues={"temperature_c": 37.8},
        steps=[
            SupplementaryExecutionStep(
                stepKey="preparation", order=1, title="实验准备", requirement="确认原料",
            )
        ],
        createdBy="研发负责人",
        createdAt="2026-07-21T00:00:00+00:00",
    )


def test_supplementary_execution_api_exposes_complete_human_workflow(monkeypatch):
    batch = _batch()
    calls = []
    fake = SimpleNamespace(
        list=lambda experiment_id: [batch],
        get=lambda experiment_id, batch_id: batch,
        create=lambda experiment_id, payload: calls.append(("create", payload.candidateId)) or batch,
        start=lambda experiment_id, batch_id, payload: calls.append(("start", payload.operator)) or batch,
        update_step=lambda experiment_id, batch_id, step_key, payload: calls.append(("step", step_key, payload.status)) or batch,
        attach_assets=lambda experiment_id, batch_id, payload: calls.append(("assets", payload.assetIds)) or batch,
        review=lambda experiment_id, batch_id, payload: calls.append(("review", payload.decision)) or batch,
    )
    monkeypatch.setattr(experiments_router, "supplementary_experiment_execution_agent", fake, raising=False)
    base = "/experiments/exp-api/supplementary-execution-batches"

    responses = [
        client.get(base),
        client.post(base, json={
            "commandId": "command-api", "designRunId": "design-api-v1",
            "planVersion": "supplement-plan-api-v1", "candidateId": "candidate-api-v1",
            "batchCode": "SUP-API-01", "scale": "lab", "operator": "研发负责人",
            "plannedAt": "2026-07-22T08:00:00+08:00", "replicateCount": 3,
            "samplingRequirements": ["至少三个独立重复"],
        }),
        client.get(f"{base}/execution-api-v1"),
        client.post(f"{base}/execution-api-v1/start", json={"operator": "执行员", "note": "开始实验"}),
        client.post(f"{base}/execution-api-v1/steps/preparation", json={"operator": "执行员", "status": "completed", "note": "原料已确认"}),
        client.post(f"{base}/execution-api-v1/assets", json={"operator": "执行员", "assetIds": ["asset-1"], "note": "设备原始文件"}),
        client.post(f"{base}/execution-api-v1/review", json={"decision": "approved", "operator": "研发负责人", "reason": "记录完整"}),
    ]

    assert all(response.status_code == 200 for response in responses)
    assert calls == [
        ("create", "candidate-api-v1"), ("start", "执行员"),
        ("step", "preparation", "completed"), ("assets", ["asset-1"]),
        ("review", "approved"),
    ]
