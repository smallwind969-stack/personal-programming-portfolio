from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.agent_runtime.contracts import (
    AgentRuntimeAdapter,
    RuntimeCommand,
    RuntimeConflictError,
    RuntimeContext,
    RuntimeEvent,
    RuntimeGraphDefinition,
    RuntimeNodeResult,
    RuntimeNodeState,
    RuntimeNotFoundError,
    RuntimeSnapshot,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeterministicRuntimeAdapter(AgentRuntimeAdapter):
    """Dependency-free runtime used by v1 and by contract tests.

    It exposes LangGraph-compatible concepts (graph, checkpoint snapshot,
    interrupt/resume and durable events) without claiming to execute an LLM.
    """

    def __init__(self) -> None:
        self._runs: dict[str, RuntimeSnapshot] = {}
        self._definitions: dict[str, RuntimeGraphDefinition] = {}
        self._processed_commands: dict[str, set[str]] = {}
        self._lock = RLock()

    def start(self, definition: RuntimeGraphDefinition, initial_state: dict, context: RuntimeContext) -> RuntimeSnapshot:
        with self._lock:
            run_id = f"runtime-{uuid4().hex[:12]}"
            nodes = [RuntimeNodeState(nodeId=node.nodeId, displayName=node.displayName) for node in definition.nodes]
            entry = next(node for node in nodes if node.nodeId == definition.entryNodeId)
            entry.status = "running"
            events = [RuntimeEvent(eventType="runStarted", nodeId=definition.entryNodeId, detail="状态图运行已创建", createdAt=_now())]
            if initial_state.get("activeGuidance"):
                events.append(RuntimeEvent(eventType="guidanceAppliedOnRestart", nodeId=definition.entryNodeId, detail=initial_state["activeGuidance"].get("intentSummary", "人工引导已写入新版本"), createdAt=_now()))
            snapshot = RuntimeSnapshot(
                runId=run_id, graphId=definition.graphId, experimentId=context.experimentId,
                status="running", currentNodeId=definition.entryNodeId,
                state=dict(initial_state), nodes=nodes,
                events=events,
            )
            self._runs[run_id] = snapshot
            self._definitions[run_id] = definition
            self._processed_commands[run_id] = set()
            return snapshot.model_copy(deep=True)

    def advance(self, run_id: str, command: RuntimeCommand) -> RuntimeSnapshot:
        with self._lock:
            run = self._get_mutable(run_id)
            if command.commandId in self._processed_commands[run_id]:
                return run.model_copy(deep=True)
            if command.expectedRevision != run.revision:
                raise RuntimeConflictError(f"revision conflict: expected {command.expectedRevision}, current {run.revision}")
            if command.command == "stop":
                if run.status in {"completed", "stopped", "failed"}:
                    raise RuntimeConflictError(f"run in {run.status} state cannot stop")
                self._processed_commands[run_id].add(command.commandId)
                if run.currentNodeId:
                    current = next(node for node in run.nodes if node.nodeId == run.currentNodeId)
                    current.status = "stopped"
                run.status = "stopped"; run.revision += 1
                self._event(run, "runStopped", run.currentNodeId, "运行已人工停止")
                return run.model_copy(deep=True)
            if run.status != "running" or run.currentNodeId is None:
                raise RuntimeConflictError(f"run in {run.status} state cannot advance")
            self._processed_commands[run_id].add(command.commandId)
            current = next(node for node in run.nodes if node.nodeId == run.currentNodeId)
            current.status = "completed"; current.progressPercent = 100
            configured = run.state.get("nodeResults", {}).get(current.nodeId)
            current.result = RuntimeNodeResult.model_validate(configured) if configured else RuntimeNodeResult(summary=[f"{current.displayName}确定性节点已完成"], evidenceRefs=[f"runtime://{run.runId}/{current.nodeId}"], confidenceScore=1.0)
            self._event(run, "nodeCompleted", current.nodeId, f"{current.displayName}已完成")
            next_id = self._definitions[run_id].edges.get(current.nodeId)
            if next_id is None:
                run.status = "completed"; run.currentNodeId = None
                self._event(run, "runCompleted", None, "状态图全部节点已完成")
            else:
                next_node = next(node for node in run.nodes if node.nodeId == next_id)
                run.currentNodeId = next_id
                definition = next(node for node in self._definitions[run_id].nodes if node.nodeId == next_id)
                next_node.status = "needsReview" if definition.requiresHuman else "running"
                run.status = "needsReview" if definition.requiresHuman else "running"
                self._event(run, "humanReviewRequired" if definition.requiresHuman else "nodeStarted", next_id, f"进入{next_node.displayName}")
            if command.statePatch:
                run.state.update(command.statePatch)
                self._event(run, command.patchEventType or "statePatched", run.currentNodeId, command.patchDetail or "运行时状态已更新")
            run.revision += 1
            return run.model_copy(deep=True)

    def interrupt(self, run_id: str, reason: str) -> RuntimeSnapshot:
        with self._lock:
            run = self._get_mutable(run_id)
            if run.status != "running":
                raise RuntimeConflictError(f"run in {run.status} state cannot be interrupted")
            run.status = "interrupted"; run.interruptReason = reason; run.revision += 1
            self._event(run, "runInterrupted", run.currentNodeId, reason)
            return run.model_copy(deep=True)

    def resume(self, run_id: str, human_decision: dict) -> RuntimeSnapshot:
        with self._lock:
            run = self._get_mutable(run_id)
            decision = human_decision.get("decision")
            if decision not in {"approved", "rejected"}:
                raise RuntimeConflictError("structured human decision is required")
            previous_status = run.status
            if run.status == "interrupted":
                run.status = "running" if decision == "approved" else "stopped"
                run.interruptReason = None
            elif run.status == "needsReview" and run.currentNodeId:
                review_node_id = run.currentNodeId
                node = next(node for node in run.nodes if node.nodeId == run.currentNodeId)
                node.status = "completed" if decision == "approved" else "stopped"
                node.progressPercent = 100
                node.result = RuntimeNodeResult(summary=[f"人工决定：{decision}"], evidenceRefs=[f"operator:{human_decision.get('operator', 'unknown')}"])
                run.status = "completed" if decision == "approved" else "stopped"
                run.currentNodeId = None
            else:
                raise RuntimeConflictError(f"run in {run.status} state cannot resume")
            run.revision += 1
            event_node_id = review_node_id if previous_status == "needsReview" else run.currentNodeId
            self._event(run, "humanDecisionRecorded" if previous_status == "needsReview" else "runResumed", event_node_id, f"人工决定：{decision}")
            return run.model_copy(deep=True)

    def get(self, run_id: str) -> RuntimeSnapshot:
        with self._lock:
            return self._get_mutable(run_id).model_copy(deep=True)

    def events(self, run_id: str) -> list[RuntimeEvent]:
        return self.get(run_id).events

    def list_snapshots(self) -> list[RuntimeSnapshot]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._runs.values()]

    def patch_state(self, run_id: str, patch: dict, event_type: str, detail: str, expected_revision: int, command_id: str) -> RuntimeSnapshot:
        with self._lock:
            run = self._get_mutable(run_id)
            if command_id in self._processed_commands[run_id]:
                return run.model_copy(deep=True)
            if expected_revision != run.revision:
                raise RuntimeConflictError(f"revision conflict: expected {expected_revision}, current {run.revision}")
            self._processed_commands[run_id].add(command_id)
            run.state.update(patch)
            run.revision += 1
            self._event(run, event_type, run.currentNodeId, detail)
            return run.model_copy(deep=True)

    def _get_mutable(self, run_id: str) -> RuntimeSnapshot:
        run = self._runs.get(run_id)
        if run is None:
            raise RuntimeNotFoundError(run_id)
        return run

    @staticmethod
    def _event(run: RuntimeSnapshot, event_type: str, node_id: str | None, detail: str) -> None:
        run.events.append(RuntimeEvent(eventType=event_type, nodeId=node_id, detail=detail, createdAt=_now()))
