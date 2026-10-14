from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from typing import Literal

from app.feature_binding_advisor.contracts import (
    DeviceAdapterPackReference,
    DeviceAdapterPackSelector,
)


ExperimentStageName = Literal["dataAnalysis", "simulation", "optimization"]
ExperimentSourceType = Literal["enterprise", "sample", "blank"]
ExperimentStageStatus = Literal[
    "waiting",
    "running",
    "completed",
    "needsReview",
    "failed",
    "stopped",
]


class ExperimentStageSummary(BaseModel):
    stage: ExperimentStageName
    label: str
    status: ExperimentStageStatus
    canEnter: bool
    canRun: bool = False
    detail: str


class ExperimentArchiveItem(BaseModel):
    experimentId: str
    name: str
    batchCode: str | None
    currentStage: ExperimentStageName
    status: ExperimentStageStatus
    resultSummary: str
    confidenceScore: float | None = Field(default=None, ge=0, le=1)
    updatedAt: str
    industry: str = "未配置"
    processType: str = "未配置"


class ExperimentArchiveResponse(BaseModel):
    totalCount: int
    runningCount: int
    completedCount: int
    averageConfidenceScore: float
    experiments: list[ExperimentArchiveItem]


class ExperimentReliabilityMetric(BaseModel):
    label: str
    value: str
    detail: str


class ProductionContext(BaseModel):
    industry: str = Field(default="未配置", min_length=1, max_length=120)
    processType: str = Field(default="未配置", min_length=1, max_length=120)
    lineName: str | None = Field(default=None, max_length=160)
    materialSystem: str | None = Field(default=None, max_length=200)
    criticalParameters: list[str] = Field(default_factory=list, max_length=30)
    parameterDefinitions: list["ProductionParameterDefinition"] = Field(default_factory=list, max_length=50)


class ProductionParameterDefinition(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    unit: str = Field(default="", max_length=30)
    min: float | None = None
    max: float | None = None
    defaultValue: float | None = None
    source: str = Field(default="实验配置", max_length=80)


class ExperimentWorkspaceOverview(BaseModel):
    experimentId: str
    name: str
    objective: str
    batchCode: str | None
    currentStage: ExperimentStageName
    status: ExperimentStageStatus
    resultSummary: str
    statusLabel: str
    updatedAt: str
    confidenceScore: float | None = Field(default=None, ge=0, le=1)
    modelVersion: str
    resultVersion: str | None = None
    modelType: str
    reliabilityMetrics: list[ExperimentReliabilityMetric]
    stages: list[ExperimentStageSummary] = Field(min_length=3, max_length=3)
    resultMetrics: list[ExperimentReliabilityMetric]
    riskItems: list[str]
    validationItems: list[str]
    targetProduct: str | None = None
    targetMetrics: list[str] = Field(default_factory=list)
    adapterPack: DeviceAdapterPackReference | None = None
    sourceType: ExperimentSourceType = "enterprise"
    sampleTemplateVersion: str | None = None
    productionContext: ProductionContext = Field(default_factory=ProductionContext)


class ExperimentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=2, max_length=2000)
    batchCode: str | None = Field(default=None, max_length=100)
    targetProduct: str = Field(min_length=1, max_length=200)
    targetMetrics: list[str] = Field(min_length=1, max_length=20)
    adapterPack: DeviceAdapterPackSelector | None = None
    sourceType: Literal["enterprise", "blank"] = "blank"
    productionContext: ProductionContext = Field(default_factory=ProductionContext)


class ExperimentRecord(BaseModel):
    experimentId: str
    resultId: str
    sampleCode: str
    testName: str
    metricValue: float
    unit: str
    targetRange: str
    status: str
    riskLevel: str
    conclusion: str
    createdAt: str


class ExperimentTextFileUploadRequest(BaseModel):
    fileName: str
    content: str
    encoding: Literal["utf8", "base64"] = "utf8"
    sourceAssetId: str | None = None
    sourceConversionNote: str | None = Field(default=None, max_length=1000)


class ExperimentBatchFileUploadRequest(BaseModel):
    files: list[ExperimentTextFileUploadRequest] = Field(min_length=1)


