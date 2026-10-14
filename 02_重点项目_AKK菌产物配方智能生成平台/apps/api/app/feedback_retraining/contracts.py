from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackDerivedDataset(BaseModel):
    datasetId: str
    experimentId: str
    parentModelVersion: str
    parentDatasetSnapshotId: str
    parentDatasetFingerprint: str
    feedbackDatasetVersions: list[str] = Field(min_length=1)
    featureNames: list[str] = Field(min_length=1)
    targetField: str
    historicalRowCount: int = Field(ge=1)
    feedbackRowCount: int = Field(ge=1)
    trainingFeedbackRowCount: int = Field(ge=0)
    externalHoldoutRowCount: int = Field(ge=1)
    holdoutStartIndex: int = Field(ge=1)
    totalRowCount: int = Field(ge=2)
    rows: list[dict[str, float]] = Field(min_length=2)
    datasetFingerprint: str
    createdAt: str


class FeedbackRetrainingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    parentModelVersion: str = Field(min_length=1)
    feedbackDatasetVersions: list[str] = Field(min_length=3)
    fixedBudgetSeconds: int = Field(default=300, ge=10, le=86400)


class FeedbackRetrainingReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "rejected"]
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class FeedbackRetrainingStage(BaseModel):
    stageId: str
    stageKey: str
    stageName: str
    status: Literal["waiting", "running", "completed", "needsReview", "failed"]
    progressPercent: int = Field(ge=0, le=100)
    detail: str
    outputSummary: list[str] = Field(default_factory=list)
    startedAt: str | None = None
    completedAt: str | None = None


class FeedbackModelCandidate(BaseModel):
    trialId: str
    algorithm: str
    modelType: str | None = None
    metrics: dict[str, float]
    deltaFromIncumbent: dict[str, float]
    artifactFingerprint: str
    artifactVerified: bool


class FeedbackPromotionGate(BaseModel):
    eligible: bool
    checks: dict[str, bool]
    reasons: list[str]
    checkedAt: str


class FeedbackRetrainingEvent(BaseModel):
    eventId: str
    eventType: str
    title: str
    detail: str
    createdAt: str


class FeedbackRetrainingRun(BaseModel):
    runId: str
    experimentId: str
    commandId: str
    requestFingerprint: str
    status: Literal["running", "needsReview", "completed", "rejected", "failed"]
    parentModelVersion: str
    feedbackDatasetVersions: list[str]
    fixedBudgetSeconds: int = Field(ge=10, le=86400)
    derivedDatasetId: str
    derivedDatasetFingerprint: str
    historicalRowCount: int
    trainingFeedbackRowCount: int
    externalHoldoutRowCount: int
    researchCampaignId: str | None = None
    incumbentMetrics: dict[str, float] = Field(default_factory=dict)
    candidates: list[FeedbackModelCandidate] = Field(default_factory=list)
    championTrialId: str | None = None
    promotionGate: FeedbackPromotionGate | None = None
    stages: list[FeedbackRetrainingStage] = Field(min_length=5, max_length=5)
    currentStageId: str | None = None
    progressPercent: int = Field(ge=0, le=100)
    promotedModelVersion: str | None = None
    evaluationReportId: str | None = None
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    events: list[FeedbackRetrainingEvent] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
    disclaimer: str = "重训练候选仅作为研发实验建议；未经人工晋升和独立可靠性确认，不得进入仿真或真实生产控制。"
