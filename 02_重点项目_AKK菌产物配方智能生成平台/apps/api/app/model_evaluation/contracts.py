from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResidualDiagnostics(BaseModel):
    meanResidual: float
    residualStd: float
    meanAbsoluteResidual: float
    maxAbsoluteResidual: float
    lag1Autocorrelation: float
    predictionResidualCorrelation: float


class PredictionIntervalEvidence(BaseModel):
    method: Literal["empirical_holdout_absolute_error"]
    confidenceLevel: float = Field(ge=0, le=1)
    margin: float = Field(ge=0)
    empiricalCoverage: float = Field(ge=0, le=1)
    sampleCount: int = Field(ge=1)
    calibrated: bool = False
    limitation: str


class FeatureDriftDiagnostic(BaseModel):
    feature: str
    standardizedMeanShift: float = Field(ge=0)
    holdoutRangeCoverage: float = Field(ge=0, le=1)
    severity: Literal["low", "medium", "high"]
    trainMean: float
    holdoutMean: float


class ModelFeatureEffect(BaseModel):
    feature: str
    effect: float
    normalizedImportance: float = Field(ge=0, le=1)
    method: str


class ModelEvaluationReport(BaseModel):
    reportId: str
    experimentId: str
    reportVersion: int
    status: Literal["needsReview", "confirmed", "rejected"]
    modelVersion: str
    campaignId: str
    trialId: str
    modelType: str
    artifactFingerprint: str
    artifactVerified: bool
    datasetSnapshotId: str
    datasetFingerprint: str
    inputFingerprint: str
    performanceMetrics: dict[str, float]
    residualDiagnostics: ResidualDiagnostics
    predictionInterval: PredictionIntervalEvidence
    driftDiagnostics: list[FeatureDriftDiagnostic]
    featureEffects: list[ModelFeatureEffect]
    scoreBreakdown: dict[str, float]
    reliabilityScore: float = Field(ge=0, le=1)
    reliabilityGrade: Literal["low", "medium", "high"]
    recommendedAdmission: bool
    admissionAllowed: bool = False
    admissionReasons: list[str]
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    createdAt: str


class ModelEvaluationReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    operator: str = Field(min_length=1)
    reason: str = Field(min_length=2)