class ExperimentFileAsset(BaseModel):
    assetId: str
    experimentId: str
    originalName: str
    detectedFormat: str
    parseStatus: str
    rowCount: int
    columnNames: list[str]
    contentHash: str
    duplicate: bool
    duplicateOfAssetId: str | None = None
    derivedFromAssetId: str | None = None
    sourceConversionNote: str | None = None
    intakeRunId: str | None = None
    adapterApplied: bool = False
    pendingReviewCount: int = 0


class ExperimentBatchFileUploadResponse(BaseModel):
    experimentId: str
    assetCount: int
    assets: list[ExperimentFileAsset]


class DataIntakeFieldTransformation(BaseModel):
    assetId: str
    originalColumn: str
    matched: bool
    standardField: str | None = None
    simulationParameter: str | None = None
    sourceUnit: str | None = None
    targetUnit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    evidence: list[str] = Field(min_length=1)
    requiresHumanReview: bool = True


class DataCollectionLocalizationRun(BaseModel):
    runId: str
    experimentId: str
    assetId: str
    status: Literal["needsReview", "confirmed", "failed"]
    managedWorkspace: bool = False
    adapterPack: DeviceAdapterPackReference | None = None
    transformationCount: int
    matchedCount: int
    pendingReviewCount: int
    transformations: list[DataIntakeFieldTransformation]
    createdAt: str


class CleaningAlignmentConfig(BaseModel):
    missingValuePolicy: Literal["keep_null"] = "keep_null"
    invalidNumericPolicy: Literal["keep_null"] = "keep_null"
    naiveTimestampTimezone: Literal["UTC"] = "UTC"
    numericPrecision: int = Field(default=8, ge=2, le=15)


class CleaningAlignmentQuality(BaseModel):
    missingValueCount: int = 0
    invalidNumericCount: int = 0
    invalidTimestampCount: int = 0
    duplicateTimestampCount: int = 0
    unmappedColumnCount: int = 0


class CleaningFieldConversionEvidence(BaseModel):
    assetId: str
    originalColumn: str
    standardField: str
    sourceUnit: str | None = None
    targetUnit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    formula: str
    sampleBefore: str | None = None
    sampleAfter: str | float | None = None


class FeatureEngineeringConfig(BaseModel):
    targetField: str = Field(min_length=1)
    sourceFields: list[str] = Field(min_length=1)
    includeRaw: bool = True
    lagSteps: list[int] = Field(default_factory=lambda: [1])
    rollingWindows: list[int] = Field(default_factory=lambda: [3])
    includeDiff: bool = True

    @model_validator(mode="after")
    def validate_windows_and_fields(self) -> "FeatureEngineeringConfig":
        if len(self.sourceFields) != len(set(self.sourceFields)):
            raise ValueError("source fields must be unique")
        if self.targetField in self.sourceFields:
            raise ValueError("target field cannot also be a source feature")
        if any(step <= 0 for step in self.lagSteps):
            raise ValueError("lag steps must use history only and be positive")
        if any(window < 2 for window in self.rollingWindows):
            raise ValueError("rolling windows must contain at least two historical observations")
        if len(self.lagSteps) != len(set(self.lagSteps)):
            raise ValueError("lag steps must be unique")
        if len(self.rollingWindows) != len(set(self.rollingWindows)):
            raise ValueError("rolling windows must be unique")
        return self


class EngineeredFeatureDefinition(BaseModel):
    name: str
    kind: Literal["raw", "lag", "diff", "rolling_mean", "rolling_std"]
    sourceField: str
    formula: str
    lag: int | None = None
    window: int | None = None
    validCount: int
    missingRate: float


class FeatureLeakageIssue(BaseModel):
    code: str
    severity: Literal["warning", "blocking"]
    featureName: str | None = None
    message: str


class FeatureEngineeringRun(BaseModel):
    featureSetId: str
    experimentId: str
    runVersion: int
    status: Literal["needsReview", "confirmed", "superseded"]
    config: FeatureEngineeringConfig
    snapshotId: str
    snapshotContentHash: str
    cleaningRunId: str
    cleaningOutputHash: str
    inputFingerprint: str
    outputHash: str
    targetField: str
    candidateFeatureNames: list[str]
    selectedFeatureNames: list[str] = Field(default_factory=list)
    definitions: list[EngineeredFeatureDefinition]
    featureRows: list[dict[str, str | float | None]]
    rowCount: int
    usableRowCount: int
    leakageIssues: list[FeatureLeakageIssue] = Field(default_factory=list)
    confirmedBy: str | None = None
    confirmationReason: str | None = None
    confirmedAt: str | None = None
    createdAt: str


