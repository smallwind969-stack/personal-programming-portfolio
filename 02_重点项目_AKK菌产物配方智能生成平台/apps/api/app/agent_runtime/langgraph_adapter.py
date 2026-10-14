from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent_runtime.contracts import RuntimeCommand, RuntimeConflictError, RuntimeContext, RuntimeEvent, RuntimeGraphDefinition, RuntimeSnapshot
from app.agent_runtime.deterministic import _now, DeterministicRuntimeAdapter
from app.agent_runtime.sqlite_persistent import RuntimeCheckpointError, SqliteRuntimeCheckpointStore


class _GraphState(TypedDict, total=False):
    executedNodes: list[str]
    runtimeState: dict
    transitionPatch: dict


class LangGraphRuntimeAdapter(DeterministicRuntimeAdapter):
    """LangGraph topology executor with provider-neutral audit snapshots.

    With ``checkpoint_path`` both the official LangGraph SqliteSaver and the
    platform snapshot table use the same SQLite file under separate tables.
    """

    def __init__(self, checkpoint_path: str | Path | None = None) -> None:
        super().__init__()
        self._graphs: dict[str, object] = {}
        self._configs: dict[str, dict] = {}
        self._graph_started: set[str] = set()
        self._platform_store = SqliteRuntimeCheckpointStore(checkpoint_path) if checkpoint_path else None
        self._checkpoint_connection: sqlite3.Connection | None = None
        if checkpoint_path:
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver
            except ImportError as exc:
                raise RuntimeCheckpointError("official langgraph-checkpoint-sqlite package is required") from exc
            self._checkpoint_connection = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
            self._checkpointer = SqliteSaver(self._checkpoint_connection)
            for snapshot, definition, commands in self._platform_store.load_all():
                self._runs[snapshot.runId] = snapshot
                self._definitions[snapshot.runId] = definition
                self._processed_commands[snapshot.runId] = commands
        else:
            self._checkpointer = InMemorySaver()
        for run_id, definition in self._definitions.items():
            self._compile_graph(run_id, definition)
            checkpoint = self._graphs[run_id].get_state(self._configs[run_id])
            if checkpoint.values and checkpoint.values.get("executedNodes"):
                self._graph_started.add(run_id)
            self._annotate(run_id)
            self._validate_recovered_alignment(run_id)

    def start(self, definition: RuntimeGraphDefinition, initial_state: dict, context: RuntimeContext) -> RuntimeSnapshot:
        snapshot = DeterministicRuntimeAdapter.start(self, definition, initial_state, context)
        try:
            self._compile_graph(snapshot.runId, definition)
            self._annotate(snapshot.runId)
            self._persist(snapshot.runId)
            return self.get(snapshot.runId)
        except Exception:
            self._runs.pop(snapshot.runId, None)
            self._definitions.pop(snapshot.runId, None)
            self._processed_commands.pop(snapshot.runId, None)
            self._graphs.pop(snapshot.runId, None)
            self._configs.pop(snapshot.runId, None)
            raise

    def advance(self, run_id: str, command: RuntimeCommand) -> RuntimeSnapshot:
        with self._lock:
            before = self.get(run_id)
            if command.commandId in self._processed_commands[run_id]:
                return before
            if command.expectedRevision != before.revision:
                raise RuntimeConflictError(f"revision conflict: expected {command.expectedRevision}, current {before.revision}")
            if command.command == "advance" and (before.status != "running" or before.currentNodeId is None):
                raise RuntimeConflictError(f"run in {before.status} state cannot advance")
            if command.command == "stop" and before.status in {"completed", "stopped", "failed"}:
                raise RuntimeConflictError(f"run in {before.status} state cannot stop")
            if command.command == "advance":
                app = self._graphs[run_id]
                config = self._configs[run_id]
                graph_update = {"runtimeState": self._portable_state(before), "transitionPatch": command.statePatch}
                result = app.invoke({"executedNodes": [], **graph_update}, config) if run_id not in self._graph_started else self._continue_graph(app, config, graph_update)
                self._graph_started.add(run_id)
                if not result.get("executedNodes") or result["executedNodes"][-1] != before.currentNodeId:
                    raise RuntimeConflictError("LangGraph checkpoint diverged from platform snapshot")
            try:
                DeterministicRuntimeAdapter.advance(self, run_id, command)
            except Exception:
                self._mark_failed(run_id, "LangGraph checkpoint committed but platform projection failed")
                raise
            self._annotate(run_id)
            self._persist(run_id)
            return self.get(run_id)

    @staticmethod
    def _continue_graph(app, config: dict, update: dict) -> dict:
        app.update_state(config, update)
        return app.invoke(None, config)

    def patch_state(self, run_id: str, patch: dict, event_type: str, detail: str, expected_revision: int, command_id: str) -> RuntimeSnapshot:
        with self._lock:
            before = self.get(run_id)
            if command_id in self._processed_commands[run_id]:
                return before
            if expected_revision != before.revision:
                raise RuntimeConflictError(f"revision conflict: expected {expected_revision}, current {before.revision}")
            if run_id in self._graph_started:
                self._graphs[run_id].update_state(self._configs[run_id], {"runtimeState": {**self._portable_state(before), **patch}})
            try:
                DeterministicRuntimeAdapter.patch_state(self, run_id, patch, event_type, detail, expected_revision, command_id)
            except Exception:
                self._mark_failed(run_id, "LangGraph state patch committed but platform state commit failed")
                raise
            self._annotate(run_id)
            self._persist(run_id)
            return self.get(run_id)

    def resume(self, run_id: str, human_decision: dict) -> RuntimeSnapshot:
        with self._lock:
            before = self.get(run_id)
            provider_committed = False
            if before.status == "needsReview" and human_decision.get("decision") == "approved":
                result = self._graphs[run_id].invoke(None, self._configs[run_id])
                provider_committed = True
                if not result.get("executedNodes") or result["executedNodes"][-1] != before.currentNodeId:
                    raise RuntimeConflictError("LangGraph human gate checkpoint diverged")
            try:
                DeterministicRuntimeAdapter.resume(self, run_id, human_decision)
            except Exception:
                if provider_committed:
                    self._mark_failed(run_id, "LangGraph human gate committed but platform state commit failed")
                raise
            self._annotate(run_id)
            self._persist(run_id)
            return self.get(run_id)

    def interrupt(self, run_id: str, reason: str) -> RuntimeSnapshot:
        result = DeterministicRuntimeAdapter.interrupt(self, run_id, reason)
        self._persist(run_id)
        return result

    def refresh_all(self) -> None:
        if not self._platform_store:
            return
        with self._lock:
            for snapshot, definition, commands in self._platform_store.load_all():
                current = self._runs.get(snapshot.runId)
                if current is None or snapshot.revision > current.revision:
                    self._runs[snapshot.runId] = snapshot
                    self._definitions[snapshot.runId] = definition
                    self._processed_commands[snapshot.runId] = commands
                if snapshot.runId not in self._graphs:
                    self._compile_graph(snapshot.runId, definition)
                checkpoint = self._graphs[snapshot.runId].get_state(self._configs[snapshot.runId])
                if checkpoint.values and checkpoint.values.get("executedNodes"):
                    self._graph_started.add(snapshot.runId)
                self._annotate(snapshot.runId)
                self._validate_recovered_alignment(snapshot.runId)

    def list_snapshots(self) -> list[RuntimeSnapshot]:
        self.refresh_all()
        return DeterministicRuntimeAdapter.list_snapshots(self)

    def get(self, run_id: str) -> RuntimeSnapshot:
        if self._platform_store:
            loaded = self._platform_store.load_one(run_id)
            if loaded:
                snapshot, definition, commands = loaded
                current = self._runs.get(run_id)
                if current is None or snapshot.revision > current.revision:
                    self._runs[run_id] = snapshot
                    self._definitions[run_id] = definition
                    self._processed_commands[run_id] = commands
                    if run_id not in self._graphs:
                        self._compile_graph(run_id, definition)
        snapshot = DeterministicRuntimeAdapter.get(self, run_id)
        self._annotate(run_id)
        return DeterministicRuntimeAdapter.get(self, run_id)

    def _compile_graph(self, run_id: str, definition: RuntimeGraphDefinition) -> None:
        builder = StateGraph(_GraphState)
        for node in definition.nodes:
            node_id = node.nodeId
            builder.add_node(node_id, lambda state, current=node_id: {
                "executedNodes": [*state.get("executedNodes", []), current],
                "runtimeState": {**state.get("runtimeState", {}), **state.get("transitionPatch", {})},
                "transitionPatch": {},
            })
        builder.add_edge(START, definition.entryNodeId)
        targets = set(definition.edges.values())
        for source, target in definition.edges.items():
            builder.add_edge(source, target)
        for node in definition.nodes:
            if node.nodeId not in definition.edges and node.nodeId in targets | {definition.entryNodeId}:
                builder.add_edge(node.nodeId, END)
        self._graphs[run_id] = builder.compile(checkpointer=self._checkpointer, interrupt_after=[node.nodeId for node in definition.nodes])
        self._configs[run_id] = {"configurable": {"thread_id": run_id}}

    def _annotate(self, run_id: str) -> None:
        app = self._graphs.get(run_id)
        if app is None:
            return
        checkpoint = app.get_state(self._configs[run_id])
        stored = self._runs[run_id]
        stored.state["langGraph"] = {
            "enabled": True,
            "checkpointBackend": "sqlite" if self._platform_store else "memory",
            "executedNodes": list(checkpoint.values.get("executedNodes", [])) if checkpoint.values else [],
            "nextNodes": list(checkpoint.next),
            "checkpointed": bool(checkpoint.config),
            "runtimeStateSynchronized": checkpoint.values.get("runtimeState", {}) == self._portable_state(stored) if checkpoint.values else False,
        }

    @staticmethod
    def _portable_state(snapshot: RuntimeSnapshot) -> dict:
        return {key: value for key, value in snapshot.state.items() if key != "langGraph"}

    def _mark_failed(self, run_id: str, detail: str) -> None:
        stored = self._runs[run_id]
        stored.status = "failed"
        if stored.currentNodeId:
            next(node for node in stored.nodes if node.nodeId == stored.currentNodeId).status = "failed"
        stored.revision += 1
        stored.events.append(RuntimeEvent(eventType="providerCommitFailure", nodeId=stored.currentNodeId, detail=detail, createdAt=_now()))
        self._annotate(run_id)
        self._persist(run_id)

    def _validate_recovered_alignment(self, run_id: str) -> None:
        stored = self._runs[run_id]
        executed = stored.state.get("langGraph", {}).get("executedNodes", [])
        if stored.currentNodeId and executed and executed[-1] == stored.currentNodeId:
            raise RuntimeCheckpointError(
                f"checkpoint load failed: LangGraph provider state is ahead of platform snapshot for {run_id}"
            )

    def _persist(self, run_id: str) -> None:
        if self._platform_store:
            self._platform_store.save(self._runs[run_id], self._definitions[run_id], self._processed_commands[run_id])
