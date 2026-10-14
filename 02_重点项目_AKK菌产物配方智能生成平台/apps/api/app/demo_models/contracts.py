from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DemoModelAdmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaignId: str = Field(min_length=1)
    trialId: str = Field(min_length=1)
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class DemoModelAdmission(BaseModel):
    admissionId: str
    experimentId: str
    status: Literal["active"] = "active"
    scope: Literal["isolated_sample_demo"] = "isolated_sample_demo"
    demoModelVersion: str
    campaignId: str
    trialId: str
    datasetSnapshotId: str
    datasetFingerprint: str
    artifactFingerprint: str
    artifactVerified: bool
    modelType: str
    featureNames: list[str]
    targetField: str
    metrics: dict[str, float]
    scoreBreakdown: dict[str, float] = Field(default_factory=dict)
    reliabilityScore: float = Field(ge=0, le=1)
    operator: str
    reason: str
    createdAt: str
    restrictions: list[str]
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str
