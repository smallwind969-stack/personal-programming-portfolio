from fastapi.testclient import TestClient

from app.main import app
from app.services.optimization_orchestrator import optimization_orchestrator
from app.services.experiment_service import experiment_service
import pytest
from types import SimpleNamespace
import app.services.optimization_orchestrator as optimization_module
from app.schemas.simulation import SimulationPredictRequest
from app.model_registry.composite import CompositeModelPrediction
from app.services.experiment_service import ExperimentService
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import ExperimentCreateRequest

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_optimization_runs() -> None:
    optimization_orchestrator.reset()
    experiment_service.reset_version_registry()


def test_locked_experiment_can_view_optimization_structure_but_not_create_run() -> None:
    preview = client.get("/experiments/exp-akk-018/optimization-runs/latest")
    assert preview.status_code == 200
    body = preview.json()
    assert body["admissionAllowed"] is False
    assert body["status"] == "waiting"
    assert len(body["candidatePlans"]) == 3
    assert client.post("/experiments/exp-akk-018/optimization-runs").status_code == 409


def test_optimization_run_generates_three_traceable_candidate_plans() -> None:
    response = client.post("/experiments/exp-food-012/optimization-runs")
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "draft"
    assert run["baseModelVersion"] == "model-012-v5"
    assert run["baseResultVersion"] == "result-012-v5"
    assert len(run["candidatePlans"]) == 3
    assert {plan["strategyKey"] for plan in run["candidatePlans"]} == {
        "balanced",
        "yieldPriority",
        "energySaving",
    }
    for plan in run["candidatePlans"]:
        assert plan["confidenceScore"] > 0
        assert plan["riskItems"]
        assert plan["validationItems"]
        assert plan["predictionIntervals"]
        assert len(plan["responseSurface"]) >= 5
        assert plan["baselineImprovements"]


def test_selection_and_formal_submission_preserve_parent_versions() -> None:
    run = client.post("/experiments/exp-food-012/optimization-runs").json()
    parent_model = run["baseModelVersion"]
    parent_result = run["baseResultVersion"]
    selection = {
        "planId": "candidate-balanced",
        "parameters": {
            "temperatureC": 36.8,
            "ph": 6.82,
            "cultureHours": 46,
            "stirringRpm": 195,
        },
    }
    selected = client.patch(
        f"/experiments/exp-food-012/optimization-runs/{run['runId']}/selection",
        json=selection,
    )
    assert selected.status_code == 200
    assert selected.json()["editedParameters"] == selection["parameters"]

    submitted = client.post(
        f"/experiments/exp-food-012/optimization-runs/{run['runId']}/submit"
    )
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["status"] == "running"
    assert body["trainingDataVersion"].startswith("dataset-opt-")
    assert body["retrainingStages"][0]["status"] == "running"
    assert body["baseModelVersion"] == parent_model
    assert body["baseResultVersion"] == parent_result
    assert body["newModelVersion"] is None
    assert body["newResultVersion"] is None


def test_retraining_requires_human_review_before_new_result_version() -> None:
    run = client.post("/experiments/exp-food-012/optimization-runs").json()
    selected = client.patch(
        f"/experiments/exp-food-012/optimization-runs/{run['runId']}/selection",
        json={"planId": "candidate-balanced", "parameters": {"temperatureC": 36.6, "ph": 6.82, "cultureHours": 46, "stirringRpm": 195}},
    )
    assert selected.status_code == 200
    submitted = client.post(f"/experiments/exp-food-012/optimization-runs/{run['runId']}/submit")
    assert submitted.status_code == 200
    run = submitted.json()
    for _ in range(3):
        response = client.post(
            f"/experiments/exp-food-012/optimization-runs/{run['runId']}/advance"
        )
        assert response.status_code == 200
        run = response.json()
    assert run["status"] == "needsReview"
    assert run["retrainingStages"][-1]["status"] == "needsReview"
    assert run["newResultVersion"] is None
    assert run["trainingMetrics"]

    assert client.post(
        f"/experiments/exp-food-012/optimization-runs/{run['runId']}/advance"
    ).status_code == 409

    reviewed = client.post(
        f"/experiments/exp-food-012/optimization-runs/{run['runId']}/review",
        json={
            "decision": "approved",
            "reason": "候选参数、验证指标和重训曲线已完成研发复核",
            "operator": "工艺研发负责人",
            "impactScope": ["training-data", "model-version", "experiment-result"],
        },
    )
    assert reviewed.status_code == 200
    final = reviewed.json()
    assert final["status"] == "completed"
    assert final["newModelVersion"].startswith("model-012-v6")
    assert final["newResultVersion"].startswith("result-012-v")
    assert final["resultSummary"]["confidenceScore"] > 0
    assert final["resultSummary"]["riskItems"]
    assert final["resultSummary"]["validationItems"]
    assert final["humanDecisions"][0]["reason"]
    assert final["baseModelVersion"] == "model-012-v5"
    assert "36.6" in " ".join(final["resultSummary"]["predictedOutcomes"])
    next_run = client.post("/experiments/exp-food-012/optimization-runs")
    assert next_run.status_code == 200
    assert next_run.json()["baseModelVersion"] == final["newModelVersion"]
    assert next_run.json()["baseResultVersion"] == final["newResultVersion"]


