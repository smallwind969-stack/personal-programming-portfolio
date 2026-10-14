from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


UnifiedTaskStatus = Literal["waiting", "running", "interrupted", "needsReview", "completed", "failed", "stopped"]


class AgentTaskProjection(BaseModel):
    taskId: str
    agentKey: Literal["productInnovation", "dataAnalysis", "simulation", "optimization"]
    agentName: str
    agentKind: Literal["business", "workflow", "tool"] = "business"
    status: UnifiedTaskStatus
    progressPercent: int = Field(ge=0, le=100)
    route: str
    dependsOn: list[str]
    blockedReasons: list[str]
    runId: str | None = None
    version: int | None = None
    summary: str
    sourceRefs: list[str]
    canGuide: bool = False
    canRetry: bool = False


class AgentTaskCenter(BaseModel):
    experimentId: str
    overallStatus: UnifiedTaskStatus
    progressPercent: int = Field(ge=0, le=100)
    activeTaskIds: list[str]
    tasks: list[AgentTaskProjection] = Field(min_length=4, max_length=4)
    generatedAt: str
    disclaimer: Literal["研发实验建议"] = "研发实验建议"
