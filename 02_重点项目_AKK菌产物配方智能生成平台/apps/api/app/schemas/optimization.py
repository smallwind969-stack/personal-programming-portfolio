from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


OptimizationStatus = Literal["waiting", "draft", "running", "needsReview", "completed", "failed", "stopped"]


class OptimizationParameters(BaseModel):
    temperatureC: float = Field(ge=20, le=55, multiple_of=0.1)
    ph: float = Field(ge=4.5, le=8.5, multiple_of=0.01)
    cultureHours: float = Field(ge=1, le=168, multiple_of=1)
    stirringRpm: float = Field(ge=0, le=600, multiple_of=1)


class OptimizationResponsePoint(BaseModel):
    temperatureC: float
    ph: float
    predictedScore: float = Field(ge=0, le=100)
    predictedValue: float | None = None


class OptimizationModelEvidence(BaseModel):
    targetField: str
    prediction: float
    intervalLower: float
    intervalUpper: float
    intervalMethod: str
    modelVersion: str
    bindingVersion: str
    artifactFingerprint: str
    extrapolated: bool = False
    outOfRangeFeatures: list[str] = Field(default_factory=list)


class OptimizationCandidatePlan(BaseModel):
    planId: str
    strategyKey: Literal["balanced", "yieldPriority", "energySaving"]
    displayName: str
    summary: str
    parameters: OptimizationParameters
    scoreBreakdown: dict[str, float]
    confidenceScore: float = Field(ge=0, le=1)
    predictionIntervals: list[str]
    riskItems: list[str]
    validationItems: list[str]
    explanation: list[str]
    responseSurface: list[OptimizationResponsePoint] = Field(min_length=5)
    baselineImprovements: dict[str, float]
    modelEvidence: list[OptimizationModelEvidence] = Field(default_factory=list)
    objectiveScore: float | None = None
    costIndex: float | None = None
    searchRank: int | None = None


class OptimizationSelectionRequest(BaseModel):
    planId: str
    parameters: OptimizationParameters


class OptimizationStage(BaseModel):
    stageId: str
    stageKey: str
    stageName: str
    status: OptimizationStatus
    progressPercent: int = Field(ge=0, le=100)
    detail: str
    outputSummary: list[str]
    startedAt: str | None = None
    completedAt: str | None = None


class OptimizationTrainingMetric(BaseModel):
    round: int = Field(ge=1)
    trainingLoss: float = Field(ge=0)
    validationScore: float = Field(ge=0, le=1)
    retained: bool


class OptimizationSearchMetric(BaseModel):
    strategyKey: str
    evaluatedCount: int = Field(ge=1)
    feasibleCount: int = Field(ge=1)
    bestObjective: float
    bestPrediction: float


class OptimizationEvent(BaseModel):
    eventId: str
    eventType: str
    stageId: str | None = None
    title: str
    detail: str
    createdAt: str


class OptimizationReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=2, max_length=1000)
    operator: str = Field(min_length=1, max_length=100)
    impactScope: list[str] = Field(min_length=1)


class OptimizationHumanDecision(BaseModel):
    decisionId: str
    decision: Literal["approved", "rejected"]
    reason: str
    operator: str
    impactScope: list[str]
    createdAt: str


class OptimizationResultSummary(BaseModel):
    confidenceScore: float = Field(ge=0, le=1)
    predictedOutcomes: list[str]
    riskItems: list[str]
    validationItems: list[str]
    disclaimer: str


class ExperimentOptimizationRun(BaseModel):
    runId: str
    experimentId: str
    version: int = Field(ge=0)
    status: OptimizationStatus
    admissionAllowed: bool
    admissionReasons: list[str]
    baseModelVersion: str
    baseResultVersion: str
    baseSimulationRunId: str | None = None
    baseBindingVersions: list[str] = Field(default_factory=list)
    searchMode: Literal["rule_demo", "promoted_model_constrained"] = "rule_demo"
    searchEvaluations: int = 0
    requirementDriven: bool = False
    productRequirementVersionId: str | None = None
    productRequirementVersion: int | None = None
    productRequirementWorkingName: str | None = None
    productRequirementSourceRunId: str | None = None
    productRequirementContentHash: str | None = None
    candidatePlans: list[OptimizationCandidatePlan] = Field(default_factory=list, max_length=3)
    selectedPlanId: str | None = None
    editedParameters: OptimizationParameters | None = None
    submittedParameters: OptimizationParameters | None = None
    trainingDataVersion: str | None = None
    retrainingStages: list[OptimizationStage] = Field(min_length=4, max_length=4)
    currentStageId: str | None = None
    progressPercent: int = Field(ge=0, le=100)
    trainingMetrics: list[OptimizationTrainingMetric]
    searchMetrics: list[OptimizationSearchMetric] = Field(default_factory=list)
    submittedModelEvidence: list[OptimizationModelEvidence] = Field(default_factory=list)
    modelRetrained: bool = False
    officialParameterVersion: str | None = None
    newModelVersion: str | None = None
    newResultVersion: str | None = None
    resultSummary: OptimizationResultSummary | None = None
    humanDecisions: list[OptimizationHumanDecision]
    events: list[OptimizationEvent]
    createdAt: str
    updatedAt: str
    disclaimer: str
