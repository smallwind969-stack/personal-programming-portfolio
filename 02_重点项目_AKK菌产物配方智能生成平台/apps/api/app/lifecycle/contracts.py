from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LifecycleStageKey = Literal[
    "dataAnalysis", "modelEvaluation", "supplementaryDesign",
    "supplementaryExecution", "measurementFeedback", "feedbackRetraining",
]
LifecycleStatus = Literal[
    "waiting", "running", "needsReview", "completed", "failed", "notRequired",
]


class ExperimentLifecycleStage(BaseModel):
    stageKey: LifecycleStageKey
    label: str
    status: LifecycleStatus
    progressPercent: int = Field(ge=0, le=100)
    route: str
    actionLabel: str
    canEnter: bool
    summary: str
    waitingReasons: list[str] = Field(default_factory=list)
    evidenceRefs: list[str] = Field(default_factory=list)
    itemCounts: dict[str, int] = Field(default_factory=dict)


class ExperimentLifecycleOverview(BaseModel):
    experimentId: str
    experimentName: str
    currentStageKey: LifecycleStageKey | None
    currentStageLabel: str
    overallStatus: LifecycleStatus
    progressPercent: int = Field(ge=0, le=100)
    stages: list[ExperimentLifecycleStage] = Field(min_length=6, max_length=6)
    generatedAt: str
    disclaimer: str = "闭环总览只读投影现有证据，不推进智能体、不生成实验结果、不控制设备。"


class ExperimentLifecycleSummary(BaseModel):
    experimentId: str
    currentStageKey: LifecycleStageKey | None
    currentStageLabel: str
    overallStatus: LifecycleStatus
    progressPercent: int = Field(ge=0, le=100)
    nextAction: str
    route: str
    waitingReasons: list[str]
    evidenceRefs: list[str]
