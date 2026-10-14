from __future__ import annotations

from typing import Literal
import math
import re

from pydantic import BaseModel, Field, model_validator
from app.model_registry.composite import CompositeTargetPrediction


CarbonSource = Literal[
    "BFP",
    "UBFP",
    "lambdaCarrageenan",
    "iotaCarrageenan",
    "fucoidan",
    "porphyraGlycoprotein",
    "PHP",
    "agar",
]
ProductFormat = Literal["culture-medium", "postbiotic-powder", "fish-ball", "encapsulated-bead"]


class SimulationRange(BaseModel):
    min: float
    max: float
    unit: str


class SimulationPredictRequest(BaseModel):
    targetProduct: str = Field(min_length=1, max_length=80)
    productFormat: ProductFormat
    carbonSource: CarbonSource
    carbonConcentration: float = Field(ge=0, le=4, multiple_of=0.05)
    cultureHours: float = Field(ge=12, le=96, multiple_of=1)
    temperatureC: float = Field(ge=20, le=55, multiple_of=0.1)
    ph: float = Field(ge=4.5, le=8.5, multiple_of=0.01)
    anaerobicScore: float = Field(ge=0, le=1, multiple_of=0.01)
    pressureMpa: float = Field(ge=0, le=450, multiple_of=1)
    stirringRpm: float = Field(ge=0, le=400, multiple_of=1)
    pretreated: bool
    useLlmAdvisor: bool = False
    customParameters: dict[str, float] = Field(default_factory=dict, max_length=50)

    @classmethod
    def validate_custom_parameters(cls, values: dict[str, float]) -> dict[str, float]:
        for key, value in values.items():
            if not re.fullmatch(r"custom_[1-9][0-9]*", key):
                raise ValueError(f"invalid custom parameter key: {key}")
            if not math.isfinite(float(value)):
                raise ValueError(f"custom parameter {key} must be finite")
        return values

    @model_validator(mode="after")
    def check_custom_parameters(self):
        self.validate_custom_parameters(self.customParameters)
        return self


class SimulationPredictions(BaseModel):
    molecularWeightKda: float
    akkGrowthScore: float
    scfaScore: float
    barrierScore: float
    overallScore: float
    confidence: str = "medium"


class SimulationRecommendedSettings(BaseModel):
    carbonSource: CarbonSource
    carbonConcentration: SimulationRange
    temperatureC: SimulationRange
    ph: SimulationRange
    anaerobicScoreMinimum: float
    cultureHours: SimulationRange
    stirringRpm: SimulationRange
    pressureMpa: SimulationRange


class SimulationLlmAdvisor(BaseModel):
    enabled: bool
    provider: str
    model: str
    apiKeyConfigured: bool
    advice: str | None = None
    mode: str


class SimulationPredictResponse(BaseModel):
    label: Literal["研发实验建议"]
    researchUseOnly: bool
    disclaimer: str
    targetProduct: str
    customParameters: dict[str, float] = Field(default_factory=dict)
    confidence: Literal["low", "medium", "high"]
    predictions: SimulationPredictions
    recommendedSettings: SimulationRecommendedSettings
    risks: list[str]
    validationIndicators: list[str]
    curve: list[dict[str, float]]
    llmAdvisor: SimulationLlmAdvisor
    predictionSource: Literal["rule_model", "promoted_model"] = "rule_model"
    modelVersion: str | None = None
    artifactFingerprint: str | None = None
    datasetFingerprint: str | None = None
    extrapolated: bool = False
    fallbackReason: str | None = None


class SimulationScenario(BaseModel):
    scenarioId: str
    name: str
    targetProduct: str
    productFormat: ProductFormat
    carbonSource: CarbonSource
    carbonConcentration: float
    cultureHours: float
    temperatureC: float
    ph: float
    anaerobicScore: float
    pressureMpa: float
    stirringRpm: float
    pretreated: bool


class SimulationLlmStatus(BaseModel):
    enabled: bool
    provider: str
    model: str
    baseUrl: str
    apiKeyConfigured: bool
    envKeys: list[str]
    mode: str


SimulationRunStatus = Literal["waiting", "running", "completed", "failed", "stopped"]


class SimulationRunStage(BaseModel):
    stageId: str
    stageKey: str
    stageName: str
    equipmentName: str
    status: SimulationRunStatus
    progressPercent: int = Field(ge=0, le=100)
    waitingReason: str | None = None
    inputSummary: list[str]
    modelBasis: list[str]
    outputSummary: list[str]
    startedAt: str | None = None
    completedAt: str | None = None


class SimulationRunEvent(BaseModel):
    eventId: str
    eventType: str
    stageId: str | None = None
    title: str
    detail: str
    createdAt: str


class SimulationTrialSnapshot(BaseModel):
    snapshotId: str
    runId: str
    createdAt: str
    parameters: SimulationPredictRequest
    predictions: SimulationPredictions
    confidence: Literal["low", "medium", "high"]
    risks: list[str]
    validationIndicators: list[str]
    baselineDifferences: list[str]
    researchUseOnly: bool = True
    disclaimer: str
    predictionSource: Literal["rule_model", "promoted_model_composite"] = "rule_model"
    modelTargets: list[CompositeTargetPrediction] = Field(default_factory=list)
    bindingVersions: list[str] = Field(default_factory=list)
    unavailableTargets: list[str] = Field(default_factory=list)
    extrapolated: bool = False


class SimulationFailureRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=500)
    affectedVersions: list[str] = Field(min_length=1)


class ExperimentSimulationRun(BaseModel):
    runId: str
    parentRunId: str | None = None
    experimentId: str
    version: int = Field(ge=0)
    status: SimulationRunStatus
    admissionAllowed: bool
    admissionReasons: list[str]
    reliabilityScore: float | None = Field(default=None, ge=0, le=1)
    modelVersion: str
    bindingVersions: list[str] = Field(default_factory=list)
    modelType: str
    lineTemplateId: str
    modelMetrics: dict[str, str]
    progressPercent: int = Field(ge=0, le=100)
    simulatedMinutes: int = Field(ge=0)
    estimatedRemainingMinutes: int = Field(ge=0)
    currentStageId: str | None
    stages: list[SimulationRunStage] = Field(min_length=7, max_length=7)
    events: list[SimulationRunEvent]
    officialParameters: SimulationPredictRequest
    trialSnapshots: list[SimulationTrialSnapshot]
    officialResult: SimulationTrialSnapshot | None = None
    failureReason: str | None = None
    lastSuccessfulStageId: str | None = None
    affectedVersions: list[str] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
    disclaimer: str
