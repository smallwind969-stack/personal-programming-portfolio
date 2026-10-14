from fastapi.testclient import TestClient

from app.main import app
from app.research.service import research_campaign_service
from app.services.agent_command_service import agent_command_queue
from app.services.agent_command_worker import AgentCommandWorker
from app.services.agent_orchestrator import agent_orchestrator


client = TestClient(app)


def setup_function() -> None:
    research_campaign_service.store.reset()
    agent_command_queue.reset()


def test_research_campaign_api_queues_trial_and_worker_records_result() -> None:
    created = client.post("/experiments/exp-food-012/research-campaigns", json={
        "commandId": "campaign-api", "datasetSnapshotId": "dataset-v4", "agentKey": "modeling",
        "baselineMetrics": {"mae": 0.18, "rmse": 0.24, "r2": 0.78}, "fixedBudgetSeconds": 300,
    })
    assert created.status_code == 200
    campaign = created.json()
    queued = client.post(f"/experiments/exp-food-012/research-campaigns/{campaign['campaignId']}/trials", json={
        "commandId": "research-trial-api", "hypothesis": "降低学习率", "parameterPatch": {"learningRate": 0.03}, "priority": 5,
    })
    assert queued.status_code == 200 and queued.json()["status"] == "queued"
    assert queued.json()["targetKind"] == "research"
    completed = AgentCommandWorker(agent_command_queue, agent_orchestrator, "research-worker", research=research_campaign_service).run_once()
    assert completed.status == "completed"
    observed = client.get(f"/experiments/exp-food-012/research-campaigns/{campaign['campaignId']}").json()
    assert len(observed["trials"]) == 2
    assert observed["trials"][1]["status"] == "keep"
    assert observed["status"] == "needsReview"

    auto = client.post(f"/experiments/exp-food-012/research-campaigns/{campaign['campaignId']}/iterate", json={"commandId": "research-auto-api", "priority": 4})
    assert auto.status_code == 200 and auto.json()["status"] == "queued"
    assert AgentCommandWorker(agent_command_queue, agent_orchestrator, "research-worker", research=research_campaign_service).run_once().status == "completed"
    latest = client.get(f"/experiments/exp-food-012/research-campaigns/{campaign['campaignId']}").json()
    assert len(latest["trials"]) == 3
    assert len(latest["trials"][2]["parameterPatch"]) == 1