def test_failed_version_promotion_rolls_back_review_state(monkeypatch: pytest.MonkeyPatch) -> None:
    run = client.post("/experiments/exp-food-012/optimization-runs").json()
    client.patch(
        f"/experiments/exp-food-012/optimization-runs/{run['runId']}/selection",
        json={"planId": "candidate-balanced", "parameters": {"temperatureC": 36.8, "ph": 6.82, "cultureHours": 46, "stirringRpm": 195}},
    )
    client.post(f"/experiments/exp-food-012/optimization-runs/{run['runId']}/submit")
    for _ in range(3):
        client.post(f"/experiments/exp-food-012/optimization-runs/{run['runId']}/advance")
    monkeypatch.setattr(experiment_service, "promote_versions", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("version race")))
    response = client.post(
        f"/experiments/exp-food-012/optimization-runs/{run['runId']}/review",
        json={"decision": "approved", "reason": "审核证据充分", "operator": "研发负责人", "impactScope": ["model-version", "result-version"]},
    )
    assert response.status_code == 409
    latest = client.get("/experiments/exp-food-012/optimization-runs/latest").json()
    assert latest["status"] == "needsReview"
    assert latest["retrainingStages"][-1]["status"] == "needsReview"
    assert latest["humanDecisions"] == []
    assert latest["newModelVersion"] is None
    assert latest["newResultVersion"] is None


def test_model_constrained_search_generates_three_real_prediction_plans(monkeypatch: pytest.MonkeyPatch) -> None:
    report = SimpleNamespace(reliabilityScore=.9, predictionInterval=SimpleNamespace(margin=.1))
    record = SimpleNamespace(
        modelVersion="model-v1", featureRanges={
            "temperature_c": SimpleNamespace(min=36.0, max=38.0),
            "ph": SimpleNamespace(min=6.7, max=7.1),
            "agitation_rpm": SimpleNamespace(min=180.0, max=220.0),
        },
    )
    binding = SimpleNamespace(bindingVersion="binding-v1", entries=[
        SimpleNamespace(modelFeature="temperature_c", simulationParameter="temperatureC", scale=1, offset=0),
        SimpleNamespace(modelFeature="ph", simulationParameter="ph", scale=1, offset=0),
        SimpleNamespace(modelFeature="agitation_rpm", simulationParameter="stirringRpm", scale=1, offset=0),
    ])
    monkeypatch.setattr(optimization_module.model_evaluation_agent, "assert_simulation_ready", lambda _id: report)
    monkeypatch.setattr(optimization_module.promoted_model_registry, "latest_per_target", lambda _id: [record])
    monkeypatch.setattr(optimization_module.feature_binding_service.store, "latest", lambda *_args: binding)

    def predict(_experiment_id, parameters, allow_extrapolation=False):
        value = parameters["temperatureC"] + parameters["ph"] + parameters["stirringRpm"] / 100
        target = {
            "targetField": "yield", "prediction": value,
            "interval": {"lower": value - .2, "upper": value + .2},
            "modelVersion": "model-v1", "trialId": "trial-v1", "bindingVersion": "binding-v1",
            "datasetSnapshotId": "dataset-v1", "datasetFingerprint": "sha256:data",
            "artifactFingerprint": "sha256:" + "a" * 64, "extrapolated": False,
            "outOfRangeFeatures": [], "bindingAudit": [], "metrics": {"r2": .9, "rmse": .1},
        }
        return CompositeModelPrediction(
            experimentId=_experiment_id, reliability="high", targets=[target],
            unavailableTargets=[], unavailableReasons={},
        )
    monkeypatch.setattr(optimization_module.composite_prediction_service, "predict", predict)
    base = SimulationPredictRequest(
        targetProduct="通用产物", productFormat="culture-medium", carbonSource="BFP",
        carbonConcentration=1, cultureHours=48, temperatureC=37, ph=6.9,
        anaerobicScore=.85, pressureMpa=50, stirringRpm=200, pretreated=False,
    )
    simulation = SimpleNamespace(
        status="completed", officialResult=SimpleNamespace(), officialParameters=base,
    )

    plans, count, metrics = optimization_module.OptimizationOrchestrator()._model_candidates("exp-managed", simulation)

    assert count == 27 and len(plans) == 3 and len(metrics) == 3
    assert {plan.strategyKey for plan in plans} == {"balanced", "yieldPriority", "energySaving"}
    assert all(plan.modelEvidence[0].intervalMethod == "empirical_holdout_absolute_error" for plan in plans)
    assert all(plan.modelEvidence[0].bindingVersion == "binding-v1" for plan in plans)
    assert all(not plan.modelEvidence[0].extrapolated for plan in plans)


def test_approved_process_version_keeps_model_and_persists_parameters(tmp_path) -> None:
    service = ExperimentService(SqliteRepository(tmp_path / "workspace.db"))
    overview = service.create_workspace(ExperimentCreateRequest(
        name="通用工艺验证", objective="验证参数版本闭环", targetProduct="目标产物",
        targetMetrics=["yield"],
    ), None)
    payload = service.repository.get_experiment_workspace(overview.experimentId)
    payload["modelVersion"] = "model-v1"; payload["resultVersion"] = "official-sim-v1"
    service.repository.update_experiment_workspace(payload)

    service.promote_optimization_result(
        overview.experimentId, expected_model_version="model-v1",
        expected_result_version="official-sim-v1", new_result_version="predicted-v2",
        parameter_version="process-v2",
        parameters={"temperatureC": 38, "ph": 6.9, "cultureHours": 48, "stirringRpm": 200},
        source_run_id="optimization-v2",
    )

    updated = service.get_workspace_overview(overview.experimentId)
    assert updated.modelVersion == "model-v1"
    assert updated.resultVersion == "predicted-v2"
    assert service.get_official_process_parameters(overview.experimentId)["temperatureC"] == 38
    assert service._version_history[overview.experimentId][-1]["modelRetrained"] is False
