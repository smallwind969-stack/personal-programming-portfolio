from pydantic import BaseModel


class RuntimeBackendCapability(BaseModel):
    backend: str
    installed: bool
    enabled: bool
    version: str | None = None
    capabilities: list[str]


class LocalModelCapability(BaseModel):
    configured: bool
    provider: str
    model: str
    endpointLabel: str
    liveProbeEndpoint: str


class AgentRuntimeStatus(BaseModel):
    requestedBackend: str
    effectiveBackend: str
    fallbackReason: str | None = None
    backends: list[RuntimeBackendCapability]
    localModel: LocalModelCapability
    executionBoundary: list[str]
    checkpointBackend: str
    persistent: bool
    recoverableRuns: int
