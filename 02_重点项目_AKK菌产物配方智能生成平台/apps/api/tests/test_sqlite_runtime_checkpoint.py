import sqlite3

import pytest

from app.agent_runtime.contracts import RuntimeCommand, RuntimeContext, RuntimeGraphDefinition, RuntimeNodeDefinition
from app.agent_runtime.sqlite_persistent import PersistentRuntimeAdapter, RuntimeCheckpointError


def graph() -> RuntimeGraphDefinition:
    return RuntimeGraphDefinition(
        graphId="persistent-test",
        nodes=[
            RuntimeNodeDefinition(nodeId="collect", displayName="采集", handlerKey="collect"),
            RuntimeNodeDefinition(nodeId="review", displayName="复核", handlerKey="review", requiresHuman=True),
        ],
        edges={"collect": "review"}, entryNodeId="collect",
    )


def test_runtime_recovers_snapshot_definition_events_and_commands(tmp_path) -> None:
    path = tmp_path / "runtime.db"
    first = PersistentRuntimeAdapter(path)
    started = first.start(graph(), {"experimentId": "exp-1"}, RuntimeContext(experimentId="exp-1"))
    command = RuntimeCommand(command="advance", commandId="advance-once", expectedRevision=started.revision)
    advanced = first.advance(started.runId, command)

    restored = PersistentRuntimeAdapter(path)
    snapshot = restored.get(started.runId)
    assert snapshot.model_dump() == advanced.model_dump()
    assert restored.events(started.runId) == advanced.events
    assert restored.advance(started.runId, command).revision == advanced.revision
    assert restored._definitions[started.runId].graphId == "persistent-test"


def test_recovered_runtime_preserves_cas_and_can_resume_human_gate(tmp_path) -> None:
    path = tmp_path / "runtime.db"
    runtime = PersistentRuntimeAdapter(path)
    started = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-1"))
    waiting = runtime.advance(started.runId, RuntimeCommand(command="advance", expectedRevision=started.revision))

    restored = PersistentRuntimeAdapter(path)
    with pytest.raises(Exception, match="revision conflict"):
        restored.patch_state(started.runId, {"bad": True}, "patch", "stale", started.revision, "stale-command")
    completed = restored.resume(started.runId, {"decision": "approved", "operator": "负责人"})
    assert completed.status == "completed"
    assert PersistentRuntimeAdapter(path).get(started.runId).status == "completed"


def test_checkpoint_write_failure_rolls_back_in_memory_state(tmp_path, monkeypatch) -> None:
    runtime = PersistentRuntimeAdapter(tmp_path / "runtime.db")
    started = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-1"))
    monkeypatch.setattr(runtime._store, "save", lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError("disk full")))
    with pytest.raises(RuntimeCheckpointError, match="checkpoint commit failed"):
        runtime.advance(started.runId, RuntimeCommand(command="advance", commandId="will-rollback", expectedRevision=started.revision))
    current = runtime.get(started.runId)
    assert current.revision == started.revision
    assert current.currentNodeId == "collect"


def test_corrupt_checkpoint_is_not_silently_ignored(tmp_path) -> None:
    path = tmp_path / "runtime.db"
    runtime = PersistentRuntimeAdapter(path)
    started = runtime.start(graph(), {}, RuntimeContext(experimentId="exp-1"))
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE agent_runtime_checkpoints SET snapshot_json = ? WHERE run_id = ?", ("not-json", started.runId))
    with pytest.raises(RuntimeCheckpointError, match="checkpoint load failed"):
        PersistentRuntimeAdapter(path)
