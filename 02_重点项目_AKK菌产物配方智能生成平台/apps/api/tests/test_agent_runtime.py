import pytest

from app.agent_runtime.contracts import (
    RuntimeCommand,
    RuntimeConflictError,
    RuntimeContext,
    RuntimeGraphDefinition,
    RuntimeNodeDefinition,
)
from app.agent_runtime.deterministic import DeterministicRuntimeAdapter


def graph() -> RuntimeGraphDefinition:
    return RuntimeGraphDefinition(
        graphId="analysis-v1",
        nodes=[
            RuntimeNodeDefinition(nodeId="collect", displayName="数据收集定位", handlerKey="collect"),
            RuntimeNodeDefinition(nodeId="model", displayName="数学建模", handlerKey="model"),
            RuntimeNodeDefinition(nodeId="review", displayName="人工确认", handlerKey="review", requiresHuman=True),
        ],
        edges={"collect": "model", "model": "review"},
        entryNodeId="collect",
    )


def test_runtime_advances_only_along_declared_edges_and_emits_audit_events() -> None:
    runtime = DeterministicRuntimeAdapter()
    snapshot = runtime.start(graph(), {"experimentId": "exp-1"}, RuntimeContext(experimentId="exp-1"))
    assert snapshot.status == "running"
    assert snapshot.currentNodeId == "collect"
    snapshot = runtime.advance(snapshot.runId, RuntimeCommand(command="advance", expectedRevision=snapshot.revision))
    assert snapshot.nodes[0].status == "completed"
    assert snapshot.currentNodeId == "model"
    assert [event.eventType for event in runtime.events(snapshot.runId)][:2] == ["runStarted", "nodeCompleted"]


def test_runtime_interrupt_resume_and_human_gate_are_explicit() -> None:
    runtime = DeterministicRuntimeAdapter()
    run = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-1"))
    interrupted = runtime.interrupt(run.runId, "等待字段确认")
    assert interrupted.status == "interrupted"
    with pytest.raises(RuntimeConflictError):
        runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision))
    resumed = runtime.resume(run.runId, {"decision": "approved", "operator": "研发负责人"})
    assert resumed.status == "running"
    run = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=resumed.revision))
    waiting = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision))
    assert waiting.status == "needsReview"
    assert waiting.currentNodeId == "review"
    completed = runtime.resume(run.runId, {"decision": "approved", "operator": "研发负责人"})
    assert completed.status == "completed"


def test_runtime_commands_are_idempotent_and_runs_are_isolated() -> None:
    runtime = DeterministicRuntimeAdapter()
    first = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-1"))
    second = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-2"))
    command = RuntimeCommand(command="advance", commandId="cmd-1", expectedRevision=first.revision)
    once = runtime.advance(first.runId, command)
    twice = runtime.advance(first.runId, command)
    assert twice.currentNodeId == once.currentNodeId
    assert len(twice.events) == len(once.events)
    assert runtime.get(second.runId).currentNodeId == "collect"


def test_runtime_can_stop_at_human_review_gate() -> None:
    runtime = DeterministicRuntimeAdapter()
    run = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-1"))
    run = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision))
    waiting = runtime.advance(run.runId, RuntimeCommand(command="advance", expectedRevision=run.revision))
    assert waiting.status == "needsReview"
    stopped = runtime.advance(run.runId, RuntimeCommand(command="stop", expectedRevision=waiting.revision))
    assert stopped.status == "stopped"
    assert next(node for node in stopped.nodes if node.nodeId == "review").status == "stopped"
