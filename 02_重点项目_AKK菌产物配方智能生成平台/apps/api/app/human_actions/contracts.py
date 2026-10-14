from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.lifecycle.contracts import LifecycleStageKey


HumanActionType = Literal[
    "reviewReliability", "generateDesign", "reviewDesign",
    "createExecution", "continueExecution", "createMeasurement",
    "enterMeasurements", "reviewMeasurements", "createRetraining",
    "reviewRetraining",
]


class HumanActionItem(BaseModel):
    actionId: str
    experimentId: str
    experimentName: str
    stageKey: LifecycleStageKey
    actionType: HumanActionType
    priority: Literal["high", "medium", "normal"]
    title: str
    detail: str
    route: str
    sourceRef: str
    blockedReasons: list[str] = Field(default_factory=list)


class HumanActionCenter(BaseModel):
    totalCount: int = Field(ge=0)
    highPriorityCount: int = Field(ge=0)
    experimentCount: int = Field(ge=0)
    experimentActionCounts: dict[str, int]
    items: list[HumanActionItem]
    generatedAt: str
    disclaimer: str = "人工待办中心只读汇总现有业务状态；点击后仍需在对应工作台完成门禁和确认。"
