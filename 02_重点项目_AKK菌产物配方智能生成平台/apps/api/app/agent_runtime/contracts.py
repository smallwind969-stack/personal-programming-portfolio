from __future__ import annotations

from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


RuntimeStatus = Literal["waiting", "running", "interrupted", "needsReview", "completed", "failed", "stopped"]


class RuntimeConflictError(RuntimeError):
    pass


class RuntimeNotFoundError(LookupError):
    pass


class RuntimeNodeDefinition(BaseModel):
    nodeId: str
    displayName: str
    handlerKey: str
    requiresHuman: bool = False


class RuntimeGraphDefinition(BaseModel):
    graphId: str
    nodes: list[RuntimeNodeDefinition] = Field(min_length=1)
    edges: dict[str, str]
    entryNodeId: str

    @model_validator(mode="after")
    def validate_graph(self):
        node_ids = {node.nodeId for node in self.nodes}
        if self.entryNodeId not in node_ids:
            raise ValueError("entryNodeId must reference a declared node")
        if any(source not in node_ids or target not in node_ids for source, target in self.edges.items()):
            raise ValueError("edges must reference declared nodes")
        return self


class RuntimeContext(BaseModel):
    experimentId: str
    actorId: str = "system"
    correlationId: str = Field(default_factory=lambda: f"corr-{uuid4().hex[:10]}")


class RuntimeCommand(BaseModel):
    command: Literal["advance", "stop"]
    commandId: str = Field(default_factory=lambda: f"cmd-{uuid4().hex[:10]}")
    expectedRevision: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    statePatch: dict[str, Any] = Field(default_factory=dict)
    patchEventType: str | None = None
    patchDetail: str | None = None


class RuntimeNodeResult(BaseModel):
    summary: list[str] = Field(default_factory=list)
    evidenceRefs: list[str] = Field(default_factory=list)
    confidenceScore: float | None = Field(default=None, ge=0, le=1)
    riskItems: list[str] = Field(default_factory=list)
    validationItems: list[str] = Field(default_factory=list)


class RuntimeNodeState(BaseModel):
    nodeId: str
    displayName: str
    status: RuntimeStatus = "waiting"
    progressPercent: int = Field(default=0, ge=0, le=100)
    result: RuntimeNodeResult | None = None


class RuntimeEvent(BaseModel):
    eventId: str = Field(default_factory=lambda: f"runtime-event-{uuid4().hex[:10]}")
    eventType: str
    nodeId: str | None = None
    detail: str
    createdAt: str


class RuntimeSnapshot(BaseModel):
    runId: str
    graphId: str
    experimentId: str
    status: RuntimeStatus
    currentNodeId: str | None
    state: dict[str, Any]
    nodes: list[RuntimeNodeState]
    events: list[RuntimeEvent]
    interruptReason: str | None = None
    revision: int = Field(default=1, ge=1)


class AgentRuntimeAdapter(Protocol):
    def start(self, definition: RuntimeGraphDefinition, initial_state: dict[str, Any], context: RuntimeContext) -> RuntimeSnapshot: ...
    def advance(self, run_id: str, command: RuntimeCommand) -> RuntimeSnapshot: ...
    def interrupt(self, run_id: str, reason: str) -> RuntimeSnapshot: ...
    def resume(self, run_id: str, human_decision: dict[str, Any]) -> RuntimeSnapshot: ...
    def get(self, run_id: str) -> RuntimeSnapshot: ...
    def events(self, run_id: str) -> list[RuntimeEvent]: ...
    def patch_state(self, run_id: str, patch: dict[str, Any], event_type: str, detail: str, expected_revision: int, command_id: str) -> RuntimeSnapshot: ...
    def list_snapshots(self) -> list[RuntimeSnapshot]: ...
