from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high"]
ConfidenceLevel = Literal["low", "medium", "high"]
Priority = Literal["required", "recommended", "optional"]
RecommendationType = Literal["rd_experiment_suggestion"]


class ProductProperty(BaseModel):
    propertyId: str
    propertyName: str
    propertyValue: str
    unit: str | None = None
    description: str | None = None


class RiskItem(BaseModel):
    riskId: str
    riskName: str
    riskLevel: RiskLevel
    description: str
    mitigationSuggestion: str


class ValidationMetric(BaseModel):
    metricId: str
    metricName: str
    methodSuggestion: str
    expectedRange: str | None = None
    priority: Priority


class PredictionResult(BaseModel):
    predictionId: str
    targetName: str
    predictedValue: str
    unit: str | None = None
    confidenceScore: float = Field(ge=0, le=1)
    explanation: str
