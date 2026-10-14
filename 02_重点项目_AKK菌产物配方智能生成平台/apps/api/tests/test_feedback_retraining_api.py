from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.feedback_retraining.contracts import (
    FeedbackRetrainingEvent,
    FeedbackRetrainingRun,
    FeedbackRetrainingStage,
)
from app.main import app
import app.routers.experiments as experiments_router


client = TestClient(app)


def _run() -> FeedbackRetrainingRun:
    return FeedbackRetrainingRun(
        runId="feedback-retraining-api-v1",
        experimentId="exp-api",
        commandId="command-api",
        requestFingerprint="sha256:request",
        status="running",
        parentModelVersion="model-v1",
        feedbackDatasetVersions=["feedback-1", "feedback-2", "feedback-3"],
        fixedBudgetSeconds=30,
        derivedDatasetId="feedback-derived-dataset-v1",
        derivedDatasetFingerprint="sha256:derived",
        historicalRowCount=20,
        trainingFeedbackRowCount=0,
        externalHoldoutRowCount=3,
        stages=[
            FeedbackRetrainingStage(
                stageId=f"stage-{index}", stageKey=f"key-{index}",
                stageName=f"阶段 {index}",
                status="running" if index == 1 else "completed" if index == 0 else "waiting",
                progressPercent=10 if index == 1 else 100 if index == 0 else 0,
                detail="可审计阶段",
            )
            for index in range(5)
        ],
        currentStageId="stage-1",
        progressPercent=20,
        events=[FeedbackRetrainingEvent(
            eventId="event-1", eventType="created",
            title="已创建", detail="测试", createdAt="2026-07-21T00:00:00+00:00",
        )],
        createdAt="2026-07-21T00:00:00+00:00",
        updatedAt="2026-07-21T00:00:00+00:00",
    )


def test_feedback_retraining_api_exposes_list_create_advance_and_review(monkeypatch):
    run = _run()
    calls = []
    fake = SimpleNamespace(
        list=lambda experiment_id: [run],
        get=lambda experiment_id, run_id: run,
        create=lambda experiment_id, payload: calls.append(("create", payload.commandId)) or run,
        advance=lambda experiment_id, run_id: calls.append(("advance", run_id)) or run,
        review=lambda experiment_id, run_id, payload: calls.append(("review", payload.decision)) or run,
    )
    monkeypatch.setattr(experiments_router, "feedback_retraining_agent", fake, raising=False)

    listed = client.get("/experiments/exp-api/feedback-retraining-runs")
    created = client.post("/experiments/exp-api/feedback-retraining-runs", json={
        "commandId": "command-api",
        "parentModelVersion": "model-v1",
        "feedbackDatasetVersions": ["feedback-1", "feedback-2", "feedback-3"],
        "fixedBudgetSeconds": 30,
    })
    advanced = client.post("/experiments/exp-api/feedback-retraining-runs/feedback-retraining-api-v1/advance")
    reviewed = client.post("/experiments/exp-api/feedback-retraining-runs/feedback-retraining-api-v1/review", json={
        "decision": "approved", "operator": "研发负责人", "reason": "指标与血缘已复核",
    })

    assert listed.status_code == 200 and len(listed.json()) == 1
    assert created.status_code == 200
    assert advanced.status_code == 200
    assert reviewed.status_code == 200
    assert calls == [
        ("create", "command-api"),
        ("advance", "feedback-retraining-api-v1"),
        ("review", "approved"),
    ]
