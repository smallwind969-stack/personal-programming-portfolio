from fastapi.testclient import TestClient

from app.main import app
from app.product_innovation.contracts import ProductInnovationInput
from app.services.product_innovation_agent import product_innovation_agent
from app.services.product_requirement_registry import product_requirement_registry
from app.services.optimization_orchestrator import optimization_orchestrator


client = TestClient(app)


def _input(name: str) -> dict:
    return ProductInnovationInput(
        brief=f"开发{name}，需要兼顾稳定性和成本并完成研发验证",
        industry="功能食品",
        targetMarket="中国",
        constraints=["仅用于研发实验建议"],
    ).model_dump()


def _create(experiment_id: str, command_id: str, name: str) -> dict:
    response = client.post(
        f"/experiments/{experiment_id}/product-innovation-runs",
        json={"commandId": command_id, "input": _input(name)},
    )
    assert response.status_code == 200
    return response.json()


def setup_function() -> None:
    product_innovation_agent._runs.clear()
    product_innovation_agent._commands.clear()
    product_requirement_registry.reset()
    optimization_orchestrator.reset()


def test_confirmation_creates_immutable_audited_version() -> None:
    run = _create("exp-food-012", "innovate-1", "低糖发酵饮品")
    response = client.post(
        f"/experiments/exp-food-012/product-innovation-runs/{run['runId']}/confirm",
        json={"commandId": "confirm-1", "operator": "研发负责人", "reason": "指标与约束已完成评审"},
    )
    assert response.status_code == 200
    version = response.json()
    assert version["version"] == 1
    assert version["sourceRunId"] == run["runId"]
    assert version["snapshot"]["workingName"] == run["workingName"]
    assert version["contentHash"].startswith("sha256:")
    assert version["status"] == "confirmed"
    assert version["disclaimer"] == "研发实验建议"

    run["workingName"] = "客户端篡改"
    latest = client.get("/experiments/exp-food-012/product-requirement-versions/latest").json()
    assert latest["snapshot"]["workingName"] != "客户端篡改"


def test_confirmation_is_idempotent_and_one_run_cannot_create_two_versions() -> None:
    run = _create("exp-food-012", "innovate-1", "低糖发酵饮品")
    url = f"/experiments/exp-food-012/product-innovation-runs/{run['runId']}/confirm"
    payload = {"commandId": "confirm-1", "operator": "研发负责人", "reason": "确认进入下一阶段"}
    first = client.post(url, json=payload)
    second = client.post(url, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["requirementVersionId"] == second.json()["requirementVersionId"]
    conflict = client.post(url, json={**payload, "commandId": "confirm-2"})
    assert conflict.status_code == 409


def test_confirmation_rejects_cross_experiment_source() -> None:
    run = _create("exp-food-012", "innovate-1", "低糖发酵饮品")
    response = client.post(
        f"/experiments/another-experiment/product-innovation-runs/{run['runId']}/confirm",
        json={"commandId": "confirm-x", "operator": "负责人", "reason": "尝试跨实验确认"},
    )
    assert response.status_code == 404


def test_versions_increment_and_link_to_parent() -> None:
    first_run = _create("exp-food-012", "innovate-1", "第一版产品")
    first = client.post(
        f"/experiments/exp-food-012/product-innovation-runs/{first_run['runId']}/confirm",
        json={"commandId": "confirm-1", "operator": "负责人", "reason": "确认第一版"},
    ).json()
    second_run = _create("exp-food-012", "innovate-2", "第二版产品")
    second = client.post(
        f"/experiments/exp-food-012/product-innovation-runs/{second_run['runId']}/confirm",
        json={"commandId": "confirm-2", "operator": "负责人", "reason": "确认第二版"},
    ).json()
    assert second["version"] == 2
    assert second["parentVersionId"] == first["requirementVersionId"]
    versions = client.get("/experiments/exp-food-012/product-requirement-versions").json()
    assert [item["version"] for item in versions] == [1, 2]


def test_optimization_freezes_latest_confirmed_requirement_reference() -> None:
    run = _create("exp-food-012", "innovate-1", "需求驱动产品")
    confirmed = client.post(
        f"/experiments/exp-food-012/product-innovation-runs/{run['runId']}/confirm",
        json={"commandId": "confirm-1", "operator": "负责人", "reason": "确认需求用于工艺优化"},
    ).json()
    optimization = client.post("/experiments/exp-food-012/optimization-runs").json()
    assert optimization["requirementDriven"] is True
    assert optimization["productRequirementVersionId"] == confirmed["requirementVersionId"]
    assert optimization["productRequirementWorkingName"] == confirmed["snapshot"]["workingName"]
    candidate_text = " ".join(
        text
        for plan in optimization["candidatePlans"]
        for text in [plan["summary"], *plan["validationItems"]]
    )
    assert confirmed["snapshot"]["workingName"] in candidate_text
    assert confirmed["snapshot"]["targetMetrics"][0]["metricName"] in candidate_text

    second_run = _create("exp-food-012", "innovate-2", "后续新需求")
    client.post(
        f"/experiments/exp-food-012/product-innovation-runs/{second_run['runId']}/confirm",
        json={"commandId": "confirm-2", "operator": "负责人", "reason": "确认后续版本"},
    )
    assert optimization_orchestrator.latest("exp-food-012").productRequirementVersionId == confirmed["requirementVersionId"]


def test_optimization_without_confirmed_requirement_is_legacy_compatible() -> None:
    response = client.post("/experiments/exp-food-012/optimization-runs")
    assert response.status_code == 200
    assert response.json()["requirementDriven"] is False
    assert response.json()["productRequirementVersionId"] is None
