from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AgentCommandStatus = Literal["queued", "leased", "completed", "failed", "deadLetter", "cancelled"]


class AgentCommandCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    experimentId: str = Field(min_length=1, max_length=128)
    runId: str = Field(min_length=1, max_length=128)
    targetKind: Literal["dataAnalysis", "simulation", "optimization", "research", "adaptation"] = "dataAnalysis"
    action: Literal["advance", "stop", "simulationCreate", "simulationAdvance", "simulationStop", "simulationRetry", "optimizationCreate", "optimizationSubmit", "optimizationAdvance", "researchTrial", "featureBindingSuggest"]
    expectedRevision: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    maxAttempts: int = Field(default=3, ge=1, le=10)
    priority: int = Field(default=0, ge=-10, le=10)
    parentTaskId: str | None = None
    requiredCapabilities: list[Literal["cpu", "gpu", "localLlm"]] = Field(default_factory=lambda: ["cpu"])


class AgentCommandTask(AgentCommandCreate):
    taskId: str
    requestFingerprint: str
    status: AgentCommandStatus
    attempts: int = Field(ge=0)
    availableAt: str
    leaseOwner: str | None = None
    leaseToken: str | None = None
    leaseExpiresAt: str | None = None
    heartbeatAt: str | None = None
    resultRevision: int | None = None
    resultRunId: str | None = None
    cancelRequestedAt: str | None = None
    cancelledAt: str | None = None
    errorCategory: str | None = None
    errorMessage: str | None = None
    createdAt: str
    updatedAt: str


class AgentCommandSummary(BaseModel):
    taskId: str
    commandId: str
    experimentId: str
    runId: str
    targetKind: str
    action: str
    status: AgentCommandStatus
    attempts: int = Field(ge=0)
    maxAttempts: int = Field(ge=1)
    priority: int
    resultRevision: int | None = None
    resultRunId: str | None = None
    errorCategory: str | None = None
    createdAt: str
    updatedAt: str


class AgentCommandEnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    action: Literal["advance", "stop"]
    expectedRevision: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    maxAttempts: int = Field(default=3, ge=1, le=10)
    priority: int = Field(default=0, ge=-10, le=10)


class UnifiedAgentCommandEnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    targetKind: Literal["simulation", "optimization"]
    runId: str = Field(min_length=1, max_length=128)
    action: Literal["simulationCreate", "simulationAdvance", "simulationStop", "simulationRetry", "optimizationCreate", "optimizationSubmit", "optimizationAdvance"]
    expectedRevision: int = Field(default=1, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    maxAttempts: int = Field(default=3, ge=1, le=10)
    priority: int = Field(default=0, ge=-10, le=10)

    @model_validator(mode="after")
    def validate_target_action(self):
        if not self.action.startswith(self.targetKind):
            raise ValueError("action does not belong to targetKind")
        return self


class AgentCommandReplayRequest(BaseModel):
    commandId: str = Field(min_length=1, max_length=128)


class AgentCommandCancelRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class AgentQueueStatus(BaseModel):
    backend: Literal["memory-sqlite", "sqlite", "postgres", "dramatiq-redis"]
    persistent: bool
    counts: dict[str, int]
    workerProcessRequired: bool = True
    requestedBackend: str = "sqlite"
    fallbackReason: str | None = None
    dispatchBackend: Literal["polling", "dramatiq-redis"] = "polling"
    workers: list["AgentWorkerStatus"] = Field(default_factory=list)


class AgentWorkerStatus(BaseModel):
    workerId: str
    capabilities: list[str]
    maxConcurrent: int = Field(ge=1)
    labels: dict[str, str] = Field(default_factory=dict)
    heartbeatAt: str
    status: Literal["online", "offline"]
    activeTasks: int = Field(default=0, ge=0)
    availableSlots: int = Field(default=0, ge=0)
