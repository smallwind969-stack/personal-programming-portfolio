from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.human_actions.contracts import HumanActionCenter, HumanActionItem
from app.main import app
import app.routers.experiments as experiments_router


client = TestClient(app)


def test_human_action_center_api_returns_read_only_prioritized_items(monkeypatch):
    center = HumanActionCenter(
        totalCount=1, highPriorityCount=0, experimentCount=1,
        experimentActionCounts={"exp-api": 1},
        items=[HumanActionItem(
            actionId="human-action-api", experimentId="exp-api", experimentName="闭环演示",
            stageKey="supplementaryExecution", actionType="createExecution", priority="normal",
            title="建立执行批次", detail="候选尚未建立执行批次",
            route="/experiments/exp-api/optimization", sourceRef="supplementary-candidate://candidate-1",
        )],
        generatedAt="2026-07-21T06:00:00+00:00",
    )
    monkeypatch.setattr(experiments_router, "human_action_center_service", SimpleNamespace(get=lambda: center), raising=False)

    response = client.get("/experiments/human-actions")

    assert response.status_code == 200
    assert response.json()["totalCount"] == 1
    assert response.json()["items"][0]["actionType"] == "createExecution"


def test_human_action_center_api_forwards_read_only_filters(monkeypatch):
    captured = {}
    center = HumanActionCenter(
        totalCount=0, highPriorityCount=0, experimentCount=0,
        experimentActionCounts={}, items=[], generatedAt="2026-07-21T06:00:00+00:00",
    )

    def get(**filters):
        captured.update(filters)
        return center

    monkeypatch.setattr(experiments_router, "human_action_center_service", SimpleNamespace(get=get), raising=False)
    response = client.get("/experiments/human-actions?priority=high&stageKey=modelEvaluation&experimentId=exp-api")

    assert response.status_code == 200
    assert captured == {"priority": "high", "stage_key": "modelEvaluation", "experiment_id": "exp-api"}
