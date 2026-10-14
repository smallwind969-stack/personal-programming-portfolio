from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductInnovationInput(StrictModel):
    brief: str = Field(min_length=5, max_length=5000)
    industry: str | None = Field(default=None, max_length=100)
    targetMarket: str | None = Field(default=None, max_length=100)
    targetUsers: list[str] = Field(default_factory=list, max_length=20)
    locale: str = Field(default="zh-CN", max_length=20)
    constraints: list[str] = Field(default_factory=list, max_length=30)


class InnovationEvidence(StrictModel):
    evidenceId: str
    title: str
    evidenceLevel: str


class ProductInnovationContext(StrictModel):
    experimentId: str
    request: ProductInnovationInput
    evidence: list[InnovationEvidence] = Field(max_length=8)
    fixedBoundaries: list[str]

    def allowed_evidence_refs(self) -> set[str]:
        return {"input:brief", "boundary:research-only", *(item.evidenceId for item in self.evidence)}


class InnovationMetricDraft(StrictModel):
    metricName: str = Field(min_length=1, max_length=100)
    direction: Literal["increase", "decrease", "target", "monitor"]
    unit: str | None = Field(default=None, max_length=30)
    targetDescription: str = Field(min_length=2, max_length=300)
    evidenceRefs: list[str] = Field(min_length=1, max_length=5)


class InnovationMaterialRoleDraft(StrictModel):
    role: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=2, max_length=300)
    constraints: list[str] = Field(max_length=10)
    evidenceRefs: list[str] = Field(min_length=1, max_length=5)


class InnovationSuggestionDraft(StrictModel):
    title: str = Field(min_length=2, max_length=100)
    purpose: str = Field(min_length=2, max_length=300)
    evidenceRefs: list[str] = Field(min_length=1, max_length=5)
    validationItems: list[str] = Field(min_length=1, max_length=10)


class InnovationProviderOutput(StrictModel):
    workingName: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=1, max_length=100)
    problemStatement: str = Field(min_length=2, max_length=600)
    targetUserTags: list[str] = Field(max_length=20)
    usageScenarios: list[str] = Field(max_length=20)
    valuePropositions: list[str] = Field(max_length=20)
    targetMetrics: list[InnovationMetricDraft] = Field(max_length=20)
    materialRoles: list[InnovationMaterialRoleDraft] = Field(max_length=20)
    costAssumptions: list[str] = Field(max_length=20)
    processConstraints: list[str] = Field(max_length=20)
    regulatoryConstraints: list[str] = Field(max_length=20)
    risks: list[str] = Field(max_length=20)
    unresolvedQuestions: list[str] = Field(max_length=20)
    validationPlan: list[InnovationSuggestionDraft] = Field(max_length=12)
    evidenceRefs: list[str] = Field(min_length=1, max_length=8)


class ProductInnovationRun(InnovationProviderOutput):
    runId: str
    experimentId: str
    commandId: str
    status: Literal["completed", "failed"]
    mode: Literal["llm_assisted", "rule_fallback"]
    provider: str
    model: str
    fallbackReason: str | None = None
    requiresHumanReview: bool = True
    createdAt: str


class ProductInnovationRunCreateRequest(StrictModel):
    commandId: str = Field(min_length=1, max_length=128)
    input: ProductInnovationInput


class ProductRequirementConfirmRequest(StrictModel):
    commandId: str = Field(min_length=1, max_length=128)
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class ProductRequirementSnapshot(InnovationProviderOutput):
    fixedBoundaries: list[str] = Field(max_length=20)


class ProductRequirementVersion(StrictModel):
    requirementVersionId: str
    experimentId: str
    version: int = Field(ge=1)
    parentVersionId: str | None = None
    sourceRunId: str
    sourceCommandId: str
    confirmationCommandId: str
    status: Literal["confirmed"] = "confirmed"
    snapshot: ProductRequirementSnapshot
    contentHash: str
    operator: str
    reason: str
    confirmedAt: str
    disclaimer: Literal["研发实验建议"] = "研发实验建议"


class InnovationProviderFailure(RuntimeError):
    def __init__(self, category: str) -> None:
        super().__init__(category); self.category = category


class ProductInnovationProvider(Protocol):
    provider: str
    model: str
    def innovate(self, context: ProductInnovationContext) -> InnovationProviderOutput: ...