class FeatureEngineeringConfirmRequest(BaseModel):
    operator: str = Field(min_length=1)
    reason: str = Field(min_length=2)
    selectedFeatureNames: list[str] = Field(min_length=1)


class CleaningAlignmentRun(BaseModel):
    runId: str
    experimentId: str
    runVersion: int = Field(ge=1)
    status: Literal["completed", "needsReview", "confirmed", "failed"]
    config: CleaningAlignmentConfig
    inputFingerprint: str
    outputHash: str
    assetCount: int
    mappingCount: int
    alignedRowCount: int
    alignedRows: list[dict[str, str | float | None]]
    conversionEvidence: list[CleaningFieldConversionEvidence]
    quality: CleaningAlignmentQuality
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    createdAt: str


class CleaningAlignmentReviewRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class ExperimentFileAuditEvent(BaseModel):
    auditId: str
    experimentId: str
    action: str
    stage: str
    stageLabel: str
    fileNames: list[str]
    assetIds: list[str]
    contentHashes: list[str]
    duplicates: list[bool]
    createdAt: str
    operator: str | None = None
    reason: str | None = None


class ExperimentFileDeleteRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class ExperimentFileDeleteResult(BaseModel):
    assetId: str
    experimentId: str
    status: Literal["deleted"]
    retainedContentHash: str
    auditId: str


class ExperimentAssetIntegrityResult(BaseModel):
    assetId: str
    experimentId: str
    contentHash: str
    verified: bool
    storageScheme: Literal["content-addressed-sha256"]


class ExperimentFileAuditTimeline(BaseModel):
    experimentId: str
    eventCount: int
    events: list[ExperimentFileAuditEvent]


class ExperimentFileAuditStageSummary(BaseModel):
    stage: str
    stageLabel: str
    eventCount: int
    assetCount: int


class ExperimentFileAuditSummary(BaseModel):
    experimentId: str
    eventCount: int
    assetCount: int
    stageSummary: list[ExperimentFileAuditStageSummary]
    lastEvent: ExperimentFileAuditEvent | None


class ExperimentFieldMappingSuggestion(BaseModel):
    originalColumn: str
    standardField: str | None
    displayName: str
    unit: str | None = None
    confidenceScore: float
    requiresHumanConfirmation: bool
    reason: str


class ExperimentAssetFieldMappingSuggestions(BaseModel):
    assetId: str
    originalName: str
    suggestions: list[ExperimentFieldMappingSuggestion]


class ExperimentFieldMappingSuggestionResponse(BaseModel):
    experimentId: str
    assetCount: int
    assets: list[ExperimentAssetFieldMappingSuggestions]


class SchemaRecognitionCandidate(BaseModel):
    assetId: str
    originalColumn: str
    standardField: str
    dataType: Literal["number", "string", "datetime", "boolean"]
    sourceUnit: str | None = None
    targetUnit: str | None = None
    isTimeField: bool
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)
    requiresHumanReview: bool
    reviewReasons: list[str]
    source: Literal["llm", "rule", "merged"]


class SchemaRecognitionRun(BaseModel):
    runId: str
    experimentId: str
    commandId: str
    status: Literal["completed", "failed"]
    mode: Literal["llm_assisted", "rule_fallback", "rule_only"]
    provider: str
    model: str
    fallbackReason: str | None = None
    candidateCount: int
    reviewCount: int
    conflictCount: int
    rejectedCount: int
    candidates: list[SchemaRecognitionCandidate]
    createdAt: str


class SchemaRecognitionRunCreateRequest(BaseModel):
    commandId: str = Field(min_length=1, max_length=128)


class ExperimentConfirmedFieldMapping(BaseModel):
    assetId: str
    originalColumn: str
    standardField: str
    displayName: str
    unit: str | None = None
    confirmedBy: str
    confirmed: bool = True


class ExperimentConfirmFieldMappingsRequest(BaseModel):
    mappings: list[ExperimentConfirmedFieldMapping] = Field(min_length=1)


class ExperimentConfirmedFieldMappingSet(BaseModel):
    experimentId: str
    mappingCount: int
    mappings: list[ExperimentConfirmedFieldMapping]


