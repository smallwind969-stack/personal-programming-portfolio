from app.agent_runtime.contracts import RuntimeCommand, RuntimeContext
from app.agent_runtime.contracts import RuntimeConflictError
import pytest
from app.services.agent_orchestrator import AgentOrchestrator
from app.agent_runtime.langgraph_adapter import LangGraphRuntimeAdapter
from app.agent_runtime.deterministic import DeterministicRuntimeAdapter
from test_agent_runtime import graph


def test_langgraph_adapter_executes_real_checkpointed_graph_one_node_per_command() -> None:
    runtime = LangGraphRuntimeAdapter()
    run = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-langgraph"))
    assert run.state["langGraph"]["enabled"] is True
    first = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision, commandId="lg-1"))
    assert first.currentNodeId == "model"
    assert first.state["langGraph"]["executedNodes"] == ["collect"]
    assert first.state["langGraph"]["nextNodes"] == ["model"]
    second = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=first.revision, commandId="lg-2"))
    assert second.status == "needsReview"
    approved = runtime.resume(run.runId, {"decision": "approved", "operator": "研发负责人"})
    assert approved.status == "completed"
    assert approved.state["langGraph"]["executedNodes"] == ["collect", "model", "review"]
    assert approved.state["langGraph"]["nextNodes"] == []


def test_langgraph_rejects_stale_revision_before_checkpoint_moves() -> None:
    runtime = LangGraphRuntimeAdapter()
    run = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-langgraph"))
    with pytest.raises(RuntimeConflictError):
        runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision + 1, commandId="stale"))
    assert runtime.get(run.runId).state["langGraph"]["executedNodes"] == []


def test_agent_orchestrator_can_run_seven_node_workflow_on_langgraph() -> None:
    orchestrator = AgentOrchestrator(runtime=LangGraphRuntimeAdapter(), runtime_backend="langgraph")
    run = orchestrator.create_run("exp-langgraph")
    for index in range(6):
        run = orchestrator.advance("exp-langgraph", run.runId, run.runtimeRevision, f"lg-business-{index}")
    assert run.status == "needsReview"
    assert run.runtimeBackend == "langgraph"
    completed = orchestrator.review("exp-langgraph", run.runId, "approved", "检查点与验证指标已复核", "研发负责人", ["model", "simulation"])
    assert completed.status == "completed"
    assert all(node.status == "completed" for node in completed.nodes)


def test_langgraph_checkpoint_contains_atomic_runtime_state_patch() -> None:
    runtime = LangGraphRuntimeAdapter()
    run = runtime.start(graph(), {"experimentId": "exp-langgraph"}, RuntimeContext(experimentId="exp-langgraph"))
    first = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision, commandId="patch-1"))
    second = runtime.advance(first.runId, RuntimeCommand(command="advance", expectedRevision=first.revision, commandId="patch-2", statePatch={"activeGuidance": {"guidanceId": "g-1"}}, patchEventType="guidanceApplied", patchDetail="应用人工字段规则"))
    assert second.state["activeGuidance"]["guidanceId"] == "g-1"
    assert second.state["langGraph"]["runtimeStateSynchronized"] is True


def test_needs_review_rejects_advance_without_moving_langgraph_checkpoint() -> None:
    runtime = LangGraphRuntimeAdapter()
    run = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-review-guard"))
    first = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision, commandId="guard-1"))
    review = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=first.revision, commandId="guard-2"))
    checkpoint_before = review.state["langGraph"]
    with pytest.raises(RuntimeConflictError):
        runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=review.revision, commandId="guard-illegal"))
    unchanged = runtime.get(run.runId)
    assert unchanged.revision == review.revision
    assert unchanged.state["langGraph"]["executedNodes"] == checkpoint_before["executedNodes"]
    assert unchanged.state["langGraph"]["nextNodes"] == checkpoint_before["nextNodes"]


def test_provider_commit_failure_marks_run_failed(monkeypatch) -> None:
    runtime = LangGraphRuntimeAdapter()
    run = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-commit-failure"))

    def fail_platform_commit(*args, **kwargs):
        raise RuntimeError("projection failed")

    monkeypatch.setattr(DeterministicRuntimeAdapter, "advance", fail_platform_commit)
    with pytest.raises(RuntimeError, match="projection failed"):
        runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision, commandId="failure-1"))
    failed = runtime.get(run.runId)
    assert failed.status == "failed"
    assert failed.events[-1].eventType == "providerCommitFailure"


def test_langgraph_sqlite_checkpoint_recovers_across_adapter_instances(tmp_path) -> None:
    path = tmp_path / "langgraph-runtime.db"
    first = LangGraphRuntimeAdapter(checkpoint_path=path)
    started = first.start(graph(), {"experimentId": "exp-recover"}, RuntimeContext(experimentId="exp-recover"))
    advanced = first.advance(started.runId, RuntimeCommand(command="advance", expectedRevision=started.revision, commandId="recover-1"))

    restored = LangGraphRuntimeAdapter(checkpoint_path=path)
    snapshot = restored.get(started.runId)
    assert snapshot.revision == advanced.revision
    assert snapshot.currentNodeId == "model"
    assert snapshot.state["langGraph"]["checkpointBackend"] == "sqlite"
    assert snapshot.state["langGraph"]["executedNodes"] == ["collect"]
    continued = restored.advance(started.runId, RuntimeCommand(command="advance", expectedRevision=snapshot.revision, commandId="recover-2"))
    assert continued.status == "needsReview"
