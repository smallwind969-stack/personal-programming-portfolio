from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.optimization import OptimizationParameters


ValidationScale = Literal["lab", "pilot"]
ValidationBatchStatus = Literal["draft", "needsReview", "confirmed", "rejected"]


class ExperimentalMeasurement(BaseModel):
    measurementId: str
    metricName: str = Field(min_length=1, max_length=120)
    value: float
    unit: str = Field(min_length=1, max_length=40)
    replicate: int = Field(ge=1)
    measuredAt: str
    method: str = Field(min_length=2, max_length=300)
    sourceAssetId: str | None = None
    isModelTarget: bool = False


class ExperimentalMeasurementInput(BaseModel):
    metricName: str = Field(min_length=1, max_length=120)
    value: float
    unit: str = Field(min_length=1, max_length=40)
    replicate: int = Field(ge=1)
    measuredAt: str
    method: str = Field(min_length=2, max_length=300)
    sourceAssetId: str | None = None
    isModelTarget: bool = False


class ExperimentalValidationBatchCreate(BaseModel):
    optimizationRunId: str = Field(min_length=1)
    parameterVersion: str = Field(min_length=1)
    predictedResultVersion: str = Field(min_length=1)
    batchCode: str = Field(min_length=1, max_length=100)
    scale: ValidationScale
    operator: str = Field(min_length=1, max_length=100)
    plannedAt: str


class ExperimentalValidationSubmission(BaseModel):
    actualParameters: OptimizationParameters
    measurements: list[ExperimentalMeasurementInput] = Field(min_length=1)
    contaminationObserved: bool = False
    equipmentAbnormalities: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def unique_measurements(self):
        keys = [(item.metricName, item.replicate) for item in self.measurements]
        if len(keys) != len(set(keys)):
            raise ValueError("measurement metricName and replicate must be unique")
        return self


class ExperimentalFeedbackReview(BaseModel):
    decision: Literal["approved", "rejected"]
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class RetrainingEligibilityGate(BaseModel):
    eligible: bool
    checks: dict[str, bool]
    reasons: list[str]
    targetMetric: str
    targetReplicateCount: int = Field(ge=0)
    feedbackDatasetVersion: str | None = None
    checkedAt: str


class ExperimentalValidationBatch(BaseModel):
    validationBatchId: str
    experimentId: str
    optimizationRunId: str
    parameterVersion: str
    predictedResultVersion: str
    parentModelVersion: str
    parentSimulationRunId: str
    batchCode: str
    scale: ValidationScale
    status: ValidationBatchStatus
    plannedAt: str
    approvedParameters: OptimizationParameters
    actualParameters: OptimizationParameters | None = None
    measurements: list[ExperimentalMeasurement] = Field(default_factory=list)
    contaminationObserved: bool = False
    equipmentAbnormalities: list[str] = Field(default_factory=list)
    notes: str = ""
    qualityGate: RetrainingEligibilityGate | None = None
    createdBy: str
    createdAt: str
    submittedAt: str | None = None
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    disclaimer: str = "真实批次反馈须经数据质量与人工确认；通过闸门只代表允许创建重训练数据资产，不代表模型已自动晋升。"