class ExperimentFieldDictionaryEntry(BaseModel):
    sourceColumn: str
    standardField: str
    displayName: str
    unit: str | None = None
    createdBy: str


class ExperimentFieldDictionaryUpsertRequest(BaseModel):
    entries: list[ExperimentFieldDictionaryEntry] = Field(min_length=1)


class ExperimentFieldDictionary(BaseModel):
    experimentId: str
    entryCount: int
    entries: list[ExperimentFieldDictionaryEntry]


class ExperimentCleaningQualitySummary(BaseModel):
    missingValueCount: int
    invalidNumericCount: int
    unmappedColumnCount: int


class ExperimentAssetCleaningPreview(BaseModel):
    assetId: str
    originalName: str
    rowCount: int
    cleanedRows: list[dict[str, str | float | None]]
    quality: ExperimentCleaningQualitySummary
    cleaningLogs: list[str]


class ExperimentCleaningPreviewResponse(BaseModel):
    experimentId: str
    assetCount: int
    assets: list[ExperimentAssetCleaningPreview]


class ExperimentAlignmentAssetSummary(BaseModel):
    assetId: str
    originalName: str
    timestampCount: int
    fields: list[str]


class ExperimentAlignmentPreviewResponse(BaseModel):
    experimentId: str
    assetCount: int
    timestampCount: int
    missingCellCount: int
    assetSummaries: list[ExperimentAlignmentAssetSummary]
    alignedRows: list[dict[str, str | float | None]]
    alignmentLogs: list[str]


class ExperimentFeatureSummary(BaseModel):
    field: str
    count: int
    min: float
    max: float
    mean: float
    first: float
    last: float
    delta: float
    windowMean: float


class ExperimentFeatureAnomalyHint(BaseModel):
    field: str
    timestamp: str
    value: float
    reason: str


class ExperimentFeaturePreviewResponse(BaseModel):
    experimentId: str
    rowCount: int
    featureCount: int
    features: list[ExperimentFeatureSummary]
    anomalyHints: list[ExperimentFeatureAnomalyHint]


class ExperimentDatasetSnapshot(BaseModel):
    snapshotId: str
    experimentId: str
    assetCount: int
    evidenceAssetCount: int = 0
    analysisAssetIds: list[str] = Field(default_factory=list)
    sourceEvidenceAssetIds: list[str] = Field(default_factory=list)
    mappingCount: int
    alignedRowCount: int
    featureCount: int
    anomalyCount: int
    contentHash: str
    cleaningRunId: str | None = None
    cleaningOutputHash: str | None = None
    alignedRows: list[dict[str, str | float | None]] = Field(default_factory=list)
    status: str
    createdAt: str


class ExperimentModelingPlanPreview(BaseModel):
    experimentId: str
    snapshotId: str
    targetField: str
    candidateFeatures: list[str]
    recommendedModelType: str
    trainSplitRatio: float
    validationSplitRatio: float
    evaluationMetrics: list[str]
    riskHints: list[str]
    status: str


class ExperimentTrainingAgentStage(BaseModel):
    agentName: str
    stageLabel: str
    status: str
    detail: str


class ExperimentTrainingTaskPreview(BaseModel):
    taskId: str
    experimentId: str
    snapshotId: str
    planTargetField: str
    recommendedModelType: str
    evaluationMetrics: list[str]
    status: str
    createdAt: str
    updatedAt: str
    agentStages: list[ExperimentTrainingAgentStage]


class ExperimentTrainingResultMetrics(BaseModel):
    mae: float
    rmse: float
    r2: float


class ExperimentTrainingResultSummary(BaseModel):
    experimentId: str
    taskId: str
    targetField: str
    status: str
    confidenceLevel: str
    metrics: ExperimentTrainingResultMetrics
    riskNotes: list[str]
    recommendations: list[str]
    manualReviewItems: list[str]
    generatedAt: str


class ResultMetricInterpretation(BaseModel):
    metricKey: Literal["mae", "rmse", "r2"]
    value: float
    interpretation: str
    evidenceRefs: list[str]


class ResultObservedPattern(BaseModel):
    statement: str
    evidenceRefs: list[str]


class ResultRiskExplanation(BaseModel):
    riskId: str
    originalRisk: str
    explanation: str
    evidenceRefs: list[str]


class ResultNextExperimentSuggestion(BaseModel):
    title: str
    purpose: str
    evidenceRefs: list[str]
    validationItems: list[str]
    requiresHumanReview: bool = True


