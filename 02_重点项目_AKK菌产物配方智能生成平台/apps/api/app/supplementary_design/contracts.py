from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.optimization import OptimizationParameters


class SupplementaryDesignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    reportId: str = Field(min_length=1)


class SupplementaryDesignSelection(BaseModel):
    candidateIds: list[str] = Field(min_length=1, max_length=3)


class SupplementaryDesignReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "rejected"]
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class SupplementaryExperimentCandidate(BaseModel):
    candidateId: str
    strategyKey: Literal["coverageRecovery", "boundaryValidation", "residualCorrection"]
    displayName: str
    summary: str
    modelFeatureValues: dict[str, float]
    processParameters: OptimizationParameters
    exploratoryPrediction: float
    intervalLower: float
    intervalUpper: float
    intervalMethod: str
    informationGainScore: float = Field(ge=0, le=1)
    boundaryRiskScore: float = Field(ge=0, le=1)
    extrapolated: bool = False
    addressesGaps: list[str] = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    requiresHumanConfirmation: bool = True


class SupplementaryDesignEvent(BaseModel):
    eventId: str
    eventType: str
    title: str
    detail: str
    createdAt: str


class SupplementaryExperimentDesignRun(BaseModel):
    runId: str
    experimentId: str
    commandId: str
    requestFingerprint: str
    status: Literal["needsReview", "approved", "rejected"]
    reportId: str
    reportInputFingerprint: str
    reliabilityScore: float = Field(ge=0, le=1)
    modelVersion: str
    modelArtifactFingerprint: str
    datasetFingerprint: str
    bindingVersion: str | None = None
    bindingSource: Literal["confirmed_binding", "standard_alias_fallback"]
    admissionReasons: list[str]
    candidates: list[SupplementaryExperimentCandidate] = Field(min_length=3, max_length=3)
    selectedCandidateIds: list[str] = Field(default_factory=list, max_length=3)
    planVersion: str | None = None
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    events: list[SupplementaryDesignEvent] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
    disclaimer: str = "补实验方案仅作为研发实验建议；批准只冻结实验计划，不生成真实结果、不重训练模型、不直接控制设备。"
