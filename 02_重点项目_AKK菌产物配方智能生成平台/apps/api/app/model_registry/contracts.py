from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NumericRange(BaseModel):
    min: float
    max: float


class PromotedModelRecord(BaseModel):
    modelVersion: str
    experimentId: str
    campaignId: str
    trialId: str
    artifactFingerprint: str
    artifactUri: str
    datasetSnapshotId: str
    datasetFingerprint: str
    runnerKey: str
    modelType: str
    featureNames: list[str] = Field(min_length=1)
    targetField: str
    targetUnit: str | None = None
    modelCategory: str = "enterprise_experiment"
    dataManifestUri: str | None = None
    uncertaintyMetric: str | None = None
    featureRanges: dict[str, NumericRange]
    metrics: dict[str, float]
    approvedBy: str
    approvalReason: str
    approvedAt: str
    status: str = "approved"
    validationStatus: Literal["passed", "failed", "pending"] = "passed"
    active: bool = True


class PromotedModelPrediction(BaseModel):
    predictionSource: Literal["promoted_model"] = "promoted_model"
    experimentId: str
    modelVersion: str
    trialId: str
    datasetSnapshotId: str
    datasetFingerprint: str
    artifactFingerprint: str
    targetField: str
    targetUnit: str | None = None
    modelCategory: str = "enterprise_experiment"
    dataManifestUri: str | None = None
    uncertainty: float | None = None
    featureRanges: dict[str, NumericRange] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    prediction: float
    extrapolated: bool
    outOfRangeFeatures: list[str]
    featureValues: dict[str, float]


class PromotedModelPredictRequest(BaseModel):
    inputs: dict[str, Any] = Field(min_length=1)
    modelVersion: str | None = None
    allowExtrapolation: bool = False