class ResultInterpretationRun(BaseModel):
    runId: str
    experimentId: str
    commandId: str
    status: Literal["completed", "failed"]
    mode: Literal["llm_assisted", "rule_fallback"]
    provider: str
    model: str
    sourceTaskId: str
    sourceGeneratedAt: str
    authoritativeMetrics: ExperimentTrainingResultMetrics
    confidenceLevel: str
    overallSummary: str
    metricInterpretations: list[ResultMetricInterpretation]
    observedPatterns: list[ResultObservedPattern]
    riskExplanations: list[ResultRiskExplanation]
    nextExperimentSuggestions: list[ResultNextExperimentSuggestion]
    unresolvedQuestions: list[str]
    fallbackReason: str | None = None
    rejectedCount: int = 0
    createdAt: str


class ResultInterpretationRunCreateRequest(BaseModel):
    commandId: str = Field(min_length=1, max_length=128)


class ExperimentResearchBriefSummary(BaseModel):
    experimentId: str
    taskId: str
    title: str
    objective: str
    dataSummary: str
    modelSummary: str
    riskSummary: str
    nextActions: list[str]
    manualConfirmationItems: list[str]
    status: str
    generatedAt: str


class ExperimentSimulationRange(BaseModel):
    min: float
    max: float
    unit: str


class ExperimentSimulationCandidatePlan(BaseModel):
    planName: str
    temperatureC: float
    ph: float
    durationHours: float
    reason: str


class ExperimentSimulationInputSummary(BaseModel):
    experimentId: str
    targetField: str
    objective: str
    recommendedRanges: dict[str, ExperimentSimulationRange]
    candidatePlans: list[ExperimentSimulationCandidatePlan]
    manualConfirmationItems: list[str]
    status: str
    generatedAt: str


AgentRunStatus = Literal["waiting", "running", "interrupted", "completed", "needsReview", "failed", "stopped"]


class AgentRunNode(BaseModel):
    nodeId: str
    agentKey: str
    agentName: str
    stageLabel: str
    status: AgentRunStatus
    progressPercent: int = Field(ge=0, le=100)
    inputSummary: list[str]
    methodSummary: list[str]
    metricSummary: list[str]
    outputSummary: list[str]
    startedAt: str | None = None
    completedAt: str | None = None


class AgentRunEvent(BaseModel):
    eventId: str
    eventType: str
    nodeId: str | None = None
    title: str
    detail: str
    createdAt: str


class AgentGuidancePreviewRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=1000)


class AgentGuidanceApplyRequest(BaseModel):
    guidanceId: str
    confirmed: bool


class AgentRunRestartRequest(BaseModel):
    guidanceId: str | None = None


class AgentRunAdvanceRequest(BaseModel):
    expectedRevision: int = Field(ge=1)
    commandId: str = Field(min_length=3, max_length=100)


class HumanReviewDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=2, max_length=1000)
    operator: str = Field(min_length=1, max_length=100)
    impactScope: list[str] = Field(min_length=1)


class AgentGuidancePreview(BaseModel):
    guidanceId: str
    experimentId: str
    runId: str
    prompt: str
    intentSummary: str
    affectedNodes: list[str]
    planChanges: list[str]
    comparisonImpact: str
    safeCheckpoint: str
    requiresRestart: bool
    status: Literal["preview", "scheduled", "applied", "rejected"]


class HumanDecision(BaseModel):
    decisionId: str
    decision: Literal["approved", "rejected"]
    reason: str
    operator: str
    impactScope: list[str]
    createdAt: str


class ExperimentAgentRun(BaseModel):
    runId: str
    runtimeBackend: str = "deterministic"
    runtimeRunId: str
    runtimeRevision: int = Field(ge=1)
    parentRunId: str | None = None
    experimentId: str
    version: int = Field(ge=1)
    status: AgentRunStatus
    currentNodeId: str | None
    progressPercent: int = Field(ge=0, le=100)
    nodes: list[AgentRunNode] = Field(min_length=7, max_length=7)
    events: list[AgentRunEvent]
    pendingGuidance: AgentGuidancePreview | None = None
    appliedGuidance: list[AgentGuidancePreview] = Field(default_factory=list)
    humanDecisions: list[HumanDecision] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
    disclaimer: str
