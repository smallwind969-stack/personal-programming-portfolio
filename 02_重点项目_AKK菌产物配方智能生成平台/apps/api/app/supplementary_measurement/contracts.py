from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.optimization import OptimizationParameters


class SupplementaryMeasurementBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1, max_length=128)
    executionBatchId: str = Field(min_length=1)
    operator: str = Field(min_length=1, max_length=100)


class SupplementaryMeasurementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metricName: str = Field(min_length=1, max_length=120)
    value: float
    unit: str = Field(min_length=1, max_length=40)
    replicate: int = Field(ge=1, le=1000)
    measuredAt: str = Field(min_length=1)
    method: str = Field(min_length=2, max_length=300)
    sourceAssetId: str = Field(min_length=1)
    isModelTarget: bool = False


class SupplementaryMeasurementSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actualParameters: OptimizationParameters
    measurements: list[SupplementaryMeasurementInput] = Field(min_length=1, max_length=1000)
    contaminationObserved: bool = False
    equipmentAbnormalities: list[str] = Field(default_factory=list, max_length=100)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def unique_metric_replicates(self):
        keys = [(item.metricName.casefold().strip(), item.replicate) for item in self.measurements]
        if len(keys) != len(set(keys)):
            raise ValueError("measurement metric and replicate must be unique")
        return self


class SupplementaryMeasurementReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "rejected"]
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class SupplementaryMeasurement(BaseModel):
    measurementId: str
    metricName: str
    value: float
    unit: str
    replicate: int
    measuredAt: str
    method: str
    sourceAssetId: str
    isModelTarget: bool


class SupplementaryMeasurementQualityGate(BaseModel):
    eligible: bool
    checks: dict[str, bool]
    reasons: list[str]
    targetMetric: str
    targetReplicateCount: int = Field(ge=0)
    feedbackDatasetVersion: str | None = None
    checkedAt: str


class SupplementaryMeasurementEvent(BaseModel):
    eventId: str
    eventType: str
    title: str
    detail: str
    operator: str
    createdAt: str


class SupplementaryMeasurementBatch(BaseModel):
    measurementBatchId: str
    experimentId: str
    commandId: str
    requestFingerprint: str
    executionBatchId: str
    planVersion: str
    candidateId: str
    executionBatchCode: str
    parentModelVersion: str
    reportId: str
    targetMetric: str
    status: Literal["draft", "needsReview", "confirmed", "rejected"]
    frozenParameters: OptimizationParameters
    actualParameters: OptimizationParameters | None = None
    allowedSourceAssetIds: list[str]
    sourceAssetNames: dict[str, str]
    measurements: list[SupplementaryMeasurement] = Field(default_factory=list)
    contaminationObserved: bool = False
    equipmentAbnormalities: list[str] = Field(default_factory=list)
    notes: str = ""
    qualityGate: SupplementaryMeasurementQualityGate | None = None
    createdBy: str
    createdAt: str
    submittedAt: str | None = None
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    events: list[SupplementaryMeasurementEvent] = Field(default_factory=list)
    disclaimer: str = "只有真实测量、来源文件、质量门禁和人工复核全部通过后才生成反馈数据资产；不会自动训练或切换模型。"
