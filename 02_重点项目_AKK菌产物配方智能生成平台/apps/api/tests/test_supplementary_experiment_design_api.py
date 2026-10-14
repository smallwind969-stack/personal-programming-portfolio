from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
import app.routers.experiments as experiments_router
from app.schemas.optimization import OptimizationParameters
from app.supplementary_design.contracts import (
    SupplementaryExperimentCandidate,
    SupplementaryExperimentDesignRun,
)


client = TestClient(app)


def _run():
    candidates = [
        SupplementaryExperimentCandidate(
            candidateId=f"candidate-{index}",
            strategyKey=strategy,
            displayName=f"方案 {index}", summary="补实验",
            modelFeatureValues={"temperature_c": 37.0 + index * 0.1},
            processParameters=OptimizationParameters(
                temperatureC=37.0 + index * 0.1, ph=6.9,
                cultureHours=48, stirringRpm=200,
            ),
            exploratoryPrediction=2.9,
            intervalLower=2.7, intervalUpper=3.1,
            intervalMethod="unreliable_model_empirical_holdout_margin",
            informationGainScore=0.7, boundaryRiskScore=0.4,
            addressesGaps=["覆盖不足"], evidence=["报告证据"],
        )
        for index, strategy in enumerate(
            ["coverageRecovery", "boundaryValidation", "residualCorrection"]
        )
    ]
    return SupplementaryExperimentDesignRun(
        runId="supplementary-design-api-v1",
        experimentId="exp-api", commandId="command-api",
        requestFingerprint="sha256:request", status="needsReview",
        reportId="report-v1", reportInputFingerprint="sha256:report",
        reliabilityScore=0.63, modelVersion="model-v2",
        modelArtifactFingerprint="sha256:model",
        datasetFingerprint="sha256:data",
        bindingSource="standard_alias_fallback",
        admissionReasons=["可靠性不足"], candidates=candidates,
        createdAt="2026-07-21T00:00:00+00:00",
        updatedAt="2026-07-21T00:00:00+00:00",
    )


def test_supplementary_design_api_lists_creates_selects_and_reviews(monkeypatch):
    run = _run()
    calls = []
    fake = SimpleNamespace(
        list=lambda experiment_id: [run],
        get=lambda experiment_id, run_id: run,
        create=lambda experiment_id, payload: calls.append(("create", payload.reportId)) or run,
        select=lambda experiment_id, run_id, payload: calls.append(("select", len(payload.candidateIds))) or run,
        review=lambda experiment_id, run_id, payload: calls.append(("review", payload.decision)) or run,
    )
    monkeypatch.setattr(experiments_router, "supplementary_experiment_design_agent", fake, raising=False)

    listed = client.get("/experiments/exp-api/supplementary-design-runs")
    created = client.post("/experiments/exp-api/supplementary-design-runs", json={"commandId": "command-api", "reportId": "report-v1"})
    selected = client.patch("/experiments/exp-api/supplementary-design-runs/supplementary-design-api-v1/selection", json={"candidateIds": ["candidate-0"]})
    reviewed = client.post("/experiments/exp-api/supplementary-design-runs/supplementary-design-api-v1/review", json={"decision": "approved", "operator": "研发负责人", "reason": "补实验方案已复核"})

    assert listed.status_code == 200 and len(listed.json()) == 1
    assert created.status_code == selected.status_code == reviewed.status_code == 200
    assert calls == [("create", "report-v1"), ("select", 1), ("review", "approved")]
