from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResultRiskContext(StrictModel):
    riskId: str
    text: str


class ResultInterpretationContext(StrictModel):
    experimentId: str
    taskId: str
    targetField: str
    status: str
    confidenceLevel: str
    metrics: dict[str, float]
    risks: list[ResultRiskContext]
    existingRecommendations: list[str]
    manualReviewItems: list[str]
    generatedAt: str

    def allowed_evidence_refs(self) -> set[str]:
        return {*(f"metric:{key}" for key in self.metrics), *(risk.riskId for risk in self.risks), "result:version", "result:manual-review"}


class MetricInterpretationDraft(StrictModel):
    metricKey: str
    interpretation: str = Field(min_length=2, max_length=500)
    evidenceRefs: list[str] = Field(min_length=1, max_length=5)


class PatternDraft(StrictModel):
    statement: str = Field(min_length=2, max_length=500)
    evidenceRefs: list[str] = Field(min_length=1, max_length=5)


class RiskExplanationDraft(StrictModel):
    riskId: str
    explanation: str = Field(min_length=2, max_length=500)
    evidenceRefs: list[str] = Field(min_length=1, max_length=5)


class NextExperimentDraft(StrictModel):
    title: str = Field(min_length=2, max_length=100)
    purpose: str = Field(min_length=2, max_length=500)
    evidenceRefs: list[str] = Field(min_length=1, max_length=5)
    validationItems: list[str] = Field(min_length=1, max_length=8)


class InterpretationProviderOutput(StrictModel):
    overallSummary: str = Field(min_length=2, max_length=1000)
    metricInterpretations: list[MetricInterpretationDraft] = Field(max_length=10)
    observedPatterns: list[PatternDraft] = Field(max_length=10)
    riskExplanations: list[RiskExplanationDraft] = Field(max_length=10)
    nextExperimentSuggestions: list[NextExperimentDraft] = Field(max_length=8)
    unresolvedQuestions: list[str] = Field(max_length=10)


class ResultInterpretationProviderFailure(RuntimeError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


class ResultInterpretationProvider(Protocol):
    provider: str
    model: str
    def interpret(self, context: ResultInterpretationContext) -> InterpretationProviderOutput: ...
