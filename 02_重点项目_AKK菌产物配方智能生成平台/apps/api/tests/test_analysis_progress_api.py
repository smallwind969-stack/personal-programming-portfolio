from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.analysis_progress.contracts import DataAnalysisProgress, DataAnalysisProgressStep
from app.analysis_progress.service import AnalysisProgressNotFoundError
from app.main import app
from app.routers import experiments as experiments_router


client = TestClient(app)


def projection():
    steps = [DataAnalysisProgressStep(
        stepKey=key, sequence=index, label=key, status="running" if index == 1 else "waiting",
        current=index == 1, summary="summary", actionLabel="action", anchor=f"#{key}",
    ) for index, key in enumerate([
        "dataIntake", "mappingReview", "cleaningAlignment",
        "datasetSnapshot", "featureEngineering", "modelingEvaluation",
    ], start=1)]
    return DataAnalysisProgress(
        experimentId="exp-api", experimentName="进度接口实验", sourceType="blank",
        progressPercent=0, currentStepKey="dataIntake", currentAction="上传实验数据",
        steps=steps, disclaimer="只读进度",
    )


def test_analysis_progress_api_returns_six_step_projection(monkeypatch):
    monkeypatch.setattr(
        experiments_router, "data_analysis_progress_service",
        SimpleNamespace(get=lambda experiment_id: projection()), raising=False,
    )

    response = client.get("/experiments/exp-api/analysis-progress")

    assert response.status_code == 200
    assert response.json()["currentStepKey"] == "dataIntake"
    assert len(response.json()["steps"]) == 6


def test_analysis_progress_api_returns_404_for_unknown_experiment(monkeypatch):
    def missing(_):
        raise AnalysisProgressNotFoundError()

    monkeypatch.setattr(
        experiments_router, "data_analysis_progress_service",
        SimpleNamespace(get=missing), raising=False,
    )
    assert client.get("/experiments/missing/analysis-progress").status_code == 404
