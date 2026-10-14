from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.lifecycle.contracts import (
    ExperimentLifecycleOverview,
    ExperimentLifecycleStage,
    ExperimentLifecycleSummary,
)
from app.lifecycle.service import ExperimentLifecycleNotFoundError
from app.main import app
import app.routers.experiments as experiments_router


client = TestClient(app)


def _overview():
    keys = [
        "dataAnalysis", "modelEvaluation", "supplementaryDesign",
        "supplementaryExecution", "measurementFeedback", "feedbackRetraining",
    ]
    return ExperimentLifecycleOverview(
        experimentId="exp-api", experimentName="闭环演示",
        currentStageKey="supplementaryExecution", currentStageLabel="实验执行",
        overallStatus="running", progressPercent=55,
        stages=[ExperimentLifecycleStage(
            stageKey=key, label=key, status="running" if key == "supplementaryExecution" else "completed",
            progressPercent=50 if key == "supplementaryExecution" else 100,
            route=f"/experiments/exp-api/{'analysis' if key in {'dataAnalysis', 'modelEvaluation'} else 'optimization'}",
            actionLabel="查看", canEnter=True, summary="状态摘要",
        ) for key in keys],
        generatedAt="2026-07-21T05:00:00+00:00",
    )


def test_lifecycle_api_returns_detail_and_archive_summaries(monkeypatch):
    overview = _overview()
    summary = ExperimentLifecycleSummary(
        experimentId="exp-api", currentStageKey="supplementaryExecution",
        currentStageLabel="实验执行", overallStatus="running", progressPercent=55,
        nextAction="进入实验执行", route="/experiments/exp-api/optimization",
        waitingReasons=["仍有执行批次未完成"], evidenceRefs=["supplementary-plan://v1"],
    )
    fake = SimpleNamespace(get=lambda experiment_id: overview, list_summaries=lambda: [summary])
    monkeypatch.setattr(experiments_router, "experiment_lifecycle_projection_service", fake, raising=False)

    detailed = client.get("/experiments/exp-api/lifecycle")
    summaries = client.get("/experiments/lifecycle-summaries")

    assert detailed.status_code == 200
    assert len(detailed.json()["stages"]) == 6
    assert detailed.json()["currentStageKey"] == "supplementaryExecution"
    assert summaries.status_code == 200
    assert summaries.json()[0]["nextAction"] == "进入实验执行"


def test_lifecycle_api_returns_404_for_unknown_experiment(monkeypatch):
    fake = SimpleNamespace(
        get=lambda experiment_id: (_ for _ in ()).throw(ExperimentLifecycleNotFoundError(experiment_id)),
        list_summaries=lambda: [],
    )
    monkeypatch.setattr(experiments_router, "experiment_lifecycle_projection_service", fake, raising=False)

    assert client.get("/experiments/not-real/lifecycle").status_code == 404
