from typing import Literal

from pydantic import BaseModel, Field


AnalysisStepKey = Literal[
    "dataIntake", "mappingReview", "cleaningAlignment",
    "datasetSnapshot", "featureEngineering", "modelingEvaluation",
]
AnalysisStepStatus = Literal["waiting", "running", "needsReview", "completed", "blocked"]


class DataAnalysisProgressStep(BaseModel):
    stepKey: AnalysisStepKey
    sequence: int = Field(ge=1, le=6)
    label: str
    status: AnalysisStepStatus
    current: bool = False
    summary: str
    actionLabel: str
    anchor: str
    evidenceRefs: list[str] = Field(default_factory=list)
    blockedReasons: list[str] = Field(default_factory=list)


class DataAnalysisProgress(BaseModel):
    experimentId: str
    experimentName: str
    sourceType: Literal["enterprise", "sample", "blank"]
    progressPercent: int = Field(ge=0, le=100)
    currentStepKey: AnalysisStepKey | None
    currentAction: str
    steps: list[DataAnalysisProgressStep] = Field(min_length=6, max_length=6)
    disclaimer: str
