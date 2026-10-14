from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchCampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    datasetSnapshotId: str = Field(min_length=1)
    agentKey: str = Field(min_length=1)
    baselineMetrics: dict[str, float]
    primaryMetric: Literal["r2", "mae", "rmse"] = "r2"
    direction: Literal["maximize", "minimize"] = "maximize"
    fixedBudgetSeconds: int = Field(default=300, ge=10, le=86400)
    minimumImprovement: float = Field(default=0.005, ge=0)
    promotionThresholds: dict[str, float] = Field(default_factory=lambda: {"r2": 0.75, "mae": 0.20})

    @model_validator(mode="after")
    def validate_metrics(self):
        missing = {"mae", "rmse", "r2"} - self.baselineMetrics.keys()
        if missing: raise ValueError(f"baseline metrics missing: {', '.join(sorted(missing))}")
        if self.direction == "maximize" and self.primaryMetric != "r2":
            raise ValueError("mae/rmse campaigns must minimize")
        return self


class ResearchTrialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    hypothesis: str = Field(min_length=2, max_length=500)
    parameterPatch: dict[str, Any] = Field(min_length=1)


class ResearchTrialEnqueueRequest(ResearchTrialCreate):
    priority: int = Field(default=0, ge=-10, le=10)


class ResearchIterationRequest(BaseModel):
    commandId: str = Field(min_length=1, max_length=128)
    priority: int = Field(default=0, ge=-10, le=10)


class ResearchPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trialId: str
    decision: Literal["approved", "rejected"]
    operator: str
    reason: str


class ResearchTrial(BaseModel):
    trialId: str
    sequence: int = Field(ge=0)
    commandId: str
    requestFingerprint: str
    hypothesis: str
    parameterPatch: dict[str, Any]
    metrics: dict[str, float]
    primaryScore: float
    status: Literal["keep", "discard", "crash"]
    comparedToTrialId: str | None = None
    deltaFromBestBefore: float
    deltaFromBaseline: float
    fixedBudgetSeconds: int
    durationSeconds: float
    artifactFingerprint: str
    artifactUri: str | None = None
    runnerKey: str
    datasetFingerprint: str | None = None
    featureNames: list[str] = Field(default_factory=list)
    targetField: str | None = None
    modelType: str | None = None
    featureRanges: dict[str, dict[str, float]] = Field(default_factory=dict)
    modelCard: dict[str, Any] | None = None
    errorMessage: str | None = None
    createdAt: str


class ResearchPromotion(BaseModel):
    trialId: str
    status: Literal["approved", "rejected"]
    operator: str
    reason: str
    gateChecks: dict[str, bool]
    promotedModelVersion: str | None = None
    createdAt: str


class ResearchCampaign(BaseModel):
    campaignId: str
    experimentId: str
    createCommandId: str
    requestFingerprint: str
    agentKey: str
    agentVersion: str
    datasetSnapshotId: str
    evaluationHarnessHash: str
    primaryMetric: str
    direction: Literal["maximize", "minimize"]
    fixedBudgetSeconds: int
    minimumImprovement: float
    promotionThresholds: dict[str, float]
    baselineTrialId: str
    bestTrialId: str
    status: Literal["active", "needsReview", "completed", "stopped"]
    trials: list[ResearchTrial]
    promotion: ResearchPromotion | None = None
    createdAt: str
    updatedAt: str
    mode: Literal["mock_evaluation", "real_runner"] = "mock_evaluation"
    runnerKey: str
    runnerFallbackReason: str | None = None
    disclaimer: Literal["研发实验建议"] = "研发实验建议"
