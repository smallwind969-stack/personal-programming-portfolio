from pydantic import BaseModel, Field


class LlmUsageRoute(BaseModel):
    routeKey: str
    label: str
    enabled: bool
    role: str
    fallback: str


class LlmStatus(BaseModel):
    enabled: bool
    provider: str
    model: str
    baseUrl: str
    available: bool
    mode: str
    apiKeyConfigured: bool = False
    endpointScope: str = "local"
    latencyMs: int | None = None
    failureCategory: str | None = None
    usageRoutes: list[LlmUsageRoute] = Field(default_factory=list)
    securityBoundaries: list[str] = Field(default_factory=list)
