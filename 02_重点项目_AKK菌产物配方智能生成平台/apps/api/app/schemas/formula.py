from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import (
    ConfidenceLevel,
    PredictionResult,
    RecommendationType,
    RiskItem,
    ValidationMetric,
)


class FormulaGenerationRequest(BaseModel):
    applicationTargetId: str
    targetProperties: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    preferredProductIds: list[str] = Field(default_factory=list)
    excludedProductIds: list[str] = Field(default_factory=list)
    maxIngredientCount: int = Field(default=3, ge=1, le=5)
    notes: str | None = None


class FormulaIngredient(BaseModel):
    productId: str
    productName: str
    ratioPercent: float
    role: str


class CompanionIngredient(BaseModel):
    ingredientId: str
    ingredientName: str
    category: str
    suggestedUsage: str
    purpose: str
    riskNote: str


class KnowledgeReference(BaseModel):
    knowledgeId: str
    title: str
    evidenceLevel: str
    sourceUrl: str
    relevanceReason: str
    retrievalScore: float | None = None
    keyPassages: list[str] = Field(default_factory=list)


class AgentTraceItem(BaseModel):
    agentName: str
    status: str
    outputSummary: str


class FormulaCandidate(BaseModel):
    candidateId: str
    candidateName: str
    composition: list[FormulaIngredient]
    companionIngredients: list[CompanionIngredient] = Field(default_factory=list)
    predictions: list[PredictionResult]
    confidenceScore: float = Field(ge=0, le=1)
    confidenceLevel: ConfidenceLevel
    riskItems: list[RiskItem]
    validationMetrics: list[ValidationMetric]
    experimentSuggestions: list[str]
    productAdvantages: list[str] = Field(default_factory=list)
    upgradeSuggestions: list[str] = Field(default_factory=list)
    knowledgeReferences: list[KnowledgeReference] = Field(default_factory=list)
    agentTrace: list[AgentTraceItem] = Field(default_factory=list)
    approvalStatus: str = "pending_research_review"


class FormulaResult(BaseModel):
    resultId: str
    recommendationType: RecommendationType
    researchUseOnly: bool
    research_use_only: bool
    disclaimer: str
    applicationName: str
    createdAt: datetime
    sourceType: Literal["mock"]
    candidates: list[FormulaCandidate]
