from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest

from app.main import app
from app.model_registry.contracts import PromotedModelPrediction
from app.model_registry.bindings import (
    FeatureBindingVersion, SimulationFeatureBindingService, SqliteFeatureBindingStore,
)
from app.model_registry.composite import CompositeModelPrediction
from app.feature_binding_advisor.contracts import FeatureBindingSuggestionRun
from app.feature_binding_advisor.adapter_pack import (
    DeviceAdapterPackCreate, DeviceAdapterPackService, SqliteDeviceAdapterPackStore,
)
import app.routers.simulation as simulation_router
import app.services.simulation_run_orchestrator as orchestrator_module
from app.services.simulation_run_orchestrator import (
    SimulationRunConflictError,
    SimulationRunOrchestrator,
)

client = TestClient(app)


def test_simulation_predict_returns_research_suggestion() -> None:
    response = client.post(
        "/simulation/predict",
        json={
            "targetProduct": "Akk 后生元冻干粉",
            "productFormat": "postbiotic-powder",
            "carbonSource": "BFP",
            "carbonConcentration": 2.0,
            "cultureHours": 60,
            "temperatureC": 37.0,
            "ph": 6.8,
            "anaerobicScore": 0.92,
            "pressureMpa": 120,
            "stirringRpm": 150,
            "pretreated": True,
            "useLlmAdvisor": False,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["label"] == "研发实验建议"
    assert result["researchUseOnly"] is True
    assert result["predictions"]["akkGrowthScore"] > 60
    assert result["predictions"]["scfaScore"] > 40
    assert result["recommendedSettings"]["temperatureC"]["min"] <= 37.0
    assert result["risks"]
    assert result["validationIndicators"]
    assert result["llmAdvisor"]["enabled"] is False
    assert result["predictionSource"] == "rule_model"
    assert result["modelVersion"] is None


def test_experiment_promoted_model_prediction_returns_full_lineage(monkeypatch) -> None:
    class FakeInference:
        def predict(self, experiment_id, inputs, model_version=None, allow_extrapolation=False):
            assert inputs == {"temperature": 37.0, "ph": 6.8}
            return PromotedModelPrediction(
                experimentId=experiment_id, modelVersion="model-v1", trialId="trial-v1",
                datasetSnapshotId="snapshot-v1", datasetFingerprint="sha256:data",
                artifactFingerprint="sha256:" + "a" * 64, targetField="od600", prediction=1.23,
                extrapolated=False, outOfRangeFeatures=[], featureValues=inputs,
            )
    monkeypatch.setattr(simulation_router, "promoted_model_inference_service", FakeInference())
    response = client.post("/simulation/experiments/exp-real/promoted-model/predict", json={
        "inputs": {"temperature": 37.0, "ph": 6.8}, "allowExtrapolation": False,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["predictionSource"] == "promoted_model"
    assert result["modelVersion"] == "model-v1" and result["datasetSnapshotId"] == "snapshot-v1"


def test_experiment_can_list_approved_model_versions(monkeypatch) -> None:
    class FakeRegistry:
        def list(self, experiment_id):
            assert experiment_id == "exp-real"
            return [{
                "modelVersion": "model-v1", "experimentId": experiment_id, "campaignId": "c1", "trialId": "t1",
                "artifactFingerprint": "sha256:" + "a" * 64, "artifactUri": "artifact://models/" + "a" * 64,
                "datasetSnapshotId": "s1", "datasetFingerprint": "sha256:data", "runnerKey": "sklearn-gradient-boosting-v1",
                "modelType": "GradientBoostingRegressor", "featureNames": ["temperature"], "targetField": "od600",
                "featureRanges": {"temperature": {"min": 35, "max": 39}}, "metrics": {"r2": 0.9},
                "approvedBy": "owner", "approvalReason": "verified", "approvedAt": "2026-07-20T10:00:00+00:00", "status": "approved",
            }]
    monkeypatch.setattr(simulation_router, "promoted_model_registry", FakeRegistry())
    response = client.get("/simulation/experiments/exp-real/promoted-models")
    assert response.status_code == 200
    assert response.json()[0]["modelVersion"] == "model-v1"


def test_experiment_confirms_binding_and_runs_composite_prediction(monkeypatch) -> None:
    class FakeBindings:
        def confirm(self, item):
            assert item.experimentId == "exp-real" and item.modelVersion == "model-v1"
            return item
    class FakeComposite:
        def predict(self, experiment_id, parameters, target_fields, allow_extrapolation):
            assert experiment_id == "exp-real" and parameters["temperatureC"] == 37
            return CompositeModelPrediction(
                experimentId=experiment_id, reliability="low", targets=[],
                unavailableTargets=target_fields, unavailableReasons={target_fields[0]: "no approved model"},
            )
    monkeypatch.setattr(simulation_router, "feature_binding_service", FakeBindings())
    monkeypatch.setattr(simulation_router, "composite_prediction_service", FakeComposite())
    binding_response = client.post("/simulation/experiments/exp-real/model-bindings", json={
        "bindingVersion": "binding-v1", "modelVersion": "model-v1", "featureNames": ["temperature_c"],
        "entries": [{"modelFeature": "temperature_c", "standardField": "temperature_c", "simulationParameter": "temperatureC"}],
        "confirmedBy": "owner", "confirmationReason": "人工确认映射",
    })
    assert binding_response.status_code == 200 and binding_response.json()["status"] == "confirmed"
    prediction_response = client.post("/simulation/experiments/exp-real/composite-predict", json={
        "parameters": {"temperatureC": 37, "ph": 6.8}, "targetFields": ["od600"], "allowExtrapolation": False,
    })
    assert prediction_response.status_code == 200
    assert prediction_response.json()["unavailableTargets"] == ["od600"]


def test_binding_advisor_api_never_activates_and_adapter_pack_round_trips(monkeypatch, tmp_path) -> None:
    run = FeatureBindingSuggestionRun(
        runId="suggestion-1", experimentId="exp-real", modelVersion="model-v1", commandId="cmd-1",
        status="completed", mode="rule_only", provider="disabled", model="none", candidateCount=1,
        reviewCount=0, conflictCount=0, rejectedCount=0, readyForConfirmation=True,
        candidates=[{"modelFeature": "temperature_c", "standardField": "temperature_c", "simulationParameter": "temperatureC", "confidence": .97, "source": "rule", "evidence": ["alias"], "requiresHumanReview": False, "reviewReasons": []}],
        createdAt="2026-07-20T12:00:00+00:00",
    )
    class FakeAdvisor:
        def create_run(self, experiment_id, model_version, command_id, adapter_selector=None): return run
        def get_run(self, experiment_id, run_id): return run if run_id == run.runId else None
    monkeypatch.setattr(simulation_router, "feature_binding_advisor", FakeAdvisor())
    monkeypatch.setattr(simulation_router, "device_adapter_pack_service", DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db")))
    created = client.post("/simulation/experiments/exp-real/models/model-v1/binding-suggestion-runs", json={"commandId": "cmd-1"})
    assert created.status_code == 200 and created.json()["activatedBindingVersion"] is None
    assert client.get("/simulation/experiments/exp-real/binding-suggestion-runs/suggestion-1").status_code == 200
    payload = {"enterpriseKey": "e1", "deviceType": "reactor", "packVersion": "1.0.0", "createdBy": "owner", "entries": [
        {"sourceFieldAlias": "Temp", "standardField": "temperature_c", "simulationParameter": "temperatureC", "sourceUnit": "°C", "targetUnit": "℃"}
    ]}
    exported = client.post("/simulation/device-adapter-packs/export", json=payload)
    assert exported.status_code == 200 and exported.json()["contentHash"].startswith("sha256:")
    imported = client.post("/simulation/device-adapter-packs/import", json=exported.json())
    assert imported.status_code == 200 and imported.json() == exported.json()


def test_device_adapter_pack_comparison_api(monkeypatch, tmp_path) -> None:
    service = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "compare-packs.db"))
    monkeypatch.setattr(simulation_router, "device_adapter_pack_service", service)
    base = {
        "enterpriseKey": "enterprise-a", "deviceType": "bioreactor-x",
        "packVersion": "1.0.0", "createdBy": "owner",
        "entries": [{
            "sourceFieldAlias": "Temp", "standardField": "temperature_c",
            "simulationParameter": "temperatureC", "sourceUnit": "C", "targetUnit": "C",
            "scale": 1, "offset": 0,
        }],
    }
    target = {
        **base, "packVersion": "2.0.0",
        "entries": [{**base["entries"][0], "targetUnit": "K", "offset": 273.15}],
    }
    assert client.post("/simulation/device-adapter-packs/export", json=base).status_code == 200
    assert client.post("/simulation/device-adapter-packs/export", json=target).status_code == 200

    response = client.get("/simulation/device-adapter-packs/compare", params={
        "enterpriseKey": "enterprise-a", "deviceType": "bioreactor-x",
        "baseVersion": "1.0.0", "targetVersion": "2.0.0",
    })
    assert response.status_code == 200
    assert response.json()["changed"][0]["changedFields"] == ["targetUnit", "offset"]
    assert client.get("/simulation/device-adapter-packs/compare", params={
        "enterpriseKey": "enterprise-a", "deviceType": "bioreactor-x",
        "baseVersion": "1.0.0", "targetVersion": "1.0.0",
    }).status_code == 422
    assert client.get("/simulation/device-adapter-packs/compare", params={
        "enterpriseKey": "enterprise-a", "deviceType": "bioreactor-x",
        "baseVersion": "1.0.0", "targetVersion": "9.0.0",
    }).status_code == 404


def test_binding_advisor_can_be_enqueued_for_worker_execution() -> None:
    response = client.post(
        "/simulation/experiments/exp-real/models/model-v1/binding-suggestion-runs/enqueue",
        json={
            "commandId": "binding-async-api", "priority": 1,
            "adapterPack": {
                "enterpriseKey": "enterprise-a", "deviceType": "reactor", "packVersion": "1.0.0",
            },
        },
    )
    assert response.status_code == 200
    task = response.json()
    assert task["targetKind"] == "adaptation"
    assert task["action"] == "featureBindingSuggest"
    assert task["status"] == "queued"
    assert task["payload"]["adapterPack"]["deviceType"] == "reactor"


def test_binding_confirmation_revalidates_suggestion_adapter_lineage(monkeypatch, tmp_path) -> None:
    packs = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "lineage-packs.db"))
    pack = packs.export(DeviceAdapterPackCreate.model_validate({
        "enterpriseKey": "enterprise-a", "deviceType": "reactor", "packVersion": "1.0.0",
        "createdBy": "owner", "entries": [{
            "sourceFieldAlias": "Temp", "standardField": "temperature_c",
            "simulationParameter": "temperatureC", "sourceUnit": "℃", "targetUnit": "℃",
        }],
    }))
    reference = {
        "packId": pack.packId, "enterpriseKey": pack.enterpriseKey,
        "deviceType": pack.deviceType, "packVersion": pack.packVersion,
        "contentHash": pack.contentHash,
    }
    suggestion = FeatureBindingSuggestionRun(
        runId="suggestion-lineage", experimentId="exp-real", modelVersion="model-v1",
        commandId="lineage-command", requestFingerprint="sha256:" + "c" * 64,
        adapterPack=reference, status="completed", mode="rule_only", provider="disabled",
        model="none", candidateCount=1, reviewCount=0, conflictCount=0, rejectedCount=0,
        readyForConfirmation=True, candidates=[{
            "modelFeature": "temperature_c", "standardField": "temperature_c",
            "simulationParameter": "temperatureC", "confidence": .99, "source": "adapter",
            "evidence": ["verified pack"], "requiresHumanReview": False, "reviewReasons": [],
        }], createdAt="2026-07-20T12:00:00Z",
    )
    class Advisor:
        def get_run(self, experiment_id, run_id):
            return suggestion if (experiment_id, run_id) == ("exp-real", suggestion.runId) else None

    monkeypatch.setattr(simulation_router, "feature_binding_advisor", Advisor())
    monkeypatch.setattr(simulation_router, "device_adapter_pack_service", packs)
    monkeypatch.setattr(
        simulation_router, "feature_binding_service",
        SimulationFeatureBindingService(SqliteFeatureBindingStore(tmp_path / "lineage-bindings.db")),
    )
    payload = {
        "bindingVersion": "binding-lineage-v1", "modelVersion": "model-v1",
        "featureNames": ["temperature_c"], "entries": [{
            "modelFeature": "temperature_c", "standardField": "temperature_c",
            "simulationParameter": "temperatureC", "scale": 1, "offset": 0,
        }], "confirmedBy": "owner", "confirmationReason": "已核对设备适配包",
        "suggestionRunId": suggestion.runId, "adapterPack": reference,
    }
    confirmed = client.post("/simulation/experiments/exp-real/model-bindings", json=payload)
    assert confirmed.status_code == 200
    assert confirmed.json()["adapterPack"]["contentHash"] == pack.contentHash

    tampered = {**payload, "bindingVersion": "binding-lineage-v2", "adapterPack": {
        **reference, "contentHash": "sha256:" + "b" * 64,
    }}
    rejected = client.post("/simulation/experiments/exp-real/model-bindings", json=tampered)
    assert rejected.status_code == 422


def test_simulation_predict_rejects_out_of_range_values() -> None:
    response = client.post(
        "/simulation/predict",
        json={
            "targetProduct": "bad",
            "productFormat": "culture-medium",
            "carbonSource": "BFP",
            "carbonConcentration": -1,
            "cultureHours": 60,
            "temperatureC": 37.0,
            "ph": 6.8,
            "anaerobicScore": 0.92,
            "pressureMpa": 120,
            "stirringRpm": 150,
            "pretreated": False,
            "useLlmAdvisor": False,
        },
    )

    assert response.status_code == 422


def test_simulation_scenarios_include_default_presets() -> None:
    response = client.get("/simulation/scenarios")

    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 4
    assert {item["carbonSource"] for item in scenarios} >= {"BFP", "lambdaCarrageenan", "UBFP"}


def test_simulation_llm_status_has_key_placeholder_fields() -> None:
    response = client.get("/simulation/llm-status")

    assert response.status_code == 200
    status = response.json()
    assert "enabled" in status
    assert "provider" in status
    assert "apiKeyConfigured" in status
    assert "envKeys" in status


def test_simulation_uses_innovation_attachment_knowledge() -> None:
    response = client.post(
        "/simulation/predict",
        json={
            "targetProduct": "λ-卡拉胶 AKK 特征代谢物培养液",
            "productFormat": "culture-medium",
            "carbonSource": "lambdaCarrageenan",
            "carbonConcentration": 2.0,
            "cultureHours": 72,
            "temperatureC": 37.0,
            "ph": 6.8,
            "anaerobicScore": 0.95,
            "pressureMpa": 80,
            "stirringRpm": 140,
            "pretreated": True,
            "useLlmAdvisor": False,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["confidence"] in {"medium", "high"}
    assert "Amuc-1260" in " ".join(result["validationIndicators"])
    assert any("λ-卡拉胶" in item or "Amuc" in item for item in result["risks"])


def _trial_payload() -> dict:
    return {
        "targetProduct": "AKK 后生元冻干粉",
        "productFormat": "postbiotic-powder",
        "carbonSource": "BFP",
        "carbonConcentration": 2.0,
        "cultureHours": 60,
        "temperatureC": 37.0,
        "ph": 6.8,
        "anaerobicScore": 0.92,
        "pressureMpa": 120,
        "stirringRpm": 150,
        "pretreated": True,
        "useLlmAdvisor": False,
    }


def _managed_overview():
    return SimpleNamespace(
        targetProduct="通用目标产物", modelVersion="model-v1",
        modelType="GradientBoostingRegressor", stages=[],
    )


def _approved_report():
    return SimpleNamespace(
        reportId="report-v1", modelVersion="model-v1",
        modelType="GradientBoostingRegressor", reliabilityScore=.91,
        admissionReasons=["可靠性评估与人工确认均已通过"],
        performanceMetrics={"r2": .92, "mae": .03},
        predictionInterval=SimpleNamespace(margin=.06),
    )


def test_managed_simulation_requires_confirmed_feature_binding(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator_module.experiment_service, "get_workspace_overview", lambda _id: _managed_overview())
    monkeypatch.setattr(orchestrator_module.experiment_service, "is_persisted_workspace", lambda _id: True)
    monkeypatch.setattr(orchestrator_module.model_evaluation_agent, "assert_simulation_ready", lambda _id: _approved_report())
    monkeypatch.setattr(orchestrator_module.promoted_model_registry, "latest_per_target", lambda _id: [SimpleNamespace(modelVersion="model-v1")])
    monkeypatch.setattr(orchestrator_module.feature_binding_service.store, "latest", lambda *_args: None)

    run = SimulationRunOrchestrator().latest("exp-managed")

    assert run.admissionAllowed is False
    assert "特征" in run.admissionReasons[0] and "绑定" in run.admissionReasons[0]


def test_managed_trial_uses_promoted_model_without_overwriting_official_parameters(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator_module.experiment_service, "get_workspace_overview", lambda _id: _managed_overview())
    monkeypatch.setattr(orchestrator_module.experiment_service, "is_persisted_workspace", lambda _id: True)
    monkeypatch.setattr(orchestrator_module.model_evaluation_agent, "assert_simulation_ready", lambda _id: _approved_report())
    monkeypatch.setattr(orchestrator_module.promoted_model_registry, "latest_per_target", lambda _id: [SimpleNamespace(modelVersion="model-v1")])
    monkeypatch.setattr(orchestrator_module.feature_binding_service.store, "latest", lambda *_args: SimpleNamespace(bindingVersion="binding-v1"))
    model_target = {
        "targetField": "yield", "prediction": 0.87,
        "interval": {"lower": .81, "upper": .93},
        "modelVersion": "model-v1", "trialId": "trial-v1", "bindingVersion": "binding-v1",
        "datasetSnapshotId": "dataset-v1", "datasetFingerprint": "sha256:data",
        "artifactFingerprint": "sha256:" + "a" * 64, "extrapolated": False,
        "outOfRangeFeatures": [], "bindingAudit": [], "metrics": {"r2": .92, "rmse": .03},
    }
    monkeypatch.setattr(orchestrator_module.composite_prediction_service, "predict", lambda *_args, **_kwargs: CompositeModelPrediction(
        experimentId="exp-managed", reliability="high", targets=[model_target],
        unavailableTargets=[], unavailableReasons={},
    ))
    orchestrator = SimulationRunOrchestrator()
    run = orchestrator.create("exp-managed")
    official_before = run.officialParameters.model_dump(mode="json")
    changed = run.officialParameters.model_copy(update={"temperatureC": 36.5})

    snapshot = orchestrator.trial("exp-managed", run.runId, changed)

    assert snapshot.predictionSource == "promoted_model_composite"
    assert snapshot.modelTargets[0].prediction == .87
    assert snapshot.modelTargets[0].interval.method == "empirical_holdout_absolute_error"
    assert snapshot.modelTargets[0].interval.lower == .81
    assert snapshot.bindingVersions == ["binding-v1"]
    assert orchestrator.latest("exp-managed").officialParameters.model_dump(mode="json") == official_before


def test_active_managed_run_stops_when_binding_lineage_changes(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator_module.experiment_service, "get_workspace_overview", lambda _id: _managed_overview())
    monkeypatch.setattr(orchestrator_module.experiment_service, "is_persisted_workspace", lambda _id: True)
    monkeypatch.setattr(orchestrator_module.model_evaluation_agent, "assert_simulation_ready", lambda _id: _approved_report())
    monkeypatch.setattr(orchestrator_module.promoted_model_registry, "latest_per_target", lambda _id: [SimpleNamespace(modelVersion="model-v1")])
    current = {"version": "binding-v1"}
    monkeypatch.setattr(orchestrator_module.feature_binding_service.store, "latest", lambda *_args: SimpleNamespace(bindingVersion=current["version"]))
    orchestrator = SimulationRunOrchestrator()
    run = orchestrator.create("exp-managed")
    current["version"] = "binding-v2"

    with pytest.raises(SimulationRunConflictError, match="必须新建版本"):
        orchestrator.advance("exp-managed", run.runId)


def test_experiment_simulation_run_has_seven_auditable_stages() -> None:
    response = client.post("/experiments/exp-akk-018/simulation-runs")

    assert response.status_code == 200
    run = response.json()
    assert run["admissionAllowed"] is True
    assert run["status"] == "running"
    assert len(run["stages"]) == 7
    assert [stage["stageKey"] for stage in run["stages"]] == [
        "modelValidation",
        "systemInitialization",
        "materialPreparation",
        "coreProduction",
        "downstreamProcessing",
        "productCollection",
        "resultEvaluation",
    ]
    assert run["stages"][0]["status"] == "running"
    assert run["events"][0]["eventType"] == "simulationStarted"

    advanced = client.post(
        f"/experiments/exp-akk-018/simulation-runs/{run['runId']}/advance"
    )
    assert advanced.status_code == 200
    body = advanced.json()
    assert body["stages"][0]["status"] == "completed"
    assert body["stages"][1]["status"] == "running"
    assert client.post("/experiments/exp-akk-018/simulation-runs").status_code == 409
    client.post(
        f"/experiments/exp-akk-018/simulation-runs/{run['runId']}/stop"
    )


def test_simulation_admission_is_enforced_by_backend() -> None:
    preview = client.get("/experiments/exp-algae-017/simulation-runs/latest")
    assert preview.status_code == 200
    assert preview.json()["admissionAllowed"] is False
    assert preview.json()["status"] == "waiting"
    assert preview.json()["admissionReasons"]

    assert client.post("/experiments/exp-algae-017/simulation-runs").status_code == 409


def test_simulation_trial_snapshot_does_not_overwrite_official_parameters() -> None:
    run = client.post("/experiments/exp-akk-018/simulation-runs").json()
    official_before = run["officialParameters"]
    payload = _trial_payload()
    payload["temperatureC"] = 36.4
    payload["ph"] = 6.72

    response = client.post(
        f"/experiments/exp-akk-018/simulation-runs/{run['runId']}/trial",
        json=payload,
    )
    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["researchUseOnly"] is True
    assert snapshot["parameters"]["temperatureC"] == 36.4
    assert snapshot["predictions"]["overallScore"] > 0

    latest = client.get("/experiments/exp-akk-018/simulation-runs/latest").json()
    assert latest["officialParameters"] == official_before
    assert latest["trialSnapshots"][-1]["snapshotId"] == snapshot["snapshotId"]
    client.post(
        f"/experiments/exp-akk-018/simulation-runs/{run['runId']}/stop"
    )


def test_simulation_run_stop_and_restart_preserve_parent_version() -> None:
    run = client.post("/experiments/exp-food-012/simulation-runs").json()
    stopped = client.post(
        f"/experiments/exp-food-012/simulation-runs/{run['runId']}/stop"
    ).json()
    assert stopped["status"] == "stopped"
    assert client.post(
        f"/experiments/exp-food-012/simulation-runs/{run['runId']}/advance"
    ).status_code == 409

    restarted = client.post(
        f"/experiments/exp-food-012/simulation-runs/{run['runId']}/restart"
    )
    assert restarted.status_code == 200
    child = restarted.json()
    assert child["parentRunId"] == run["runId"]
    assert child["version"] == run["version"] + 1
    assert child["officialParameters"]["targetProduct"] == "功能食品稳定基料"
    assert child["lineTemplateId"] == "functional-food-processing"
    assert child["stages"][2]["equipmentName"] == "配料与均质单元"

    failed = client.post(
        f"/experiments/exp-food-012/simulation-runs/{child['runId']}/fail",
        json={"reason": "mock 传感器数据中断", "affectedVersions": [child["modelVersion"]]},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["failureReason"]
    competing = client.post("/experiments/exp-food-012/simulation-runs")
    assert competing.status_code == 200
    assert client.post(
        f"/experiments/exp-food-012/simulation-runs/{child['runId']}/retry"
    ).status_code == 409
    client.post(
        f"/experiments/exp-food-012/simulation-runs/{competing.json()['runId']}/stop"
    )
    retried = client.post(
        f"/experiments/exp-food-012/simulation-runs/{child['runId']}/retry"
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "running"
    completed = retried.json()
    for _ in range(7):
        completed = client.post(
            f"/experiments/exp-food-012/simulation-runs/{child['runId']}/advance"
        ).json()
    assert completed["status"] == "completed"
    assert completed["officialResult"]["predictions"]["overallScore"] > 0
    assert completed["officialResult"]["risks"]
    assert completed["officialResult"]["validationIndicators"]


def test_simulation_trial_rejects_invalid_parameter_precision() -> None:
    run = client.get("/experiments/exp-food-012/simulation-runs/latest").json()
    payload = _trial_payload()
    payload["temperatureC"] = 36.44
    response = client.post(
        f"/experiments/exp-food-012/simulation-runs/{run['runId']}/trial",
        json=payload,
    )
    assert response.status_code == 422


def test_concurrent_retries_leave_only_one_active_simulation_run() -> None:
    orchestrator = SimulationRunOrchestrator()
    first = orchestrator.create("exp-akk-018")
    orchestrator.fail("exp-akk-018", first.runId, "first mock failure", [first.modelVersion])
    second = orchestrator.create("exp-akk-018")
    orchestrator.fail("exp-akk-018", second.runId, "second mock failure", [second.modelVersion])

    def retry(run_id: str) -> str:
        try:
            return orchestrator.retry("exp-akk-018", run_id).status
        except SimulationRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(retry, [first.runId, second.runId]))

    assert results.count("running") == 1
    assert results.count("conflict") == 1
