from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.optimization import OptimizationParameters


ExecutionBatchStatus = Literal[
    "planned", "inProgress", "awaitingData", "needsReview", "completed", "cancelled",
]
ExecutionStepStatus = Literal["pending", "inProgress", "completed"]


class SupplementaryExecutionBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    designRunId: str = Field(min_length=1)
    planVersion: str = Field(min_length=1)
    candidateId: str = Field(min_length=1)
    batchCode: str = Field(min_length=1, max_length=100)
    scale: Literal["lab", "pilot"]
    operator: str = Field(min_length=1, max_length=100)
    plannedAt: str = Field(min_length=1)
    replicateCount: int = Field(ge=3, le=100)
    samplingRequirements: list[str] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_requirements(self):
        normalized = [item.strip() for item in self.samplingRequirements]
        if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("sampling requirements must be non-empty and unique")
        self.samplingRequirements = normalized
        return self


class SupplementaryExecutionStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operator: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=2, max_length=1000)


class SupplementaryExecutionStepUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operator: str = Field(min_length=1, max_length=100)
    status: Literal["inProgress", "completed"]
    note: str = Field(min_length=2, max_length=2000)


class SupplementaryExecutionAssetAttach(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operator: str = Field(min_length=1, max_length=100)
    assetIds: list[str] = Field(min_length=1, max_length=100)
    note: str = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def unique_assets(self):
        if len(self.assetIds) != len(set(self.assetIds)):
            raise ValueError("asset IDs must be unique")
        return self


class SupplementaryExecutionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "rejected"]
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class SupplementaryExecutionStep(BaseModel):
    stepKey: Literal[
        "preparation", "equipmentCheck", "parameterExecution",
        "sampling", "dataArchive", "humanConfirmation",
    ]
    order: int = Field(ge=1)
    title: str
    requirement: str
    status: ExecutionStepStatus = "pending"
    operator: str | None = None
    note: str | None = None
    startedAt: str | None = None
    completedAt: str | None = None


class SupplementaryExecutionAsset(BaseModel):
    assetId: str
    originalName: str
    contentHash: str
    parseStatus: str
    integrityVerified: bool
    attachedBy: str
    attachedAt: str
    note: str


class SupplementaryExecutionEvent(BaseModel):
    eventId: str
    eventType: str
    title: str
    detail: str
    operator: str
    createdAt: str


class SupplementaryExecutionBatch(BaseModel):
    batchId: str
    experimentId: str
    commandId: str
    requestFingerprint: str
    designRunId: str
    planVersion: str
    candidateId: str
    strategyKey: str
    candidateName: str
    modelVersion: str
    reportId: str
    reportInputFingerprint: str
    batchCode: str
    scale: Literal["lab", "pilot"]
    status: ExecutionBatchStatus
    plannedAt: str
    replicateCount: int = Field(ge=3)
    samplingRequirements: list[str]
    frozenParameters: OptimizationParameters
    modelFeatureValues: dict[str, float]
    steps: list[SupplementaryExecutionStep]
    assets: list[SupplementaryExecutionAsset] = Field(default_factory=list)
    createdBy: str
    createdAt: str
    startedAt: str | None = None
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    completedAt: str | None = None
    events: list[SupplementaryExecutionEvent] = Field(default_factory=list)
    disclaimer: str = "执行批次只记录人工实验过程和真实上传数据；不生成虚构测量、不自动重训练模型、不直接控制设备。"
