from pydantic import BaseModel, Field


class NumericRange(BaseModel):
    min: float
    max: float
    unit: str


class ProductionLineProfile(BaseModel):
    lineId: str
    lineName: str
    equipmentType: str
    workingVolume: str
    temperatureRange: NumericRange
    phRange: NumericRange
    agitationRange: NumericRange
    anaerobicCapability: str
    aerationCapability: str
    sensors: list[str]
    downstreamCapabilities: list[str]
    feasibilityScore: int
    dataCompleteness: str
    limitations: list[str]


class ProcessTaskRequest(BaseModel):
    targetProductName: str
    targetProductForm: str
    akkProductType: str
    applicationDirection: str
    targetContent: str = "每批次有效成分 18-24 g"
    activityTarget: str = "不低于 82%"
    stabilityTarget: str = "常温 90 天指标衰减不超过 15%"
    costLimit: str = "培养与后处理成本不高于 620 元/批"
    optimizationStrategy: str
    allowCoCulture: bool = False
    targetScale: str
    constraints: list[str] = Field(default_factory=list)
    productionLineId: str
    currentTemperature: float | None = None
    currentPh: float | None = None
    currentAgitationRpm: float | None = None
    currentVolumeL: float | None = None
    sensorCapability: str | None = None
    downstreamCapability: str | None = None


class ScoreBreakdown(BaseModel):
    overallScore: int
    yieldScore: int
    activityScore: int
    stabilityScore: int
    costScore: int
    riskScore: int
    feasibilityScore: int
    confidenceScore: int


class RecommendedParameters(BaseModel):
    temperature: NumericRange
    ph: NumericRange
    cultureTimeHours: NumericRange
    agitationRpm: NumericRange
    aerationMode: str
    inoculationRatio: str
    coCultureRatio: str | None = None


class CandidatePlan(BaseModel):
    planId: str
    planType: str
    displayName: str
    summary: str
    recommendedParameters: RecommendedParameters
    scoreBreakdown: ScoreBreakdown
    riskItems: list[str]
    validationMetrics: list[str]
    explanation: list[str]


class SurfacePoint(BaseModel):
    temperature: float
    ph: float
    score: int
    riskLevel: str


class ResponseSurface(BaseModel):
    xAxisLabel: str
    yAxisLabel: str
    zAxisLabel: str
    points: list[SurfacePoint]


class RecommendationReport(BaseModel):
    title: str
    parameterWindows: list[str]
    predictedOutcomes: list[str]
    riskControls: list[str]
    validationPlan: list[str]
    nextStepSuggestion: str


class GeneratedProcessTask(BaseModel):
    taskId: str
    targetSummary: str
    selectedLine: ProductionLineProfile
    candidatePlans: list[CandidatePlan]
    surface: ResponseSurface
    report: RecommendationReport
    disclaimer: str


class ExperimentFeedbackRequest(BaseModel):
    taskId: str
    actualYield: str
    actualActivity: str
    contaminationObserved: bool
    equipmentAbnormalities: list[str] = Field(default_factory=list)
    conclusion: str
    notes: str = ""


class ExperimentFeedback(ExperimentFeedbackRequest):
    feedbackId: str
