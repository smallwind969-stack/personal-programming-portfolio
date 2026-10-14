from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.demo_models.contracts import DemoModelAdmission
from app.main import app
import app.routers.experiments as experiments_router
import app.services.simulation_run_orchestrator as simulation_module
import app.services.optimization_orchestrator as optimization_module
from app.services.simulation_run_orchestrator import SimulationRunOrchestrator
from app.services.optimization_orchestrator import OptimizationOrchestrator
from app.schemas.optimization import OptimizationParameters


client = TestClient(app)


def admission() -> DemoModelAdmission:
    return DemoModelAdmission(
        admissionId="demo-admission-1", experimentId="exp-sample", demoModelVersion="demo-trial-best",
        campaignId="campaign-1", trialId="trial-best", datasetSnapshotId="snapshot-1",
        datasetFingerprint="sha256:data", artifactFingerprint="sha256:artifact", artifactVerified=True,
        modelType="RandomForestRegressor", featureNames=["temperature_c", "ph"], targetField="od600",
        metrics={"r2": 0.79, "mae": 0.04}, scoreBreakdown={"artifactIntegrity": 1.0}, reliabilityScore=0.79, operator="负责人",
        reason="隔离演示", createdAt="2026-07-21T00:00:00+00:00",
        restrictions=["不得晋升为企业正式模型", "不得登记为真实实验测量", "不得发送设备控制指令"],
        limitations=["仅为演示准入评分"],
        disclaimer="仅用于隔离演示",
    )


def test_demo_model_admission_api_returns_isolated_contract(monkeypatch) -> None:
    record = admission()
    monkeypatch.setattr(experiments_router.experiment_service, "get_workspace_overview", lambda _id: SimpleNamespace())
    monkeypatch.setattr(experiments_router.demo_model_admission_service, "create", lambda *_args: record)
    monkeypatch.setattr(experiments_router.demo_model_admission_service, "latest", lambda _id: record)

    created = client.post("/experiments/exp-sample/demo-model-admission", json={
        "campaignId": "campaign-1", "trialId": "trial-best", "operator": "负责人", "reason": "隔离演示",
    })
    fetched = client.get("/experiments/exp-sample/demo-model-admission")

    assert created.status_code == 200 and fetched.status_code == 200
    assert created.json()["scope"] == "isolated_sample_demo"
    assert created.json()["demoModelVersion"] == "demo-trial-best"


def test_sample_simulation_uses_demo_admission_without_formal_registry(monkeypatch) -> None:
    overview = SimpleNamespace(
        sourceType="sample", targetProduct="藻类培养产物", modelVersion="demo-trial-best",
        modelType="隔离演示 · RandomForestRegressor", confidenceScore=0.79,
    )
    monkeypatch.setattr(simulation_module.experiment_service, "get_workspace_overview", lambda _id: overview)
    monkeypatch.setattr(simulation_module.experiment_service, "is_persisted_workspace", lambda _id: True)
    monkeypatch.setattr(simulation_module.experiment_service, "get_official_process_parameters", lambda _id: None)
    monkeypatch.setattr(simulation_module.demo_model_admission_service, "require_active", lambda _id: admission())
    monkeypatch.setattr(simulation_module.demo_model_admission_service, "latest", lambda _id: admission())
    monkeypatch.setattr(
        simulation_module.promoted_model_registry, "latest_per_target",
        lambda _id: (_ for _ in ()).throw(AssertionError("formal registry must not be read")),
    )

    run = SimulationRunOrchestrator().create("exp-sample")

    assert run.admissionAllowed is True
    assert run.modelVersion == "demo-trial-best"
    assert run.modelType.startswith("隔离演示")
    assert run.bindingVersions == []
    assert run.modelMetrics["演示可靠性"] == "79.0%"


def test_completed_sample_simulation_opens_rule_demo_optimization(monkeypatch) -> None:
    record = admission()
    simulation = SimpleNamespace(
        runId="simulation-demo-1", status="completed", modelVersion=record.demoModelVersion,
        bindingVersions=[], officialResult=SimpleNamespace(snapshotId="official-demo-1"),
    )
    overview = SimpleNamespace(
        sourceType="sample", modelVersion=record.demoModelVersion, resultVersion="official-demo-1",
    )
    monkeypatch.setattr(optimization_module.experiment_service, "get_workspace_overview", lambda _id: overview)
    monkeypatch.setattr(optimization_module.experiment_service, "is_persisted_workspace", lambda _id: True)
    monkeypatch.setattr(optimization_module.demo_model_admission_service, "require_active", lambda _id: record)
    monkeypatch.setattr(optimization_module.simulation_run_orchestrator, "peek_latest", lambda _id: simulation)
    monkeypatch.setattr(optimization_module.product_requirement_registry, "latest", lambda _id: None)

    run = OptimizationOrchestrator().latest("exp-sample")

    assert run.admissionAllowed is True
    assert run.searchMode == "rule_demo"
    assert run.baseSimulationRunId == "simulation-demo-1"
    assert len(run.candidatePlans) == 3


