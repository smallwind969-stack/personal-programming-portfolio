from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_command_service import agent_command_queue
from app.services.agent_command_worker import AgentCommandWorker
from app.services.agent_orchestrator import agent_orchestrator
from app.agent_runtime.langgraph_adapter import LangGraphRuntimeAdapter
from app.agent_queue.sqlite_queue import SqliteAgentCommandQueue
from app.schemas.agent_commands import AgentCommandCreate
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.domain_run_store import SqliteDomainRunStore
from app.services.simulation_run_orchestrator import SimulationRunOrchestrator
from app.services.optimization_orchestrator import OptimizationOrchestrator
from app.schemas.simulation import ExperimentSimulationRun
from app.schemas.optimization import ExperimentOptimizationRun
from app.feature_binding_advisor.contracts import FeatureBindingSuggestionRun
from app.feature_binding_advisor.contracts import DeviceAdapterPackSelector


client = TestClient(app)


def setup_function() -> None:
    agent_command_queue.reset()
    agent_orchestrator._runs.clear()
    agent_orchestrator._run_ids_by_experiment.clear()


def test_api_enqueues_without_advancing_and_worker_commits_result() -> None:
    run = client.post("/experiments/exp-food-012/agent-runs").json()
    response = client.post(
        f"/experiments/exp-food-012/agent-runs/{run['runId']}/commands",
        json={"commandId": "async-advance-1", "action": "advance", "expectedRevision": run["runtimeRevision"], "payload": {}, "maxAttempts": 3},
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "queued"
    assert task["requiredCapabilities"] == ["cpu"]
    assert agent_orchestrator.get_run("exp-food-012", run["runId"]).runtimeRevision == run["runtimeRevision"]

    result = AgentCommandWorker(agent_command_queue, agent_orchestrator, "test-worker").run_once()
    assert result is not None and result.status == "completed"
    assert result.resultRevision > run["runtimeRevision"]
    queried = client.get(f"/agent-runtime/commands/{task['taskId']}").json()
    assert queried["status"] == "completed"


def test_worker_marks_revision_conflict_as_dead_letter() -> None:
    run = client.post("/experiments/exp-food-012/agent-runs").json()
    client.post(
        f"/experiments/exp-food-012/agent-runs/{run['runId']}/commands",
        json={"commandId": "stale-advance", "action": "advance", "expectedRevision": run["runtimeRevision"] + 10, "payload": {}, "maxAttempts": 3},
    )
    result = AgentCommandWorker(agent_command_queue, agent_orchestrator, "test-worker").run_once()
    assert result.status == "deadLetter"
    assert result.errorCategory == "conflict"
    assert result.attempts == 1


def test_queue_status_discloses_backend_and_counts() -> None:
    response = client.get("/agent-runtime/queue/status")
    assert response.status_code == 200
    body = response.json()
    assert body["backend"] in {"memory-sqlite", "sqlite"}
    assert body["workerProcessRequired"] is True
    assert set(body["counts"]) >= {"queued", "leased", "completed", "deadLetter"}


def test_recent_command_api_is_read_only_and_omits_payload_and_lease_tokens() -> None:
    agent_command_queue.enqueue(AgentCommandCreate(
        commandId="recent-safe", experimentId="exp-food-012", runId="run-safe",
        action="advance", expectedRevision=1, payload={"private": "must-not-leak"},
    ))

    response = client.get("/agent-runtime/commands?limit=10")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["commandId"] == "recent-safe"
    assert "payload" not in item
    assert "leaseToken" not in item
    assert "requestFingerprint" not in item
    assert "must-not-leak" not in response.text


def test_command_cancel_and_dead_letter_replay_api() -> None:
    run = client.post("/experiments/exp-food-012/agent-runs").json()
    queued = client.post(f"/experiments/exp-food-012/agent-runs/{run['runId']}/commands", json={
        "commandId": "cancel-api", "action": "advance", "expectedRevision": run["runtimeRevision"], "payload": {}, "maxAttempts": 1,
    }).json()
    cancelled = client.post(f"/agent-runtime/commands/{queued['taskId']}/cancel", json={"reason": "用户调整实验计划"})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"

    stale = client.post(f"/experiments/exp-food-012/agent-runs/{run['runId']}/commands", json={
        "commandId": "dead-api", "action": "advance", "expectedRevision": run["runtimeRevision"] + 20, "payload": {}, "maxAttempts": 1,
    }).json()
    dead = AgentCommandWorker(agent_command_queue, agent_orchestrator, "test-worker").run_once()
    assert dead.taskId == stale["taskId"] and dead.status == "deadLetter"
    replayed = client.post(f"/agent-runtime/commands/{dead.taskId}/replay", json={"commandId": "replay-api"})
    assert replayed.status_code == 200 and replayed.json()["parentTaskId"] == dead.taskId


def test_separate_worker_orchestrator_recovers_mapping_and_api_observes_revision(tmp_path) -> None:
    runtime_path = tmp_path / "shared-runtime.db"
    queue = SqliteAgentCommandQueue(tmp_path / "shared-queue.db")
    api_orchestrator = AgentOrchestrator(LangGraphRuntimeAdapter(runtime_path), "langgraph-sqlite")
    created = api_orchestrator.create_run("exp-shared")
    queue.enqueue(AgentCommandCreate(
        commandId="cross-process-1", experimentId="exp-shared", runId=created.runId,
        action="advance", expectedRevision=created.runtimeRevision, payload={}, maxAttempts=3,
    ))

    worker_orchestrator = AgentOrchestrator(LangGraphRuntimeAdapter(runtime_path), "langgraph-sqlite")
    completed_task = AgentCommandWorker(queue, worker_orchestrator, "separate-worker").run_once()
    assert completed_task.status == "completed"
    observed = api_orchestrator.get_run("exp-shared", created.runId)
    assert observed.runtimeRevision == completed_task.resultRevision
    assert observed.currentNodeId == "schema-recognition"


def test_worker_dispatches_simulation_and_optimization_commands(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "commands.db")
    simulation = SimulationRunOrchestrator(SqliteDomainRunStore(tmp_path / "domains.db", "simulation", ExperimentSimulationRun))
    optimization = OptimizationOrchestrator(SqliteDomainRunStore(tmp_path / "domains.db", "optimization", ExperimentOptimizationRun))
    worker = AgentCommandWorker(queue, agent_orchestrator, "domain-worker", simulation=simulation, optimization=optimization)

    queue.enqueue(AgentCommandCreate(commandId="sim-create", experimentId="exp-food-012", runId="new", targetKind="simulation", action="simulationCreate", expectedRevision=1))
    sim_task = worker.run_once()
    assert sim_task.status == "completed" and sim_task.resultRunId.startswith("simulation-run-")
    queue.enqueue(AgentCommandCreate(commandId="sim-advance", experimentId="exp-food-012", runId=sim_task.resultRunId, targetKind="simulation", action="simulationAdvance", expectedRevision=1))
    assert worker.run_once().status == "completed"

    optimization_run = optimization.create("exp-food-012")
    plan = optimization_run.candidatePlans[0]
    optimization.select("exp-food-012", optimization_run.runId, plan.planId, plan.parameters)
    queue.enqueue(AgentCommandCreate(commandId="opt-submit", experimentId="exp-food-012", runId=optimization_run.runId, targetKind="optimization", action="optimizationSubmit", expectedRevision=1))
    opt_task = worker.run_once()
    assert opt_task.status == "completed" and optimization.latest("exp-food-012").status == "running"


def test_worker_dispatches_feature_binding_advisor_command(tmp_path) -> None:
    class Advisor:
        def create_run(self, experiment_id: str, model_version: str, command_id: str, adapter_selector=None):
            assert (experiment_id, model_version, command_id) == ("exp-real", "model-v1", "binding-command")
            assert adapter_selector == DeviceAdapterPackSelector(
                enterpriseKey="enterprise-a", deviceType="reactor", packVersion="1.0.0",
            )
            return FeatureBindingSuggestionRun(
                runId="binding-run-1", experimentId=experiment_id, modelVersion=model_version,
                commandId=command_id, status="completed", mode="rule_only", provider="none", model="none",
                candidateCount=0, reviewCount=0, conflictCount=0, rejectedCount=0,
                readyForConfirmation=True, candidates=[], createdAt="2026-07-20T00:00:00Z",
            )

    queue = SqliteAgentCommandQueue(tmp_path / "binding-commands.db")
    worker = AgentCommandWorker(queue, agent_orchestrator, "binding-worker", binding_advisor=Advisor())
    queued = queue.enqueue(AgentCommandCreate(
        commandId="binding-command", experimentId="exp-real", runId="model-v1",
        targetKind="adaptation", action="featureBindingSuggest", expectedRevision=1,
        payload={"adapterPack": {
            "enterpriseKey": "enterprise-a", "deviceType": "reactor", "packVersion": "1.0.0",
        }},
    ))

    completed = worker.run_once()

    assert completed.taskId == queued.taskId
    assert completed.status == "completed"
    assert completed.resultRunId == "binding-run-1"
