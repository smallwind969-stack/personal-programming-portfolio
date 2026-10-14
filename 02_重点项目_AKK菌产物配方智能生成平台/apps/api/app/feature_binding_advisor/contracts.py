from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BindingAdvisorContext(BaseModel):
    experimentId: str
    modelVersion: str
    featureNames: list[str] = Field(min_length=1)
    confirmedStandardFields: dict[str, str | None]
    featureRanges: dict[str, dict[str, float]]


class DeviceAdapterPackSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enterpriseKey: str = Field(min_length=1)
    deviceType: str = Field(min_length=1)
    packVersion: str = Field(min_length=1)


class DeviceAdapterPackReference(DeviceAdapterPackSelector):
    packId: str
    contentHash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class BindingLlmCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modelFeature: str
    simulationParameter: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)
    scale: float = 1.0
    offset: float = 0.0


class BindingSuggestionCandidate(BaseModel):
    modelFeature: str
    standardField: str
    simulationParameter: str | None
    sourceUnit: str | None = None
    targetUnit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    confidence: float = Field(ge=0, le=1)
    source: Literal["rule", "llm", "merged", "adapter"]
    evidence: list[str] = Field(min_length=1)
    requiresHumanReview: bool
    reviewReasons: list[str]


class FeatureBindingSuggestionRun(BaseModel):
    runId: str
    experimentId: str
    modelVersion: str
    commandId: str
    requestFingerprint: str = ""
    adapterPack: DeviceAdapterPackReference | None = None
    status: Literal["completed", "failed"]
    mode: Literal["rule_only", "llm_assisted", "rule_fallback"]
    provider: str
    model: str
    fallbackReason: str | None = None
    candidateCount: int
    reviewCount: int
    conflictCount: int
    rejectedCount: int
    readyForConfirmation: bool
    candidates: list[BindingSuggestionCandidate]
    activatedBindingVersion: None = None
    createdAt: str


class FeatureBindingSuggestionRunCreate(BaseModel):
    commandId: str = Field(min_length=1, max_length=128)
    adapterPack: DeviceAdapterPackSelector | None = None


class FeatureBindingSuggestionEnqueueRequest(BaseModel):
    commandId: str = Field(min_length=1, max_length=128)
    priority: int = Field(default=0, ge=-10, le=10)
    adapterPack: DeviceAdapterPackSelector | None = None