def test_sample_optimization_review_creates_demo_assets_without_formal_promotion(monkeypatch) -> None:
    record = admission()
    simulation = SimpleNamespace(
        runId="simulation-demo-1", status="completed", modelVersion=record.demoModelVersion,
        bindingVersions=[], officialResult=SimpleNamespace(snapshotId="official-demo-1"),
    )
    overview = SimpleNamespace(
        sourceType="sample", modelVersion=record.demoModelVersion, resultVersion="official-demo-1",
    )
    monkeypatch.setattr(optimization_module.experiment_service, "get_workspace_overview", lambda _id: overview)
    monkeypatch.setattr(optimization_module.experiment_service, "is_persisted_workspace", lambda _id: True)
    monkeypatch.setattr(optimization_module.experiment_service, "mark_optimization_started", lambda _run: None)
    monkeypatch.setattr(
        optimization_module.experiment_service,
        "promote_versions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("formal versions must not be promoted")),
    )
    monkeypatch.setattr(
        optimization_module.experiment_service,
        "promote_optimization_result",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("formal process versions must not be promoted")),
    )
    monkeypatch.setattr(optimization_module.demo_model_admission_service, "require_active", lambda _id: record)
    monkeypatch.setattr(optimization_module.simulation_run_orchestrator, "peek_latest", lambda _id: simulation)
    monkeypatch.setattr(optimization_module.product_requirement_registry, "latest", lambda _id: None)

    orchestrator = OptimizationOrchestrator()
    run = orchestrator.create("exp-sample")
    parameters = OptimizationParameters(temperatureC=36.8, ph=6.82, cultureHours=46, stirringRpm=195)
    run = orchestrator.select("exp-sample", run.runId, "candidate-balanced", parameters)
    run = orchestrator.submit("exp-sample", run.runId)
    assert run.trainingDataVersion.startswith("demo-dataset-opt-")
    assert run.events[-1].title == "演示优化任务已提交"
    for _ in range(3):
        run = orchestrator.advance("exp-sample", run.runId)
    stage_evidence = " ".join(item for stage in run.retrainingStages for item in stage.outputSummary)
    assert "mock" not in stage_evidence
    assert "新模型" not in stage_evidence
    assert "规则代理" in stage_evidence
    run = orchestrator.review(
        "exp-sample", run.runId, "approved", "确认演示流程", "研发负责人", ["demo-only"],
    )

    assert run.status == "completed"
    assert run.newModelVersion is None
    assert run.officialParameterVersion.startswith("demo-process-parameters-")
    assert run.newResultVersion.startswith("demo-predicted-result-")
    assert run.resultSummary is not None
    assert "隔离演示" in run.resultSummary.disclaimer


def test_sample_optimization_can_restart_without_deleting_audit_history(monkeypatch) -> None:
    record = admission()
    simulation = SimpleNamespace(
        runId="simulation-demo-1", status="completed", modelVersion=record.demoModelVersion,
        bindingVersions=[], officialResult=SimpleNamespace(snapshotId="official-demo-1"),
    )
    overview = SimpleNamespace(
        sourceType="sample", modelVersion=record.demoModelVersion, resultVersion="official-demo-1",
    )
    monkeypatch.setattr(optimization_module.experiment_service, "get_workspace_overview", lambda _id: overview)
    monkeypatch.setattr(optimization_module.experiment_service, "is_persisted_workspace", lambda _id: True)
    monkeypatch.setattr(optimization_module.experiment_service, "mark_optimization_started", lambda _run: None)
    monkeypatch.setattr(optimization_module.demo_model_admission_service, "require_active", lambda _id: record)
    monkeypatch.setattr(optimization_module.simulation_run_orchestrator, "peek_latest", lambda _id: simulation)
    monkeypatch.setattr(optimization_module.product_requirement_registry, "latest", lambda _id: None)

    orchestrator = OptimizationOrchestrator()
    original = orchestrator.create("exp-sample")
    restarted = orchestrator.restart_demo("exp-sample", original.runId)

    assert restarted.runId != original.runId
    assert restarted.version == 2
    assert restarted.status == "draft"
    assert len(restarted.candidatePlans) == 3
    history = orchestrator.list_runs("exp-sample")
    assert [run.status for run in history] == ["stopped", "draft"]
    assert history[0].events[-1].eventType == "demoRestarted"
