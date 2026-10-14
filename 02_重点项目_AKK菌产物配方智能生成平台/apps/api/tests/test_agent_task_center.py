from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_orchestrator import agent_orchestrator
from app.services.optimization_orchestrator import optimization_orchestrator
from app.services.product_innovation_agent import product_innovation_agent
from app.services.product_requirement_registry import product_requirement_registry
from app.services.simulation_run_orchestrator import simulation_run_orchestrator


client = TestClient(app)


def setup_function() -> None:
    agent_orchestrator._runs.clear()
    agent_orchestrator._run_ids_by_experiment.clear()
    product_innovation_agent._runs.clear()
    product_innovation_agent._commands.clear()
    product_requirement_registry.reset()
    simulation_run_orchestrator.reset()
    optimization_orchestrator.reset()


def test_task_center_is_read_only_and_exposes_four_business_agents() -> None:
    response = client.get("/experiments/exp-food-012/agent-task-center")
    assert response.status_code == 200
    center = response.json()
    assert [task["agentKey"] for task in center["tasks"]] == [
        "productInnovation", "dataAnalysis", "simulation", "optimization"
    ]
    assert all(task["agentKind"] == "business" for task in center["tasks"])
    assert all("智能体" not in task["agentName"] and "大模型" not in task["agentName"] for task in center["tasks"])
    assert agent_orchestrator._run_ids_by_experiment.get("exp-food-012") is None
    assert center["disclaimer"] == "研发实验建议"


def test_task_center_projects_real_data_analysis_run_without_mutation() -> None:
    run = client.post("/experiments/exp-food-012/agent-runs").json()
    center = client.get("/experiments/exp-food-012/agent-task-center").json()
    task = next(item for item in center["tasks"] if item["agentKey"] == "dataAnalysis")
    assert task["status"] == "running"
    assert task["runId"] == run["runId"]
    assert task["version"] == run["version"]
    assert task["canGuide"] is True
    assert any(ref.startswith("runtime://") for ref in task["sourceRefs"])


def test_confirmed_product_requirement_is_visible_and_traceable() -> None:
    innovation = client.post("/experiments/exp-food-012/product-innovation-runs", json={
        "commandId": "innovation-1",
        "input": {"brief": "开发低糖稳定的菌藻发酵饮品并完成研发验证", "industry": "功能食品", "targetMarket": "中国", "targetUsers": [], "locale": "zh-CN", "constraints": []},
    }).json()
    version = client.post(
        f"/experiments/exp-food-012/product-innovation-runs/{innovation['runId']}/confirm",
        json={"commandId": "confirm-1", "operator": "研发负责人", "reason": "需求已复核"},
    ).json()
    center = client.get("/experiments/exp-food-012/agent-task-center").json()
    task = next(item for item in center["tasks"] if item["agentKey"] == "productInnovation")
    assert task["status"] == "completed"
    assert task["version"] == version["version"]
    assert f"product-requirement://{version['requirementVersionId']}" in task["sourceRefs"]


def test_dependencies_and_blocking_reasons_are_explicit() -> None:
    center = client.get("/experiments/exp-food-012/agent-task-center").json()
    simulation = next(item for item in center["tasks"] if item["agentKey"] == "simulation")
    optimization = next(item for item in center["tasks"] if item["agentKey"] == "optimization")
    assert simulation["dependsOn"] == ["data-analysis"]
    assert optimization["dependsOn"] == ["product-innovation", "simulation"]
    assert simulation["blockedReasons"]
    assert optimization["blockedReasons"]


def test_unknown_experiment_returns_404() -> None:
    assert client.get("/experiments/not-real/agent-task-center").status_code == 404
