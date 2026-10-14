import { z } from "zod";

export const riskLevelSchema = z.enum(["low", "medium", "high"]);
export const confidenceLevelSchema = z.enum(["low", "medium", "high"]);

export const productPropertySchema = z.object({
  propertyId: z.string(),
  propertyName: z.string(),
  propertyValue: z.string(),
  unit: z.string().optional().nullable(),
  description: z.string().optional().nullable(),
});

export const riskItemSchema = z.object({
  riskId: z.string(),
  riskName: z.string(),
  riskLevel: riskLevelSchema,
  description: z.string(),
  mitigationSuggestion: z.string(),
});

export const validationMetricSchema = z.object({
  metricId: z.string(),
  metricName: z.string(),
  methodSuggestion: z.string(),
  expectedRange: z.string().optional().nullable(),
  priority: z.enum(["required", "recommended", "optional"]),
});

export const akkProductSchema = z.object({
  productId: z.string(),
  productName: z.string(),
  productCategory: z.string(),
  description: z.string(),
  keyProperties: z.array(productPropertySchema),
  functionalAssumptions: z.array(z.string()),
  recommendedApplications: z.array(z.string()),
  constraints: z.array(z.string()),
  riskItems: z.array(riskItemSchema),
  validationMetrics: z.array(validationMetricSchema),
  riskLevel: riskLevelSchema,
  evidenceLevel: z.string(),
  sourceType: z.literal("mock"),
});

export const formulaGenerationRequestSchema = z.object({
  applicationTargetId: z.string(),
  targetProperties: z.array(z.string()),
  constraints: z.array(z.string()),
  preferredProductIds: z.array(z.string()),
  excludedProductIds: z.array(z.string()),
  maxIngredientCount: z.number().min(1).max(5),
  notes: z.string().optional(),
});

export const predictionResultSchema = z.object({
  predictionId: z.string(),
  targetName: z.string(),
  predictedValue: z.string(),
  unit: z.string().optional().nullable(),
  confidenceScore: z.number(),
  explanation: z.string(),
});

export const formulaIngredientSchema = z.object({
  productId: z.string(),
  productName: z.string(),
  ratioPercent: z.number(),
  role: z.string(),
});

export const companionIngredientSchema = z.object({
  ingredientId: z.string(),
  ingredientName: z.string(),
  category: z.string(),
  suggestedUsage: z.string(),
  purpose: z.string(),
  riskNote: z.string(),
});

export const knowledgeReferenceSchema = z.object({
  knowledgeId: z.string(),
  title: z.string(),
  evidenceLevel: z.string(),
  sourceUrl: z.string(),
  relevanceReason: z.string(),
  retrievalScore: z.number().optional().nullable(),
  keyPassages: z.array(z.string()).default([]),
});

export const agentTraceItemSchema = z.object({
  agentName: z.string(),
  status: z.string(),
  outputSummary: z.string(),
});

export const formulaCandidateSchema = z.object({
  candidateId: z.string(),
  candidateName: z.string(),
  composition: z.array(formulaIngredientSchema),
  companionIngredients: z.array(companionIngredientSchema).default([]),
  predictions: z.array(predictionResultSchema),
  confidenceScore: z.number(),
  confidenceLevel: confidenceLevelSchema,
  riskItems: z.array(riskItemSchema),
  validationMetrics: z.array(validationMetricSchema),
  experimentSuggestions: z.array(z.string()),
  productAdvantages: z.array(z.string()).default([]),
  upgradeSuggestions: z.array(z.string()).default([]),
  knowledgeReferences: z.array(knowledgeReferenceSchema).default([]),
  agentTrace: z.array(agentTraceItemSchema).default([]),
  approvalStatus: z.string().default("pending_research_review"),
});

export const formulaResultSchema = z.object({
  resultId: z.string(),
  recommendationType: z.literal("rd_experiment_suggestion"),
  researchUseOnly: z.boolean(),
  research_use_only: z.boolean(),
  disclaimer: z.string(),
  applicationName: z.string(),
  createdAt: z.string(),
  sourceType: z.literal("mock"),
  candidates: z.array(formulaCandidateSchema),
});

export const knowledgeItemSchema = z.object({
  knowledgeId: z.string(),
  title: z.string(),
  sourceName: z.string(),
  sourceUrl: z.string(),
  sourceFile: z.string().optional().nullable(),
  year: z.number().optional().nullable(),
  evidenceType: z.string().optional().nullable(),
  evidenceLevel: z.string(),
  topics: z.array(z.string()),
  foodMatrix: z.array(z.string()).default([]),
  akkMaterial: z.array(z.string()).default([]),
  summary: z.string(),
  usableInsights: z.array(z.string()),
  riskNotes: z.array(z.string()),
  validationMetrics: z.array(z.string()).default([]),
  retrievalScore: z.number().optional().nullable(),
  matchReasons: z.array(z.string()).default([]),
  keyPassages: z.array(z.string()).default([]),
});

export const knowledgeChunkSchema = z.object({
  chunkId: z.string(),
  knowledgeId: z.string(),
  title: z.string(),
  sourceName: z.string(),
  sourceFile: z.string().optional().nullable(),
  sourceUrl: z.string(),
  evidenceLevel: z.string(),
  evidenceType: z.string().optional().nullable(),
  topics: z.array(z.string()).default([]),
  foodMatrix: z.array(z.string()).default([]),
  text: z.string(),
  retrievalScore: z.number().optional().nullable(),
  matchReasons: z.array(z.string()).default([]),
});

export const llmStatusSchema = z.object({
  enabled: z.boolean(),
  provider: z.string(),
  model: z.string(),
  baseUrl: z.string(),
  available: z.boolean(),
  mode: z.string(),
  apiKeyConfigured: z.boolean().default(false),
  endpointScope: z.string().default("local"),
  latencyMs: z.number().int().nonnegative().nullable().default(null),
  failureCategory: z.string().nullable().default(null),
  usageRoutes: z.array(z.object({
    routeKey: z.string(),
    label: z.string(),
    enabled: z.boolean(),
    role: z.string(),
    fallback: z.string(),
  })).default([]),
  securityBoundaries: z.array(z.string()).default([]),
});

export const experimentRecordSchema = z.object({
  experimentId: z.string(),
  resultId: z.string(),
  sampleCode: z.string(),
  testName: z.string(),
  metricValue: z.number(),
  unit: z.string(),
  targetRange: z.string(),
  status: z.string(),
  riskLevel: z.string(),
  conclusion: z.string(),
  createdAt: z.string(),
});

export const experimentStageNameSchema = z.enum([
  "dataAnalysis",
  "simulation",
  "optimization",
]);

export const experimentStageStatusSchema = z.enum([
  "waiting",
  "running",
  "completed",
  "needsReview",
  "failed",
  "stopped",
]);

export const experimentStageSummarySchema = z.object({
  stage: experimentStageNameSchema,
  label: z.string(),
  status: experimentStageStatusSchema,
  canEnter: z.boolean(),
  canRun: z.boolean(),
  detail: z.string(),
});

export const experimentArchiveItemSchema = z.object({
  experimentId: z.string(),
  name: z.string(),
  batchCode: z.string().nullable(),
  currentStage: experimentStageNameSchema,
  status: experimentStageStatusSchema,
  resultSummary: z.string(),
  confidenceScore: z.number().min(0).max(1).nullable(),
  updatedAt: z.string(),
  industry: z.string().default("未配置"),
  processType: z.string().default("未配置"),
});

export const experimentArchiveResponseSchema = z.object({
  totalCount: z.number().int().nonnegative(),
  runningCount: z.number().int().nonnegative(),
  completedCount: z.number().int().nonnegative(),
  averageConfidenceScore: z.number().min(0).max(1),
  experiments: z.array(experimentArchiveItemSchema),
});

export const experimentReliabilityMetricSchema = z.object({
  label: z.string(),
  value: z.string(),
  detail: z.string(),
});

export const experimentSourceTypeSchema = z.enum(["enterprise", "sample", "blank"]);

export const productionContextSchema = z.object({
  industry: z.string().min(1).default("未配置"),
  processType: z.string().min(1).default("未配置"),
  lineName: z.string().nullable().default(null),
  materialSystem: z.string().nullable().default(null),
  criticalParameters: z.array(z.string()).default([]),
  parameterDefinitions: z.array(z.object({
    key: z.string(), label: z.string(), unit: z.string().default(""),
    min: z.number().nullable().default(null), max: z.number().nullable().default(null),
    defaultValue: z.number().nullable().default(null), source: z.string().default("实验配置"),
  })).default([]),
});

export const experimentWorkspaceOverviewSchema = z.object({
  experimentId: z.string(),
  name: z.string(),
  objective: z.string(),
  batchCode: z.string().nullable(),
  currentStage: experimentStageNameSchema,
  status: experimentStageStatusSchema,
  resultSummary: z.string(),
  statusLabel: z.string(),
  updatedAt: z.string(),
  confidenceScore: z.number().min(0).max(1).nullable(),
  modelVersion: z.string(),
  resultVersion: z.string().nullable(),
  modelType: z.string(),
  reliabilityMetrics: z.array(experimentReliabilityMetricSchema),
  stages: z.array(experimentStageSummarySchema).length(3),
  resultMetrics: z.array(experimentReliabilityMetricSchema),
  riskItems: z.array(z.string()),
  validationItems: z.array(z.string()),
  targetProduct: z.string().nullable(),
  targetMetrics: z.array(z.string()),
  adapterPack: z.object({
    enterpriseKey: z.string(), deviceType: z.string(), packVersion: z.string(),
    packId: z.string(), contentHash: z.string(),
  }).nullable(),
  sourceType: experimentSourceTypeSchema.default("enterprise"),
  sampleTemplateVersion: z.string().nullable().default(null),
  productionContext: productionContextSchema.default({
    industry: "未配置", processType: "未配置", lineName: null,
    materialSystem: null, criticalParameters: [],
  }),
});

export const experimentCreateRequestSchema = z.object({
  name: z.string().min(2), objective: z.string().min(2),
  batchCode: z.string().nullable(), targetProduct: z.string().min(1),
  targetMetrics: z.array(z.string()).min(1),
  adapterPack: z.object({
    enterpriseKey: z.string(), deviceType: z.string(), packVersion: z.string(),
  }).nullable(),
  sourceType: z.enum(["enterprise", "blank"]).default("blank"),
  productionContext: productionContextSchema,
});

export const sampleExperimentCreateSchema = z.object({
  templateKey: z.literal("algae-culture").default("algae-culture"),
  name: z.string().min(2).max(120).nullable().optional(),
});

export const experimentFileAuditEventSchema = z.object({
  auditId: z.string(),
  experimentId: z.string(),
  action: z.string(),
  stage: z.string(),
  stageLabel: z.string(),
  fileNames: z.array(z.string()),
  assetIds: z.array(z.string()),
  contentHashes: z.array(z.string()),
  duplicates: z.array(z.boolean()),
  createdAt: z.string(),
});

export const experimentFileAuditStageSummarySchema = z.object({
  stage: z.string(),
  stageLabel: z.string(),
  eventCount: z.number(),
  assetCount: z.number(),
});

export const experimentFileAuditSummarySchema = z.object({
  experimentId: z.string(),
  eventCount: z.number(),
  assetCount: z.number(),
  stageSummary: z.array(experimentFileAuditStageSummarySchema),
  lastEvent: experimentFileAuditEventSchema.nullable(),
});

export const experimentTextFileUploadRequestSchema = z.object({
  fileName: z.string().min(1),
  content: z.string(),
  encoding: z.enum(["utf8", "base64"]).optional(),
  sourceAssetId: z.string().min(1).nullable().optional(),
  sourceConversionNote: z.string().max(1000).nullable().optional(),
});

export const experimentFileAssetSchema = z.object({
  assetId: z.string(),
  experimentId: z.string(),
  originalName: z.string(),
  detectedFormat: z.string(),
  parseStatus: z.string(),
  rowCount: z.number(),
  columnNames: z.array(z.string()),
  contentHash: z.string(),
  duplicate: z.boolean(),
  duplicateOfAssetId: z.string().nullable().optional(),
  derivedFromAssetId: z.string().nullable().optional(),
  sourceConversionNote: z.string().nullable().optional(),
  intakeRunId: z.string().nullable().optional(),
  adapterApplied: z.boolean().default(false),
  pendingReviewCount: z.number().int().default(0),
});

export const sampleExperimentResultSchema = z.object({
  overview: experimentWorkspaceOverviewSchema,
  asset: experimentFileAssetSchema,
  intakeRunId: z.string(),
  templateKey: z.string(),
  templateVersion: z.string(),
  templateContentHash: z.string(),
  disclaimer: z.string(),
});
export const experimentAssetIntegrityResultSchema = z.object({
  assetId: z.string(), experimentId: z.string(), contentHash: z.string(),
  verified: z.boolean(), storageScheme: z.literal("content-addressed-sha256"),
});
export const experimentFileDeleteResultSchema = z.object({
  assetId: z.string(), experimentId: z.string(), status: z.literal("deleted"),
  retainedContentHash: z.string(), auditId: z.string(),
});

export const dataIntakeFieldTransformationSchema = z.object({
  assetId: z.string(), originalColumn: z.string(), matched: z.boolean(),
  standardField: z.string().nullable(), simulationParameter: z.string().nullable(),
  sourceUnit: z.string().nullable(), targetUnit: z.string().nullable(),
  scale: z.number(), offset: z.number(), evidence: z.array(z.string()),
  requiresHumanReview: z.boolean(),
});
export const dataCollectionLocalizationRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), assetId: z.string(),
  status: z.enum(["needsReview", "confirmed", "failed"]),
  managedWorkspace: z.boolean().default(false),
  adapterPack: z.object({
    enterpriseKey: z.string(), deviceType: z.string(), packVersion: z.string(),
    packId: z.string(), contentHash: z.string(),
  }).nullable(),
  transformationCount: z.number().int(), matchedCount: z.number().int(),
  pendingReviewCount: z.number().int(),
  transformations: z.array(dataIntakeFieldTransformationSchema), createdAt: z.string(),
});
export const cleaningAlignmentConfigSchema = z.object({
  missingValuePolicy: z.literal("keep_null").default("keep_null"),
  invalidNumericPolicy: z.literal("keep_null").default("keep_null"),
  naiveTimestampTimezone: z.literal("UTC").default("UTC"),
  numericPrecision: z.number().int().min(2).max(15).default(8),
});
export const cleaningAlignmentQualitySchema = z.object({
  missingValueCount: z.number().int(), invalidNumericCount: z.number().int(),
  invalidTimestampCount: z.number().int(), duplicateTimestampCount: z.number().int(),
  unmappedColumnCount: z.number().int(),
});
export const cleaningFieldConversionEvidenceSchema = z.object({
  assetId: z.string(), originalColumn: z.string(), standardField: z.string(),
  sourceUnit: z.string().nullable(), targetUnit: z.string().nullable(),
  scale: z.number(), offset: z.number(), formula: z.string(),
  sampleBefore: z.string().nullable(), sampleAfter: z.union([z.string(), z.number()]).nullable(),
});
export const cleaningAlignmentRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), runVersion: z.number().int(),
  status: z.enum(["completed", "needsReview", "confirmed", "failed"]),
  config: cleaningAlignmentConfigSchema, inputFingerprint: z.string(), outputHash: z.string(),
  assetCount: z.number().int(), mappingCount: z.number().int(), alignedRowCount: z.number().int(),
  alignedRows: z.array(z.record(z.union([z.string(), z.number(), z.null()]))),
  conversionEvidence: z.array(cleaningFieldConversionEvidenceSchema),
  quality: cleaningAlignmentQualitySchema,
  reviewedBy: z.string().nullable(), reviewReason: z.string().nullable(),
  reviewedAt: z.string().nullable(), createdAt: z.string(),
});
export const featureEngineeringConfigSchema = z.object({
  targetField: z.string().min(1),
  sourceFields: z.array(z.string()).min(1),
  includeRaw: z.boolean().default(true),
  lagSteps: z.array(z.number().int().positive()).default([1]),
  rollingWindows: z.array(z.number().int().min(2)).default([3]),
  includeDiff: z.boolean().default(true),
});
export const engineeredFeatureDefinitionSchema = z.object({
  name: z.string(),
  kind: z.enum(["raw", "lag", "diff", "rolling_mean", "rolling_std"]),
  sourceField: z.string(),
  formula: z.string(),
  lag: z.number().int().nullable(),
  window: z.number().int().nullable(),
  validCount: z.number().int(),
  missingRate: z.number(),
});
export const featureLeakageIssueSchema = z.object({
  code: z.string(),
  severity: z.enum(["warning", "blocking"]),
  featureName: z.string().nullable(),
  message: z.string(),
});
export const featureEngineeringRunSchema = z.object({
  featureSetId: z.string(),
  experimentId: z.string(),
  runVersion: z.number().int(),
  status: z.enum(["needsReview", "confirmed", "superseded"]),
  config: featureEngineeringConfigSchema,
  snapshotId: z.string(),
  snapshotContentHash: z.string(),
  cleaningRunId: z.string(),
  cleaningOutputHash: z.string(),
  inputFingerprint: z.string(),
  outputHash: z.string(),
  targetField: z.string(),
  candidateFeatureNames: z.array(z.string()),
  selectedFeatureNames: z.array(z.string()),
  definitions: z.array(engineeredFeatureDefinitionSchema),
  featureRows: z.array(z.record(z.union([z.string(), z.number(), z.null()]))),
  rowCount: z.number().int(),
  usableRowCount: z.number().int(),
  leakageIssues: z.array(featureLeakageIssueSchema),
  confirmedBy: z.string().nullable(),
  confirmationReason: z.string().nullable(),
  confirmedAt: z.string().nullable(),
  createdAt: z.string(),
});

export const experimentFieldMappingSuggestionSchema = z.object({
  originalColumn: z.string(),
  standardField: z.string().nullable(),
  displayName: z.string(),
  unit: z.string().nullable().optional(),
  confidenceScore: z.number(),
  requiresHumanConfirmation: z.boolean(),
  reason: z.string(),
});

export const experimentAssetFieldMappingSuggestionsSchema = z.object({
  assetId: z.string(),
  originalName: z.string(),
  suggestions: z.array(experimentFieldMappingSuggestionSchema),
});

export const experimentFieldMappingSuggestionResponseSchema = z.object({
  experimentId: z.string(),
  assetCount: z.number(),
  assets: z.array(experimentAssetFieldMappingSuggestionsSchema),
});

export const schemaRecognitionCandidateSchema = z.object({
  assetId: z.string(), originalColumn: z.string(), standardField: z.string(),
  dataType: z.enum(["number", "string", "datetime", "boolean"]),
  sourceUnit: z.string().nullable(), targetUnit: z.string().nullable(), isTimeField: z.boolean(),
  confidence: z.number().min(0).max(1), evidence: z.array(z.string()),
  requiresHumanReview: z.boolean(), reviewReasons: z.array(z.string()),
  source: z.enum(["llm", "rule", "merged"]),
});

export const schemaRecognitionRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), commandId: z.string(), status: z.enum(["completed", "failed"]),
  mode: z.enum(["llm_assisted", "rule_fallback", "rule_only"]), provider: z.string(), model: z.string(),
  fallbackReason: z.string().nullable(), candidateCount: z.number(), reviewCount: z.number(),
  conflictCount: z.number(), rejectedCount: z.number(), candidates: z.array(schemaRecognitionCandidateSchema), createdAt: z.string(),
});

export const productInnovationInputSchema = z.object({
  brief: z.string().min(5).max(5000), industry: z.string().nullable().optional(), targetMarket: z.string().nullable().optional(),
  targetUsers: z.array(z.string()).default([]), locale: z.string().default("zh-CN"), constraints: z.array(z.string()).default([]),
});
const innovationEvidenceRefs = z.array(z.string());
export const productInnovationRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), commandId: z.string(), status: z.enum(["completed", "failed"]),
  mode: z.enum(["llm_assisted", "rule_fallback"]), provider: z.string(), model: z.string(), fallbackReason: z.string().nullable(),
  requiresHumanReview: z.boolean(), createdAt: z.string(), workingName: z.string(), category: z.string(), problemStatement: z.string(),
  targetUserTags: z.array(z.string()), usageScenarios: z.array(z.string()), valuePropositions: z.array(z.string()),
  targetMetrics: z.array(z.object({ metricName: z.string(), direction: z.enum(["increase", "decrease", "target", "monitor"]), unit: z.string().nullable(), targetDescription: z.string(), evidenceRefs: innovationEvidenceRefs })),
  materialRoles: z.array(z.object({ role: z.string(), purpose: z.string(), constraints: z.array(z.string()), evidenceRefs: innovationEvidenceRefs })),
  costAssumptions: z.array(z.string()), processConstraints: z.array(z.string()), regulatoryConstraints: z.array(z.string()),
  risks: z.array(z.string()), unresolvedQuestions: z.array(z.string()),
  validationPlan: z.array(z.object({ title: z.string(), purpose: z.string(), evidenceRefs: innovationEvidenceRefs, validationItems: z.array(z.string()) })), evidenceRefs: innovationEvidenceRefs,
});

export const productRequirementSnapshotSchema = productInnovationRunSchema.omit({
  runId: true, experimentId: true, commandId: true, status: true, mode: true,
  provider: true, model: true, fallbackReason: true, requiresHumanReview: true, createdAt: true,
}).extend({ fixedBoundaries: z.array(z.string()) });

export const productRequirementVersionSchema = z.object({
  requirementVersionId: z.string(), experimentId: z.string(), version: z.number().int().min(1),
  parentVersionId: z.string().nullable(), sourceRunId: z.string(), sourceCommandId: z.string(),
  confirmationCommandId: z.string(), status: z.literal("confirmed"), snapshot: productRequirementSnapshotSchema,
  contentHash: z.string(), operator: z.string(), reason: z.string(), confirmedAt: z.string(),
  disclaimer: z.literal("研发实验建议"),
});

export const experimentConfirmedFieldMappingSchema = z.object({
  assetId: z.string(),
  originalColumn: z.string(),
  standardField: z.string(),
  displayName: z.string(),
  unit: z.string().nullable().optional(),
  confirmedBy: z.string(),
  confirmed: z.boolean().default(true),
});

export const experimentConfirmFieldMappingsRequestSchema = z.object({
  mappings: z.array(experimentConfirmedFieldMappingSchema).min(1),
});

export const experimentConfirmedFieldMappingSetSchema = z.object({
  experimentId: z.string(),
  mappingCount: z.number(),
  mappings: z.array(experimentConfirmedFieldMappingSchema),
});

export const experimentFieldDictionaryEntrySchema = z.object({
  sourceColumn: z.string(),
  standardField: z.string(),
  displayName: z.string(),
  unit: z.string().nullable().optional(),
  createdBy: z.string(),
});

export const experimentFieldDictionaryUpsertRequestSchema = z.object({
  entries: z.array(experimentFieldDictionaryEntrySchema).min(1),
});

export const experimentFieldDictionarySchema = z.object({
  experimentId: z.string(),
  entryCount: z.number(),
  entries: z.array(experimentFieldDictionaryEntrySchema),
});

export const experimentCleaningQualitySummarySchema = z.object({
  missingValueCount: z.number(),
  invalidNumericCount: z.number(),
  unmappedColumnCount: z.number(),
});

export const experimentAssetCleaningPreviewSchema = z.object({
  assetId: z.string(),
  originalName: z.string(),
  rowCount: z.number(),
  cleanedRows: z.array(z.record(z.union([z.string(), z.number(), z.null()]))),
  quality: experimentCleaningQualitySummarySchema,
  cleaningLogs: z.array(z.string()),
});

export const experimentCleaningPreviewResponseSchema = z.object({
  experimentId: z.string(),
  assetCount: z.number(),
  assets: z.array(experimentAssetCleaningPreviewSchema),
});

export const experimentAlignmentAssetSummarySchema = z.object({
  assetId: z.string(),
  originalName: z.string(),
  timestampCount: z.number(),
  fields: z.array(z.string()),
});

export const experimentAlignmentPreviewResponseSchema = z.object({
  experimentId: z.string(),
  assetCount: z.number(),
  timestampCount: z.number(),
  missingCellCount: z.number(),
  assetSummaries: z.array(experimentAlignmentAssetSummarySchema),
  alignedRows: z.array(z.record(z.union([z.string(), z.number(), z.null()]))),
  alignmentLogs: z.array(z.string()),
});

export const experimentFeatureSummarySchema = z.object({
  field: z.string(),
  count: z.number(),
  min: z.number(),
  max: z.number(),
  mean: z.number(),
  first: z.number(),
  last: z.number(),
  delta: z.number(),
  windowMean: z.number(),
});

export const experimentFeatureAnomalyHintSchema = z.object({
  field: z.string(),
  timestamp: z.string(),
  value: z.number(),
  reason: z.string(),
});

export const experimentFeaturePreviewResponseSchema = z.object({
  experimentId: z.string(),
  rowCount: z.number(),
  featureCount: z.number(),
  features: z.array(experimentFeatureSummarySchema),
  anomalyHints: z.array(experimentFeatureAnomalyHintSchema),
});

export const experimentDatasetSnapshotSchema = z.object({
  snapshotId: z.string(),
  experimentId: z.string(),
  assetCount: z.number(),
  evidenceAssetCount: z.number().default(0),
  analysisAssetIds: z.array(z.string()).default([]),
  sourceEvidenceAssetIds: z.array(z.string()).default([]),
  mappingCount: z.number(),
  alignedRowCount: z.number(),
  featureCount: z.number(),
  anomalyCount: z.number(),
  contentHash: z.string(),
  cleaningRunId: z.string().nullable().optional(),
  cleaningOutputHash: z.string().nullable().optional(),
  alignedRows: z.array(z.record(z.union([z.string(), z.number(), z.null()]))).default([]),
  status: z.string(),
  createdAt: z.string(),
});

export const experimentModelingPlanPreviewSchema = z.object({
  experimentId: z.string(),
  snapshotId: z.string(),
  targetField: z.string(),
  candidateFeatures: z.array(z.string()),
  recommendedModelType: z.string(),
  trainSplitRatio: z.number(),
  validationSplitRatio: z.number(),
  evaluationMetrics: z.array(z.string()),
  riskHints: z.array(z.string()),
  status: z.string(),
});

export const experimentTrainingAgentStageSchema = z.object({
  agentName: z.string(),
  stageLabel: z.string(),
  status: z.string(),
  detail: z.string(),
});

export const experimentTrainingTaskPreviewSchema = z.object({
  taskId: z.string(),
  experimentId: z.string(),
  snapshotId: z.string(),
  planTargetField: z.string(),
  recommendedModelType: z.string(),
  evaluationMetrics: z.array(z.string()),
  status: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  agentStages: z.array(experimentTrainingAgentStageSchema),
});

export const experimentTrainingResultMetricsSchema = z.object({
  mae: z.number(),
  rmse: z.number(),
  r2: z.number(),
});

export const experimentTrainingResultSummarySchema = z.object({
  experimentId: z.string(),
  taskId: z.string(),
  targetField: z.string(),
  status: z.string(),
  confidenceLevel: z.string(),
  metrics: experimentTrainingResultMetricsSchema,
  riskNotes: z.array(z.string()),
  recommendations: z.array(z.string()),
  manualReviewItems: z.array(z.string()),
  generatedAt: z.string(),
});

export const resultInterpretationRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), commandId: z.string(), status: z.enum(["completed", "failed"]),
  mode: z.enum(["llm_assisted", "rule_fallback"]), provider: z.string(), model: z.string(),
  sourceTaskId: z.string(), sourceGeneratedAt: z.string(),
  authoritativeMetrics: experimentTrainingResultMetricsSchema, confidenceLevel: z.string(), overallSummary: z.string(),
  metricInterpretations: z.array(z.object({ metricKey: z.enum(["mae", "rmse", "r2"]), value: z.number(), interpretation: z.string(), evidenceRefs: z.array(z.string()) })),
  observedPatterns: z.array(z.object({ statement: z.string(), evidenceRefs: z.array(z.string()) })),
  riskExplanations: z.array(z.object({ riskId: z.string(), originalRisk: z.string(), explanation: z.string(), evidenceRefs: z.array(z.string()) })),
  nextExperimentSuggestions: z.array(z.object({ title: z.string(), purpose: z.string(), evidenceRefs: z.array(z.string()), validationItems: z.array(z.string()), requiresHumanReview: z.boolean() })),
  unresolvedQuestions: z.array(z.string()), fallbackReason: z.string().nullable(), rejectedCount: z.number(), createdAt: z.string(),
});

export const experimentResearchBriefSummarySchema = z.object({
  experimentId: z.string(),
  taskId: z.string(),
  title: z.string(),
  objective: z.string(),
  dataSummary: z.string(),
  modelSummary: z.string(),
  riskSummary: z.string(),
  nextActions: z.array(z.string()),
  manualConfirmationItems: z.array(z.string()),
  status: z.string(),
  generatedAt: z.string(),
});

export const experimentSimulationRangeSchema = z.object({
  min: z.number(),
  max: z.number(),
  unit: z.string(),
});

export const experimentSimulationCandidatePlanSchema = z.object({
  planName: z.string(),
  temperatureC: z.number(),
  ph: z.number(),
  durationHours: z.number(),
  reason: z.string(),
});

export const experimentSimulationInputSummarySchema = z.object({
  experimentId: z.string(),
  targetField: z.string(),
  objective: z.string(),
  recommendedRanges: z.record(experimentSimulationRangeSchema),
  candidatePlans: z.array(experimentSimulationCandidatePlanSchema),
  manualConfirmationItems: z.array(z.string()),
  status: z.string(),
  generatedAt: z.string(),
});

export const agentRunStatusSchema = z.enum(["waiting", "running", "interrupted", "completed", "needsReview", "failed", "stopped"]);

export const agentRunNodeSchema = z.object({
  nodeId: z.string(),
  agentKey: z.string(),
  agentName: z.string(),
  stageLabel: z.string(),
  status: agentRunStatusSchema,
  progressPercent: z.number().min(0).max(100),
  inputSummary: z.array(z.string()),
  methodSummary: z.array(z.string()),
  metricSummary: z.array(z.string()),
  outputSummary: z.array(z.string()),
  startedAt: z.string().nullable(),
  completedAt: z.string().nullable(),
});

export const agentRunEventSchema = z.object({
  eventId: z.string(),
  eventType: z.string(),
  nodeId: z.string().nullable(),
  title: z.string(),
  detail: z.string(),
  createdAt: z.string(),
});

export const agentGuidancePreviewSchema = z.object({
  guidanceId: z.string(),
  experimentId: z.string(),
  runId: z.string(),
  prompt: z.string(),
  intentSummary: z.string(),
  affectedNodes: z.array(z.string()),
  planChanges: z.array(z.string()),
  comparisonImpact: z.string(),
  safeCheckpoint: z.string(),
  requiresRestart: z.boolean(),
  status: z.enum(["preview", "scheduled", "applied", "rejected"]),
});

export const humanDecisionSchema = z.object({
  decisionId: z.string(),
  decision: z.enum(["approved", "rejected"]),
  reason: z.string(),
  operator: z.string(),
  impactScope: z.array(z.string()),
  createdAt: z.string(),
});

export const experimentAgentRunSchema = z.object({
  runId: z.string(),
  runtimeBackend: z.string(),
  runtimeRunId: z.string(),
  runtimeRevision: z.number().int().min(1),
  parentRunId: z.string().nullable(),
  experimentId: z.string(),
  version: z.number().int().min(1),
  status: agentRunStatusSchema,
  currentNodeId: z.string().nullable(),
  progressPercent: z.number().min(0).max(100),
  nodes: z.array(agentRunNodeSchema).length(7),
  events: z.array(agentRunEventSchema),
  pendingGuidance: agentGuidancePreviewSchema.nullable(),
  appliedGuidance: z.array(agentGuidancePreviewSchema),
  humanDecisions: z.array(humanDecisionSchema),
  createdAt: z.string(),
  updatedAt: z.string(),
  disclaimer: z.string(),
});

export const agentRuntimeStatusSchema = z.object({
  requestedBackend: z.string(), effectiveBackend: z.string(), fallbackReason: z.string().nullable(),
  backends: z.array(z.object({ backend: z.string(), installed: z.boolean(), enabled: z.boolean(), version: z.string().nullable(), capabilities: z.array(z.string()) })),
  localModel: z.object({ configured: z.boolean(), provider: z.string(), model: z.string(), endpointLabel: z.string(), liveProbeEndpoint: z.string() }),
  executionBoundary: z.array(z.string()),
  checkpointBackend: z.enum(["memory", "sqlite"]), persistent: z.boolean(), recoverableRuns: z.number().int().min(0),
});

export const agentCommandTaskSchema = z.object({
  taskId: z.string(), commandId: z.string(), requestFingerprint: z.string(), experimentId: z.string(), runId: z.string(),
  targetKind: z.enum(["dataAnalysis", "simulation", "optimization", "research", "adaptation"]),
  action: z.enum(["advance", "stop", "simulationCreate", "simulationAdvance", "simulationStop", "simulationRetry", "optimizationCreate", "optimizationSubmit", "optimizationAdvance", "researchTrial", "featureBindingSuggest"]), expectedRevision: z.number().int().min(1), payload: z.record(z.unknown()),
  maxAttempts: z.number().int().min(1), priority: z.number().int(), parentTaskId: z.string().nullable(), status: z.enum(["queued", "leased", "completed", "failed", "deadLetter", "cancelled"]),
  attempts: z.number().int().min(0), availableAt: z.string(), leaseOwner: z.string().nullable(), leaseToken: z.string().nullable(),
  leaseExpiresAt: z.string().nullable(), heartbeatAt: z.string().nullable(), resultRevision: z.number().int().nullable(), resultRunId: z.string().nullable(),
  cancelRequestedAt: z.string().nullable(), cancelledAt: z.string().nullable(),
  requiredCapabilities: z.array(z.enum(["cpu", "gpu", "localLlm"])),
  errorCategory: z.string().nullable(), errorMessage: z.string().nullable(), createdAt: z.string(), updatedAt: z.string(),
});
export const agentCommandSummarySchema = z.object({
  taskId: z.string(), commandId: z.string(), experimentId: z.string(), runId: z.string(),
  targetKind: z.string(), action: z.string(),
  status: z.enum(["queued", "leased", "completed", "failed", "deadLetter", "cancelled"]),
  attempts: z.number().int().min(0), maxAttempts: z.number().int().min(1), priority: z.number().int(),
  resultRevision: z.number().int().nullable(), resultRunId: z.string().nullable(), errorCategory: z.string().nullable(),
  createdAt: z.string(), updatedAt: z.string(),
});
export const agentQueueStatusSchema = z.object({
  backend: z.enum(["memory-sqlite", "sqlite", "postgres", "dramatiq-redis"]), persistent: z.boolean(), counts: z.record(z.number().int().min(0)), workerProcessRequired: z.boolean(),
  requestedBackend: z.string(), fallbackReason: z.string().nullable(),
  dispatchBackend: z.enum(["polling", "dramatiq-redis"]),
  workers: z.array(z.object({
    workerId: z.string(), capabilities: z.array(z.string()), maxConcurrent: z.number().int().min(1),
    labels: z.record(z.string()), heartbeatAt: z.string(), status: z.enum(["online", "offline"]),
    activeTasks: z.number().int().min(0), availableSlots: z.number().int().min(0),
  })),
});
export const agentManifestSchema = z.object({
  agentKey: z.string(), version: z.string(), displayName: z.string(), description: z.string(),
  kind: z.enum(["supervisor", "specialist", "humanGate", "toolAdapter"]),
  framework: z.enum(["langgraph", "deterministic", "human"]), capabilities: z.array(z.string()),
  requiredWorkerCapabilities: z.array(z.enum(["cpu", "gpu", "localLlm"])), inputSchema: z.string(), outputSchema: z.string(),
  enabled: z.boolean(), safetyBoundary: z.array(z.string()),
});
export const workflowManifestSchema = z.object({
  workflowKey: z.string(), version: z.string(), displayName: z.string(), description: z.string(),
  nodes: z.array(z.object({ nodeId: z.string(), agentKey: z.string(), stageLabel: z.string(), requiresHuman: z.boolean(), inputSummary: z.array(z.string()), methodSummary: z.array(z.string()), metricSummary: z.array(z.string()), outputSummary: z.array(z.string()) })),
  edges: z.record(z.array(z.string())), entryNodeId: z.string(),
});
export const agentCatalogSnapshotSchema = z.object({
  framework: z.literal("langgraph"), frameworkVersion: z.string(), agentCount: z.number().int(), workflowCount: z.number().int(),
  agents: z.array(agentManifestSchema), workflows: z.array(workflowManifestSchema), disclaimer: z.literal("研发实验建议"),
});
export const researchTrialSchema = z.object({
  trialId: z.string(), sequence: z.number().int(), commandId: z.string(), requestFingerprint: z.string(), hypothesis: z.string(),
  parameterPatch: z.record(z.unknown()), metrics: z.record(z.number()), primaryScore: z.number(), status: z.enum(["keep", "discard", "crash"]),
  comparedToTrialId: z.string().nullable(), deltaFromBestBefore: z.number(), deltaFromBaseline: z.number(), fixedBudgetSeconds: z.number().int(),
  durationSeconds: z.number(), artifactFingerprint: z.string(), artifactUri: z.string().nullable(), runnerKey: z.string(),
  datasetFingerprint: z.string().nullable(), featureNames: z.array(z.string()), targetField: z.string().nullable(), modelType: z.string().nullable(), errorMessage: z.string().nullable(), createdAt: z.string(),
  featureRanges: z.record(z.object({ min: z.number(), max: z.number() })).default({}),
  modelCard: z.object({
    schemaVersion: z.string(),
    algorithm: z.enum(["ridge", "random_forest", "gradient_boosting"]),
    modelType: z.string(),
    parameters: z.record(z.unknown()),
    randomState: z.number().int(),
    datasetSnapshotId: z.string(),
    datasetFingerprint: z.string(),
    featureNames: z.array(z.string()),
    targetField: z.string(),
    splitStrategy: z.string(),
    shuffle: z.boolean(),
    trainRows: z.number().int(),
    holdoutRows: z.number().int(),
    crossValidationFolds: z.array(z.object({
      fold: z.number().int(),
      trainStart: z.number().int(),
      trainEnd: z.number().int(),
      validationStart: z.number().int(),
      validationEnd: z.number().int(),
      trainRows: z.number().int(),
      validationRows: z.number().int(),
      metrics: z.record(z.number()),
    })),
    crossValidationMean: z.record(z.number()),
    crossValidationStd: z.record(z.number()),
    holdoutMetrics: z.record(z.number()),
    holdoutDiagnostics: z.object({
      trainTargetStd: z.number(), holdoutTargetStd: z.number(), varianceRatio: z.number(),
      trainTargetRange: z.number(), holdoutTargetRange: z.number(), normalizedMaeByTrainRange: z.number(),
      r2Stable: z.boolean(), r2Interpretation: z.enum(["standard", "unstable_low_variance_holdout"]),
    }).optional(),
    featureRanges: z.record(z.object({ min: z.number(), max: z.number() })),
    pythonVersion: z.string(),
    sklearnVersion: z.string(),
    limitations: z.array(z.string()),
  }).nullable().optional(),
});
export const researchCampaignSchema = z.object({
  campaignId: z.string(), experimentId: z.string(), createCommandId: z.string(), requestFingerprint: z.string(), agentKey: z.string(), agentVersion: z.string(),
  datasetSnapshotId: z.string(), evaluationHarnessHash: z.string(), primaryMetric: z.string(), direction: z.enum(["maximize", "minimize"]),
  fixedBudgetSeconds: z.number().int(), minimumImprovement: z.number(), promotionThresholds: z.record(z.number()), baselineTrialId: z.string(), bestTrialId: z.string(),
  status: z.enum(["active", "needsReview", "completed", "stopped"]), trials: z.array(researchTrialSchema), promotion: z.object({
    trialId: z.string(), status: z.enum(["approved", "rejected"]), operator: z.string(), reason: z.string(), gateChecks: z.record(z.boolean()), promotedModelVersion: z.string().nullable(), createdAt: z.string(),
  }).nullable(), createdAt: z.string(), updatedAt: z.string(), mode: z.enum(["mock_evaluation", "real_runner"]), runnerKey: z.string(), runnerFallbackReason: z.string().nullable(), disclaimer: z.literal("研发实验建议"),
});
export const modelEvaluationReportSchema = z.object({
  reportId: z.string(),
  experimentId: z.string(),
  reportVersion: z.number().int(),
  status: z.enum(["needsReview", "confirmed", "rejected"]),
  modelVersion: z.string(),
  campaignId: z.string(),
  trialId: z.string(),
  modelType: z.string(),
  artifactFingerprint: z.string(),
  artifactVerified: z.boolean(),
  datasetSnapshotId: z.string(),
  datasetFingerprint: z.string(),
  inputFingerprint: z.string(),
  performanceMetrics: z.record(z.number()),
  residualDiagnostics: z.object({
    meanResidual: z.number(),
    residualStd: z.number(),
    meanAbsoluteResidual: z.number(),
    maxAbsoluteResidual: z.number(),
    lag1Autocorrelation: z.number(),
    predictionResidualCorrelation: z.number(),
  }),
  predictionInterval: z.object({
    method: z.literal("empirical_holdout_absolute_error"),
    confidenceLevel: z.number(),
    margin: z.number(),
    empiricalCoverage: z.number(),
    sampleCount: z.number().int(),
    calibrated: z.boolean(),
    limitation: z.string(),
  }),
  driftDiagnostics: z.array(z.object({
    feature: z.string(),
    standardizedMeanShift: z.number(),
    holdoutRangeCoverage: z.number(),
    severity: z.enum(["low", "medium", "high"]),
    trainMean: z.number(),
    holdoutMean: z.number(),
  })),
  featureEffects: z.array(z.object({
    feature: z.string(),
    effect: z.number(),
    normalizedImportance: z.number(),
    method: z.string(),
  })),
  scoreBreakdown: z.record(z.number()),
  reliabilityScore: z.number().min(0).max(1),
  reliabilityGrade: z.enum(["low", "medium", "high"]),
  recommendedAdmission: z.boolean(),
  admissionAllowed: z.boolean(),
  admissionReasons: z.array(z.string()),
  reviewedBy: z.string().nullable(),
  reviewReason: z.string().nullable(),
  reviewedAt: z.string().nullable(),
  createdAt: z.string(),
});

export const numericRangeSchema = z.object({
  min: z.number(),
  max: z.number(),
  unit: z.string(),
});

export const processProductionLineSchema = z.object({
  lineId: z.string(),
  lineName: z.string(),
  equipmentType: z.string(),
  workingVolume: z.string(),
  temperatureRange: numericRangeSchema,
  phRange: numericRangeSchema,
  agitationRange: numericRangeSchema,
  anaerobicCapability: z.string(),
  aerationCapability: z.string(),
  sensors: z.array(z.string()),
  downstreamCapabilities: z.array(z.string()),
  feasibilityScore: z.number(),
  dataCompleteness: z.string(),
  limitations: z.array(z.string()),
});

export const processTaskRequestSchema = z.object({
  targetProductName: z.string(),
  targetProductForm: z.string(),
  akkProductType: z.string(),
  applicationDirection: z.string(),
  targetContent: z.string().optional(),
  activityTarget: z.string().optional(),
  stabilityTarget: z.string().optional(),
  costLimit: z.string().optional(),
  optimizationStrategy: z.string(),
  allowCoCulture: z.boolean(),
  targetScale: z.string(),
  constraints: z.array(z.string()),
  productionLineId: z.string(),
  currentTemperature: z.number().optional().nullable(),
  currentPh: z.number().optional().nullable(),
  currentAgitationRpm: z.number().optional().nullable(),
  currentVolumeL: z.number().optional().nullable(),
  sensorCapability: z.string().optional().nullable(),
  downstreamCapability: z.string().optional().nullable(),
});

export const processScoreBreakdownSchema = z.object({
  overallScore: z.number(),
  yieldScore: z.number(),
  activityScore: z.number(),
  stabilityScore: z.number(),
  costScore: z.number(),
  riskScore: z.number(),
  feasibilityScore: z.number(),
  confidenceScore: z.number(),
});

export const processRecommendedParametersSchema = z.object({
  temperature: numericRangeSchema,
  ph: numericRangeSchema,
  cultureTimeHours: numericRangeSchema,
  agitationRpm: numericRangeSchema,
  aerationMode: z.string(),
  inoculationRatio: z.string(),
  coCultureRatio: z.string().nullable().optional(),
});

export const processCandidatePlanSchema = z.object({
  planId: z.string(),
  planType: z.string(),
  displayName: z.string(),
  summary: z.string(),
  recommendedParameters: processRecommendedParametersSchema,
  scoreBreakdown: processScoreBreakdownSchema,
  riskItems: z.array(z.string()),
  validationMetrics: z.array(z.string()),
  explanation: z.array(z.string()),
});

export const processSurfacePointSchema = z.object({
  temperature: z.number(),
  ph: z.number(),
  score: z.number(),
  riskLevel: z.string(),
});

export const processSurfaceSchema = z.object({
  xAxisLabel: z.string(),
  yAxisLabel: z.string(),
  zAxisLabel: z.string(),
  points: z.array(processSurfacePointSchema),
});

export const processReportSchema = z.object({
  title: z.string(),
  parameterWindows: z.array(z.string()),
  predictedOutcomes: z.array(z.string()),
  riskControls: z.array(z.string()),
  validationPlan: z.array(z.string()),
  nextStepSuggestion: z.string(),
});

export const generatedProcessTaskSchema = z.object({
  taskId: z.string(),
  targetSummary: z.string(),
  selectedLine: processProductionLineSchema,
  candidatePlans: z.array(processCandidatePlanSchema),
  surface: processSurfaceSchema,
  report: processReportSchema,
  disclaimer: z.string(),
});

export const processFeedbackRequestSchema = z.object({
  taskId: z.string(),
  actualYield: z.string(),
  actualActivity: z.string(),
  contaminationObserved: z.boolean(),
  equipmentAbnormalities: z.array(z.string()),
  conclusion: z.string(),
  notes: z.string(),
});

export const processFeedbackSchema = processFeedbackRequestSchema.extend({
  feedbackId: z.string(),
});

export const simulationCarbonSourceSchema = z.enum(["BFP", "UBFP", "lambdaCarrageenan", "iotaCarrageenan", "fucoidan", "porphyraGlycoprotein", "PHP", "agar"]);
export const simulationProductFormatSchema = z.enum(["culture-medium", "postbiotic-powder", "fish-ball", "encapsulated-bead"]);

export const simulationRangeSchema = z.object({
  min: z.number(),
  max: z.number(),
  unit: z.string(),
});

export const simulationPredictRequestSchema = z.object({
  targetProduct: z.string().min(1).max(80),
  productFormat: simulationProductFormatSchema,
  carbonSource: simulationCarbonSourceSchema,
  carbonConcentration: z.number().min(0).max(4).multipleOf(0.05),
  cultureHours: z.number().min(12).max(96).multipleOf(1),
  temperatureC: z.number().min(20).max(55).multipleOf(0.1),
  ph: z.number().min(4.5).max(8.5).multipleOf(0.01),
  anaerobicScore: z.number().min(0).max(1).multipleOf(0.01),
  pressureMpa: z.number().min(0).max(450).multipleOf(1),
  stirringRpm: z.number().min(0).max(400).multipleOf(1),
  pretreated: z.boolean(),
  useLlmAdvisor: z.boolean(),
  customParameters: z.record(z.string().regex(/^custom_[1-9][0-9]*$/), z.number().finite()).refine((value) => Object.keys(value).length <= 50).default({}),
});

export const simulationPredictionsSchema = z.object({
  molecularWeightKda: z.number(),
  akkGrowthScore: z.number(),
  scfaScore: z.number(),
  barrierScore: z.number(),
  overallScore: z.number(),
});

export const simulationRecommendedSettingsSchema = z.object({
  carbonSource: simulationCarbonSourceSchema,
  carbonConcentration: simulationRangeSchema,
  temperatureC: simulationRangeSchema,
  ph: simulationRangeSchema,
  anaerobicScoreMinimum: z.number(),
  cultureHours: simulationRangeSchema,
  stirringRpm: simulationRangeSchema,
  pressureMpa: simulationRangeSchema,
});

export const simulationLlmAdvisorSchema = z.object({
  enabled: z.boolean(),
  provider: z.string(),
  model: z.string(),
  apiKeyConfigured: z.boolean(),
  advice: z.string().nullable().optional(),
  mode: z.string(),
});

export const simulationPredictResponseSchema = z.object({
  label: z.literal("研发实验建议"),
  researchUseOnly: z.boolean(),
  disclaimer: z.string(),
  targetProduct: z.string(),
  customParameters: z.record(z.string().regex(/^custom_[1-9][0-9]*$/), z.number().finite()).default({}),
  confidence: confidenceLevelSchema,
  predictions: simulationPredictionsSchema,
  recommendedSettings: simulationRecommendedSettingsSchema,
  risks: z.array(z.string()),
  validationIndicators: z.array(z.string()),
  curve: z.array(z.object({
    carbonConcentration: z.number(),
    akkGrowthScore: z.number(),
    scfaScore: z.number(),
    overallScore: z.number(),
  })),
  llmAdvisor: simulationLlmAdvisorSchema,
  predictionSource: z.enum(["rule_model", "promoted_model"]),
  modelVersion: z.string().nullable(),
  artifactFingerprint: z.string().nullable(),
  datasetFingerprint: z.string().nullable(),
  extrapolated: z.boolean(),
  fallbackReason: z.string().nullable(),
});

export const promotedModelPredictionSchema = z.object({
  predictionSource: z.literal("promoted_model"), experimentId: z.string(), modelVersion: z.string(), trialId: z.string(),
  datasetSnapshotId: z.string(), datasetFingerprint: z.string(), artifactFingerprint: z.string(), targetField: z.string(),
  prediction: z.number(), extrapolated: z.boolean(), outOfRangeFeatures: z.array(z.string()), featureValues: z.record(z.number()),
});

export const promotedModelRecordSchema = z.object({
  modelVersion: z.string(), experimentId: z.string(), campaignId: z.string(), trialId: z.string(),
  artifactFingerprint: z.string(), artifactUri: z.string(), datasetSnapshotId: z.string(), datasetFingerprint: z.string(),
  runnerKey: z.string(), modelType: z.string(), featureNames: z.array(z.string()), targetField: z.string(),
  featureRanges: z.record(z.object({ min: z.number(), max: z.number() })), metrics: z.record(z.number()),
  approvedBy: z.string(), approvalReason: z.string(), approvedAt: z.string(), status: z.literal("approved"),
});

export const deviceAdapterPackSelectorSchema = z.object({
  enterpriseKey: z.string(), deviceType: z.string(), packVersion: z.string(),
});
export const deviceAdapterPackReferenceSchema = deviceAdapterPackSelectorSchema.extend({
  packId: z.string(), contentHash: z.string().regex(/^sha256:[0-9a-f]{64}$/),
});
export const deviceAdapterEntrySchema = z.object({
  sourceFieldAlias: z.string(), standardField: z.string(), simulationParameter: z.string(),
  sourceUnit: z.string().nullable(), targetUnit: z.string().nullable(),
  scale: z.number(), offset: z.number(),
});
export const deviceAdapterPackSchema = deviceAdapterPackSelectorSchema.extend({
  packId: z.string(), entries: z.array(deviceAdapterEntrySchema), createdBy: z.string(),
  createdAt: z.string(), integrityScheme: z.literal("canonical-json-sha256"),
  contentHash: z.string().regex(/^sha256:[0-9a-f]{64}$/),
});
export const deviceAdapterPackCreateSchema = deviceAdapterPackSelectorSchema.extend({
  entries: z.array(deviceAdapterEntrySchema).min(1), createdBy: z.string().min(1),
});
export const deviceAdapterEntryChangeSchema = z.object({
  sourceFieldAlias: z.string(), changedFields: z.array(z.string()),
  before: deviceAdapterEntrySchema, after: deviceAdapterEntrySchema,
});
export const deviceAdapterPackComparisonSchema = z.object({
  enterpriseKey: z.string(), deviceType: z.string(),
  baseVersion: z.string(), targetVersion: z.string(),
  baseContentHash: z.string(), targetContentHash: z.string(),
  added: z.array(deviceAdapterEntrySchema), removed: z.array(deviceAdapterEntrySchema),
  changed: z.array(deviceAdapterEntryChangeSchema), unchangedCount: z.number().int().min(0),
});

export const featureBindingSuggestionCandidateSchema = z.object({
  modelFeature: z.string(), standardField: z.string(), simulationParameter: z.string().nullable(),
  sourceUnit: z.string().nullable().optional(), targetUnit: z.string().nullable().optional(),
  scale: z.number(), offset: z.number(), confidence: z.number().min(0).max(1),
  source: z.enum(["rule", "llm", "merged", "adapter"]), evidence: z.array(z.string()),
  requiresHumanReview: z.boolean(), reviewReasons: z.array(z.string()),
});

export const featureBindingSuggestionRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), modelVersion: z.string(), commandId: z.string(),
  requestFingerprint: z.string(), adapterPack: deviceAdapterPackReferenceSchema.nullable(),
  status: z.enum(["completed", "failed"]), mode: z.enum(["rule_only", "llm_assisted", "rule_fallback"]),
  provider: z.string(), model: z.string(), fallbackReason: z.string().nullable(),
  candidateCount: z.number().int().min(0), reviewCount: z.number().int().min(0),
  conflictCount: z.number().int().min(0), rejectedCount: z.number().int().min(0),
  readyForConfirmation: z.boolean(), candidates: z.array(featureBindingSuggestionCandidateSchema),
  activatedBindingVersion: z.null(), createdAt: z.string(),
});

export const featureBindingEntrySchema = z.object({
  modelFeature: z.string(), standardField: z.string(), simulationParameter: z.string(),
  sourceUnit: z.string().nullable().optional(), targetUnit: z.string().nullable().optional(), scale: z.number(), offset: z.number(),
});
export const featureBindingVersionSchema = z.object({
  bindingVersion: z.string(), experimentId: z.string(), modelVersion: z.string(), featureNames: z.array(z.string()),
  entries: z.array(featureBindingEntrySchema), confirmedBy: z.string(), confirmationReason: z.string(),
  suggestionRunId: z.string().nullable(), adapterPack: deviceAdapterPackReferenceSchema.nullable(),
  createdAt: z.string(), status: z.literal("confirmed"),
});
export const modelAssetEvaluationSchema = z.object({
  reportId: z.string(), status: z.string(), reliabilityScore: z.number().min(0).max(1), reliabilityGrade: z.string(),
  recommendedAdmission: z.boolean(), admissionAllowed: z.boolean(), artifactVerified: z.boolean(),
});
export const modelSimulationUsageSchema = z.object({
  runId: z.string(), version: z.number().int(), status: z.string(), bindingVersions: z.array(z.string()),
  reliabilityScore: z.number().min(0).max(1).nullable(), officialSnapshotId: z.string().nullable(), updatedAt: z.string(),
});
export const modelAssetSummarySchema = z.object({
  experimentId: z.string(), experimentName: z.string(), modelVersion: z.string(), targetField: z.string(), modelType: z.string(),
  approvedAt: z.string(), approvedBy: z.string(), status: z.string(), latest: z.boolean(), datasetSnapshotId: z.string(),
  featureCount: z.number().int().min(1), metrics: z.record(z.number()), artifactVerified: z.boolean(),
  evaluationStatus: z.string().nullable(), reliabilityScore: z.number().min(0).max(1).nullable(),
  bindingVersion: z.string().nullable(), simulationUsageCount: z.number().int().min(0),
});
export const enterpriseKnowledgeEntrySchema = z.object({
  knowledgeId: z.string(), experimentId: z.string(), experimentName: z.string(),
  category: z.enum(["verifiedFact", "applicabilityBoundary", "validationPlan"]),
  title: z.string(), content: z.string(), evidenceRefs: z.array(z.string()).min(1),
  sourceReportId: z.string(), sourceReportVersion: z.number().int().min(1), sourceStatementId: z.string(),
  sourceInputFingerprint: z.string(), contentHash: z.string(), reviewedBy: z.string(), reviewReason: z.string(),
  reviewedAt: z.string(), depositedAt: z.string(), status: z.literal("active"),
});
export const enterpriseKnowledgeUsageSchema = z.object({
  usageId: z.string(), experimentId: z.string(), knowledgeIds: z.array(z.string()).min(1),
  sourceEntries: z.array(enterpriseKnowledgeEntrySchema).min(1),
  purpose: z.enum(["modeling", "simulation", "optimization", "reporting"]), targetVersion: z.string(),
  operator: z.string(), note: z.string(), usageFingerprint: z.string(), createdAt: z.string(),
});
export const modelAssetDetailSchema = z.object({
  experimentName: z.string(), latest: z.boolean(), artifactVerified: z.boolean(), record: promotedModelRecordSchema,
  evaluationReport: modelAssetEvaluationSchema.nullable(), binding: featureBindingVersionSchema.nullable(),
  simulationUsages: z.array(modelSimulationUsageSchema), knowledgeUsages: z.array(enterpriseKnowledgeUsageSchema).default([]), disclaimer: z.string(),
});
export const compositeModelPredictionSchema = z.object({
  experimentId: z.string(), predictionSource: z.literal("promoted_model_composite"), reliability: confidenceLevelSchema,
  targets: z.array(z.object({
    targetField: z.string(), prediction: z.number(), interval: z.object({ lower: z.number(), upper: z.number(), method: z.literal("approximate95_rmse"), coverageClaim: z.literal("not_calibrated") }),
    modelVersion: z.string(), trialId: z.string(), bindingVersion: z.string(), datasetSnapshotId: z.string(), datasetFingerprint: z.string(), artifactFingerprint: z.string(),
    extrapolated: z.boolean(), outOfRangeFeatures: z.array(z.string()), bindingAudit: z.array(z.object({
      modelFeature: z.string(), standardField: z.string(), simulationParameter: z.string(), sourceUnit: z.string().nullable().optional(), targetUnit: z.string().nullable().optional(),
      sourceValue: z.number(), modelValue: z.number(), scale: z.number(), offset: z.number(),
    })), metrics: z.record(z.number()),
  })), unavailableTargets: z.array(z.string()), unavailableReasons: z.record(z.string()), disclaimer: z.string(),
});

export const simulationScenarioSchema = simulationPredictRequestSchema.omit({ useLlmAdvisor: true }).extend({
  scenarioId: z.string(),
  name: z.string(),
});

export const simulationLlmStatusSchema = z.object({
  enabled: z.boolean(),
  provider: z.string(),
  model: z.string(),
  baseUrl: z.string(),
  apiKeyConfigured: z.boolean(),
  envKeys: z.array(z.string()),
  mode: z.string(),
});

export const simulationRunStatusSchema = z.enum(["waiting", "running", "completed", "failed", "stopped"]);

export const simulationRunStageSchema = z.object({
  stageId: z.string(),
  stageKey: z.string(),
  stageName: z.string(),
  equipmentName: z.string(),
  status: simulationRunStatusSchema,
  progressPercent: z.number().min(0).max(100),
  waitingReason: z.string().nullable(),
  inputSummary: z.array(z.string()),
  modelBasis: z.array(z.string()),
  outputSummary: z.array(z.string()),
  startedAt: z.string().nullable(),
  completedAt: z.string().nullable(),
});

export const simulationRunEventSchema = z.object({
  eventId: z.string(),
  eventType: z.string(),
  stageId: z.string().nullable(),
  title: z.string(),
  detail: z.string(),
  createdAt: z.string(),
});

export const simulationTrialSnapshotSchema = z.object({
  snapshotId: z.string(),
  runId: z.string(),
  createdAt: z.string(),
  parameters: simulationPredictRequestSchema,
  predictions: simulationPredictionsSchema,
  confidence: confidenceLevelSchema,
  risks: z.array(z.string()),
  validationIndicators: z.array(z.string()),
  baselineDifferences: z.array(z.string()),
  researchUseOnly: z.boolean(),
  disclaimer: z.string(),
  predictionSource: z.enum(["rule_model", "promoted_model_composite"]).default("rule_model"),
  modelTargets: z.array(z.object({
    targetField: z.string(), prediction: z.number(),
    interval: z.object({ lower: z.number(), upper: z.number(), method: z.enum(["approximate95_rmse", "empirical_holdout_absolute_error"]), coverageClaim: z.enum(["not_calibrated", "empirical_holdout"]) }),
    modelVersion: z.string(), trialId: z.string(), bindingVersion: z.string(),
    datasetSnapshotId: z.string(), datasetFingerprint: z.string(), artifactFingerprint: z.string(),
    extrapolated: z.boolean(), outOfRangeFeatures: z.array(z.string()), bindingAudit: z.array(z.unknown()), metrics: z.record(z.number()),
  })).default([]),
  bindingVersions: z.array(z.string()).default([]),
  unavailableTargets: z.array(z.string()).default([]),
  extrapolated: z.boolean().default(false),
});

export const experimentSimulationRunSchema = z.object({
  runId: z.string(),
  parentRunId: z.string().nullable(),
  experimentId: z.string(),
  version: z.number().int().min(0),
  status: simulationRunStatusSchema,
  admissionAllowed: z.boolean(),
  admissionReasons: z.array(z.string()),
  reliabilityScore: z.number().min(0).max(1).nullable(),
  modelVersion: z.string(),
  bindingVersions: z.array(z.string()).default([]),
  modelType: z.string(),
  lineTemplateId: z.string(),
  modelMetrics: z.record(z.string()),
  progressPercent: z.number().min(0).max(100),
  simulatedMinutes: z.number().min(0),
  estimatedRemainingMinutes: z.number().min(0),
  currentStageId: z.string().nullable(),
  stages: z.array(simulationRunStageSchema).length(7),
  events: z.array(simulationRunEventSchema),
  officialParameters: simulationPredictRequestSchema,
  trialSnapshots: z.array(simulationTrialSnapshotSchema),
  officialResult: simulationTrialSnapshotSchema.nullable(),
  failureReason: z.string().nullable(),
  lastSuccessfulStageId: z.string().nullable(),
  affectedVersions: z.array(z.string()),
  createdAt: z.string(),
  updatedAt: z.string(),
  disclaimer: z.string(),
});

export const optimizationParametersSchema = z.object({
  temperatureC: z.number().min(20).max(55).multipleOf(0.1),
  ph: z.number().min(4.5).max(8.5).multipleOf(0.01),
  cultureHours: z.number().min(1).max(168).multipleOf(1),
  stirringRpm: z.number().min(0).max(600).multipleOf(1),
});
export const optimizationStatusSchema = z.enum(["waiting", "draft", "running", "needsReview", "completed", "failed", "stopped"]);
const optimizationModelEvidenceSchema = z.object({
  targetField: z.string(), prediction: z.number(), intervalLower: z.number(), intervalUpper: z.number(),
  intervalMethod: z.string(), modelVersion: z.string(), bindingVersion: z.string(),
  artifactFingerprint: z.string(), extrapolated: z.boolean(), outOfRangeFeatures: z.array(z.string()),
});

export const optimizationCandidatePlanSchema = z.object({
  planId: z.string(), strategyKey: z.enum(["balanced", "yieldPriority", "energySaving"]),
  displayName: z.string(), summary: z.string(), parameters: optimizationParametersSchema,
  scoreBreakdown: z.record(z.number()), confidenceScore: z.number().min(0).max(1),
  predictionIntervals: z.array(z.string()), riskItems: z.array(z.string()),
  validationItems: z.array(z.string()), explanation: z.array(z.string()),
  responseSurface: z.array(z.object({ temperatureC: z.number(), ph: z.number(), predictedScore: z.number().min(0).max(100), predictedValue: z.number().nullable().default(null) })).min(5),
  baselineImprovements: z.record(z.number()),
  modelEvidence: z.array(optimizationModelEvidenceSchema).default([]),
  objectiveScore: z.number().nullable().default(null), costIndex: z.number().nullable().default(null), searchRank: z.number().int().nullable().default(null),
});

export const optimizationStageSchema = z.object({
  stageId: z.string(), stageKey: z.string(), stageName: z.string(),
  status: optimizationStatusSchema, progressPercent: z.number().min(0).max(100),
  detail: z.string(), outputSummary: z.array(z.string()),
  startedAt: z.string().nullable(), completedAt: z.string().nullable(),
});

export const experimentOptimizationRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), version: z.number().int().min(0),
  status: optimizationStatusSchema, admissionAllowed: z.boolean(), admissionReasons: z.array(z.string()),
  baseModelVersion: z.string(), baseResultVersion: z.string(),
  baseSimulationRunId: z.string().nullable().default(null), baseBindingVersions: z.array(z.string()).default([]),
  searchMode: z.enum(["rule_demo", "promoted_model_constrained"]).default("rule_demo"), searchEvaluations: z.number().int().min(0).default(0),
  requirementDriven: z.boolean(), productRequirementVersionId: z.string().nullable(),
  productRequirementVersion: z.number().int().min(1).nullable(), productRequirementWorkingName: z.string().nullable(),
  productRequirementSourceRunId: z.string().nullable(), productRequirementContentHash: z.string().nullable(),
  candidatePlans: z.array(optimizationCandidatePlanSchema).max(3),
  selectedPlanId: z.string().nullable(), editedParameters: optimizationParametersSchema.nullable(),
  submittedParameters: optimizationParametersSchema.nullable(), trainingDataVersion: z.string().nullable(),
  retrainingStages: z.array(optimizationStageSchema).length(4), currentStageId: z.string().nullable(),
  progressPercent: z.number().min(0).max(100),
  trainingMetrics: z.array(z.object({ round: z.number().int().min(1), trainingLoss: z.number().min(0), validationScore: z.number().min(0).max(1), retained: z.boolean() })),
  searchMetrics: z.array(z.object({ strategyKey: z.string(), evaluatedCount: z.number().int().min(1), feasibleCount: z.number().int().min(1), bestObjective: z.number(), bestPrediction: z.number() })).default([]),
  submittedModelEvidence: z.array(optimizationModelEvidenceSchema).default([]), modelRetrained: z.boolean().default(false), officialParameterVersion: z.string().nullable().default(null),
  newModelVersion: z.string().nullable(), newResultVersion: z.string().nullable(),
  resultSummary: z.object({ confidenceScore: z.number().min(0).max(1), predictedOutcomes: z.array(z.string()), riskItems: z.array(z.string()), validationItems: z.array(z.string()), disclaimer: z.string() }).nullable(),
  humanDecisions: z.array(z.object({ decisionId: z.string(), decision: z.enum(["approved", "rejected"]), reason: z.string(), operator: z.string(), impactScope: z.array(z.string()), createdAt: z.string() })),
  events: z.array(z.object({ eventId: z.string(), eventType: z.string(), stageId: z.string().nullable(), title: z.string(), detail: z.string(), createdAt: z.string() })),
  createdAt: z.string(), updatedAt: z.string(), disclaimer: z.string(),
});

export const experimentalMeasurementSchema = z.object({
  measurementId: z.string(), metricName: z.string(), value: z.number(), unit: z.string(),
  replicate: z.number().int().min(1), measuredAt: z.string(), method: z.string(),
  sourceAssetId: z.string().nullable(), isModelTarget: z.boolean(),
});
export const retrainingEligibilityGateSchema = z.object({
  eligible: z.boolean(), checks: z.record(z.boolean()), reasons: z.array(z.string()),
  targetMetric: z.string(), targetReplicateCount: z.number().int().min(0),
  feedbackDatasetVersion: z.string().nullable(), checkedAt: z.string(),
});
export const experimentalValidationBatchSchema = z.object({
  validationBatchId: z.string(), experimentId: z.string(), optimizationRunId: z.string(),
  parameterVersion: z.string(), predictedResultVersion: z.string(), parentModelVersion: z.string(),
  parentSimulationRunId: z.string(), batchCode: z.string(), scale: z.enum(["lab", "pilot"]),
  status: z.enum(["draft", "needsReview", "confirmed", "rejected"]), plannedAt: z.string(),
  approvedParameters: optimizationParametersSchema, actualParameters: optimizationParametersSchema.nullable(),
  measurements: z.array(experimentalMeasurementSchema), contaminationObserved: z.boolean(),
  equipmentAbnormalities: z.array(z.string()), notes: z.string(),
  qualityGate: retrainingEligibilityGateSchema.nullable(), createdBy: z.string(), createdAt: z.string(),
  submittedAt: z.string().nullable(), reviewedBy: z.string().nullable(), reviewReason: z.string().nullable(),
  reviewedAt: z.string().nullable(), disclaimer: z.string(),
});

const feedbackRetrainingStageSchema = z.object({
  stageId: z.string(), stageKey: z.string(), stageName: z.string(),
  status: z.enum(["waiting", "running", "completed", "needsReview", "failed"]),
  progressPercent: z.number().int().min(0).max(100), detail: z.string(),
  outputSummary: z.array(z.string()), startedAt: z.string().nullable(), completedAt: z.string().nullable(),
});
const feedbackModelCandidateSchema = z.object({
  trialId: z.string(), algorithm: z.string(), modelType: z.string().nullable(),
  metrics: z.record(z.number()), deltaFromIncumbent: z.record(z.number()),
  artifactFingerprint: z.string(), artifactVerified: z.boolean(),
});
const feedbackPromotionGateSchema = z.object({
  eligible: z.boolean(), checks: z.record(z.boolean()), reasons: z.array(z.string()), checkedAt: z.string(),
});
export const feedbackRetrainingRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), commandId: z.string(), requestFingerprint: z.string(),
  status: z.enum(["running", "needsReview", "completed", "rejected", "failed"]),
  parentModelVersion: z.string(), feedbackDatasetVersions: z.array(z.string()).min(3),
  fixedBudgetSeconds: z.number().int().min(10), derivedDatasetId: z.string(), derivedDatasetFingerprint: z.string(),
  historicalRowCount: z.number().int().min(1), trainingFeedbackRowCount: z.number().int().min(0),
  externalHoldoutRowCount: z.number().int().min(3), researchCampaignId: z.string().nullable(),
  incumbentMetrics: z.record(z.number()), candidates: z.array(feedbackModelCandidateSchema),
  championTrialId: z.string().nullable(), promotionGate: feedbackPromotionGateSchema.nullable(),
  stages: z.array(feedbackRetrainingStageSchema).length(5), currentStageId: z.string().nullable(),
  progressPercent: z.number().int().min(0).max(100), promotedModelVersion: z.string().nullable(),
  evaluationReportId: z.string().nullable(), reviewedBy: z.string().nullable(), reviewReason: z.string().nullable(),
  reviewedAt: z.string().nullable(), events: z.array(z.object({ eventId: z.string(), eventType: z.string(), title: z.string(), detail: z.string(), createdAt: z.string() })),
  createdAt: z.string(), updatedAt: z.string(), disclaimer: z.string(),
});

const supplementaryExperimentCandidateSchema = z.object({
  candidateId: z.string(), strategyKey: z.enum(["coverageRecovery", "boundaryValidation", "residualCorrection"]),
  displayName: z.string(), summary: z.string(), modelFeatureValues: z.record(z.number()),
  processParameters: optimizationParametersSchema, exploratoryPrediction: z.number(),
  intervalLower: z.number(), intervalUpper: z.number(), intervalMethod: z.string(),
  informationGainScore: z.number().min(0).max(1), boundaryRiskScore: z.number().min(0).max(1),
  extrapolated: z.boolean(), addressesGaps: z.array(z.string()).min(1), evidence: z.array(z.string()).min(1),
  requiresHumanConfirmation: z.boolean(),
});
export const supplementaryExperimentDesignRunSchema = z.object({
  runId: z.string(), experimentId: z.string(), commandId: z.string(), requestFingerprint: z.string(),
  status: z.enum(["needsReview", "approved", "rejected"]), reportId: z.string(),
  reportInputFingerprint: z.string(), reliabilityScore: z.number().min(0).max(1), modelVersion: z.string(),
  modelArtifactFingerprint: z.string(), datasetFingerprint: z.string(), bindingVersion: z.string().nullable(),
  bindingSource: z.enum(["confirmed_binding", "standard_alias_fallback"]), admissionReasons: z.array(z.string()),
  candidates: z.array(supplementaryExperimentCandidateSchema).length(3), selectedCandidateIds: z.array(z.string()).max(3),
  planVersion: z.string().nullable(), reviewedBy: z.string().nullable(), reviewReason: z.string().nullable(),
  reviewedAt: z.string().nullable(), events: z.array(z.object({ eventId: z.string(), eventType: z.string(), title: z.string(), detail: z.string(), createdAt: z.string() })),
  createdAt: z.string(), updatedAt: z.string(), disclaimer: z.string(),
});

const supplementaryExecutionStepSchema = z.object({
  stepKey: z.enum(["preparation", "equipmentCheck", "parameterExecution", "sampling", "dataArchive", "humanConfirmation"]),
  order: z.number().int().min(1), title: z.string(), requirement: z.string(),
  status: z.enum(["pending", "inProgress", "completed"]), operator: z.string().nullable(),
  note: z.string().nullable(), startedAt: z.string().nullable(), completedAt: z.string().nullable(),
});
const supplementaryExecutionAssetSchema = z.object({
  assetId: z.string(), originalName: z.string(), contentHash: z.string(), parseStatus: z.string(),
  integrityVerified: z.boolean(), attachedBy: z.string(), attachedAt: z.string(), note: z.string(),
});
export const supplementaryExecutionBatchSchema = z.object({
  batchId: z.string(), experimentId: z.string(), commandId: z.string(), requestFingerprint: z.string(),
  designRunId: z.string(), planVersion: z.string(), candidateId: z.string(), strategyKey: z.string(),
  candidateName: z.string(), modelVersion: z.string(), reportId: z.string(), reportInputFingerprint: z.string(),
  batchCode: z.string(), scale: z.enum(["lab", "pilot"]),
  status: z.enum(["planned", "inProgress", "awaitingData", "needsReview", "completed", "cancelled"]),
  plannedAt: z.string(), replicateCount: z.number().int().min(3), samplingRequirements: z.array(z.string()).min(1),
  frozenParameters: optimizationParametersSchema, modelFeatureValues: z.record(z.number()),
  steps: z.array(supplementaryExecutionStepSchema).length(6), assets: z.array(supplementaryExecutionAssetSchema),
  createdBy: z.string(), createdAt: z.string(), startedAt: z.string().nullable(),
  reviewedBy: z.string().nullable(), reviewReason: z.string().nullable(), reviewedAt: z.string().nullable(),
  completedAt: z.string().nullable(),
  events: z.array(z.object({ eventId: z.string(), eventType: z.string(), title: z.string(), detail: z.string(), operator: z.string(), createdAt: z.string() })),
  disclaimer: z.string(),
});

const supplementaryMeasurementSchema = z.object({
  measurementId: z.string(), metricName: z.string(), value: z.number(), unit: z.string(),
  replicate: z.number().int().min(1), measuredAt: z.string(), method: z.string(),
  sourceAssetId: z.string(), isModelTarget: z.boolean(),
});
const supplementaryMeasurementQualityGateSchema = z.object({
  eligible: z.boolean(), checks: z.record(z.boolean()), reasons: z.array(z.string()),
  targetMetric: z.string(), targetReplicateCount: z.number().int().min(0),
  feedbackDatasetVersion: z.string().nullable(), checkedAt: z.string(),
});
export const supplementaryMeasurementBatchSchema = z.object({
  measurementBatchId: z.string(), experimentId: z.string(), commandId: z.string(), requestFingerprint: z.string(),
  executionBatchId: z.string(), planVersion: z.string(), candidateId: z.string(), executionBatchCode: z.string(),
  parentModelVersion: z.string(), reportId: z.string(), targetMetric: z.string(),
  status: z.enum(["draft", "needsReview", "confirmed", "rejected"]),
  frozenParameters: optimizationParametersSchema, actualParameters: optimizationParametersSchema.nullable(),
  allowedSourceAssetIds: z.array(z.string()).min(1), sourceAssetNames: z.record(z.string()),
  measurements: z.array(supplementaryMeasurementSchema), contaminationObserved: z.boolean(),
  equipmentAbnormalities: z.array(z.string()), notes: z.string(), qualityGate: supplementaryMeasurementQualityGateSchema.nullable(),
  createdBy: z.string(), createdAt: z.string(), submittedAt: z.string().nullable(),
  reviewedBy: z.string().nullable(), reviewReason: z.string().nullable(), reviewedAt: z.string().nullable(),
  events: z.array(z.object({ eventId: z.string(), eventType: z.string(), title: z.string(), detail: z.string(), operator: z.string(), createdAt: z.string() })),
  disclaimer: z.string(),
});

const lifecycleStatusSchema = z.enum(["waiting", "running", "needsReview", "completed", "failed", "notRequired"]);
const lifecycleStageKeySchema = z.enum(["dataAnalysis", "modelEvaluation", "supplementaryDesign", "supplementaryExecution", "measurementFeedback", "feedbackRetraining"]);
export const experimentLifecycleStageSchema = z.object({
  stageKey: lifecycleStageKeySchema, label: z.string(), status: lifecycleStatusSchema,
  progressPercent: z.number().int().min(0).max(100), route: z.string(), actionLabel: z.string(),
  canEnter: z.boolean(), summary: z.string(), waitingReasons: z.array(z.string()),
  evidenceRefs: z.array(z.string()), itemCounts: z.record(z.number().int()),
});
export const experimentLifecycleOverviewSchema = z.object({
  experimentId: z.string(), experimentName: z.string(), currentStageKey: lifecycleStageKeySchema.nullable(),
  currentStageLabel: z.string(), overallStatus: lifecycleStatusSchema,
  progressPercent: z.number().int().min(0).max(100),
  stages: z.array(experimentLifecycleStageSchema).length(6), generatedAt: z.string(), disclaimer: z.string(),
});
export const experimentLifecycleSummarySchema = z.object({
  experimentId: z.string(), currentStageKey: lifecycleStageKeySchema.nullable(), currentStageLabel: z.string(),
  overallStatus: lifecycleStatusSchema, progressPercent: z.number().int().min(0).max(100),
  nextAction: z.string(), route: z.string(), waitingReasons: z.array(z.string()), evidenceRefs: z.array(z.string()),
});
const humanActionTypeSchema = z.enum(["reviewReliability", "generateDesign", "reviewDesign", "createExecution", "continueExecution", "createMeasurement", "enterMeasurements", "reviewMeasurements", "createRetraining", "reviewRetraining"]);
export const humanActionItemSchema = z.object({
  actionId: z.string(), experimentId: z.string(), experimentName: z.string(),
  stageKey: lifecycleStageKeySchema, actionType: humanActionTypeSchema,
  priority: z.enum(["high", "medium", "normal"]), title: z.string(), detail: z.string(),
  route: z.string(), sourceRef: z.string(), blockedReasons: z.array(z.string()),
});
export const humanActionCenterSchema = z.object({
  totalCount: z.number().int().min(0), highPriorityCount: z.number().int().min(0),
  experimentCount: z.number().int().min(0), experimentActionCounts: z.record(z.number().int().min(0)),
  items: z.array(humanActionItemSchema), generatedAt: z.string(), disclaimer: z.string(),
});
const dataAnalysisStepKeySchema = z.enum(["dataIntake", "mappingReview", "cleaningAlignment", "datasetSnapshot", "featureEngineering", "modelingEvaluation"]);
export const dataAnalysisProgressStepSchema = z.object({
  stepKey: dataAnalysisStepKeySchema,
  sequence: z.number().int().min(1).max(6),
  label: z.string(),
  status: z.enum(["waiting", "running", "needsReview", "completed", "blocked"]),
  current: z.boolean(),
  summary: z.string(),
  actionLabel: z.string(),
  anchor: z.string(),
  evidenceRefs: z.array(z.string()),
  blockedReasons: z.array(z.string()),
});
export const dataAnalysisProgressSchema = z.object({
  experimentId: z.string(),
  experimentName: z.string(),
  sourceType: experimentSourceTypeSchema,
  progressPercent: z.number().int().min(0).max(100),
  currentStepKey: dataAnalysisStepKeySchema.nullable(),
  currentAction: z.string(),
  steps: z.array(dataAnalysisProgressStepSchema).length(6),
  disclaimer: z.string(),
});
export const demoModelAdmissionSchema = z.object({
  admissionId: z.string(), experimentId: z.string(), status: z.literal("active"),
  scope: z.literal("isolated_sample_demo"), demoModelVersion: z.string(),
  campaignId: z.string(), trialId: z.string(), datasetSnapshotId: z.string(),
  datasetFingerprint: z.string(), artifactFingerprint: z.string(), artifactVerified: z.boolean(),
  modelType: z.string(), featureNames: z.array(z.string()), targetField: z.string(),
  metrics: z.record(z.number()), scoreBreakdown: z.record(z.number()), reliabilityScore: z.number().min(0).max(1),
  operator: z.string(), reason: z.string(), createdAt: z.string(),
  restrictions: z.array(z.string()), limitations: z.array(z.string()), disclaimer: z.string(),
});

export const agentTaskStatusSchema = z.enum(["waiting", "running", "interrupted", "needsReview", "completed", "failed", "stopped"]);
export const agentTaskProjectionSchema = z.object({
  taskId: z.string(), agentKey: z.enum(["productInnovation", "dataAnalysis", "simulation", "optimization"]),
  agentName: z.string(), agentKind: z.enum(["business", "workflow", "tool"]), status: agentTaskStatusSchema,
  progressPercent: z.number().int().min(0).max(100), route: z.string(), dependsOn: z.array(z.string()),
  blockedReasons: z.array(z.string()), runId: z.string().nullable(), version: z.number().int().nullable(),
  summary: z.string(), sourceRefs: z.array(z.string()), canGuide: z.boolean(), canRetry: z.boolean(),
});
export const agentTaskCenterSchema = z.object({
  experimentId: z.string(), overallStatus: agentTaskStatusSchema, progressPercent: z.number().int().min(0).max(100),
  activeTaskIds: z.array(z.string()), tasks: z.array(agentTaskProjectionSchema).length(4), generatedAt: z.string(),
  disclaimer: z.literal("研发实验建议"),
});
export const researchReportStatementSchema = z.object({
  statementId: z.string(), kind: z.enum(["fact", "prediction", "recommendation", "limitation"]),
  title: z.string(), text: z.string(), evidenceRefs: z.array(z.string()).min(1),
});
export const researchReportSectionSchema = z.object({
  sectionKey: z.string(), title: z.string(), statements: z.array(researchReportStatementSchema),
});
export const researchReportSchema = z.object({
  reportId: z.string(), experimentId: z.string(), reportVersion: z.number().int().min(1), commandId: z.string(),
  title: z.string(), status: z.enum(["draft", "reviewed"]), inputFingerprint: z.string(), sourceVersions: z.record(z.string()),
  sections: z.array(researchReportSectionSchema), unresolvedItems: z.array(z.string()), generatedBy: z.string(), generatedAt: z.string(),
  reviewedBy: z.string().nullable().default(null), reviewReason: z.string().nullable().default(null), reviewedAt: z.string().nullable().default(null),
  approvedKnowledgeStatementIds: z.array(z.string()).default([]), disclaimer: z.string(),
});
export type AkkProduct = z.infer<typeof akkProductSchema>;
export type FormulaGenerationRequest = z.infer<typeof formulaGenerationRequestSchema>;
export type FormulaResult = z.infer<typeof formulaResultSchema>;
export type KnowledgeItem = z.infer<typeof knowledgeItemSchema>;
export type KnowledgeChunk = z.infer<typeof knowledgeChunkSchema>;
export type LlmStatus = z.infer<typeof llmStatusSchema>;
export type ExperimentRecord = z.infer<typeof experimentRecordSchema>;
export type ExperimentStageName = z.infer<typeof experimentStageNameSchema>;
export type ExperimentStageStatus = z.infer<typeof experimentStageStatusSchema>;
export type ExperimentStageSummary = z.infer<typeof experimentStageSummarySchema>;
export type ExperimentArchiveItem = z.infer<typeof experimentArchiveItemSchema>;
export type ExperimentArchiveResponse = z.infer<typeof experimentArchiveResponseSchema>;
export type ExperimentReliabilityMetric = z.infer<typeof experimentReliabilityMetricSchema>;
export type ExperimentWorkspaceOverview = z.infer<typeof experimentWorkspaceOverviewSchema>;
export type ExperimentCreateRequest = z.infer<typeof experimentCreateRequestSchema>;
export type SampleExperimentCreate = z.infer<typeof sampleExperimentCreateSchema>;
export type SampleExperimentResult = z.infer<typeof sampleExperimentResultSchema>;
export type ExperimentFileAuditEvent = z.infer<typeof experimentFileAuditEventSchema>;
export type ExperimentFileAuditStageSummary = z.infer<typeof experimentFileAuditStageSummarySchema>;
export type ExperimentFileAuditSummary = z.infer<typeof experimentFileAuditSummarySchema>;
export type ExperimentTextFileUploadRequest = z.infer<typeof experimentTextFileUploadRequestSchema>;
export type ExperimentFileAsset = z.infer<typeof experimentFileAssetSchema>;
export type ExperimentAssetIntegrityResult = z.infer<typeof experimentAssetIntegrityResultSchema>;
export type ExperimentFileDeleteResult = z.infer<typeof experimentFileDeleteResultSchema>;
export type DataCollectionLocalizationRun = z.infer<typeof dataCollectionLocalizationRunSchema>;
export type CleaningAlignmentConfig = z.infer<typeof cleaningAlignmentConfigSchema>;
export type CleaningAlignmentRun = z.infer<typeof cleaningAlignmentRunSchema>;
export type FeatureEngineeringConfig = z.infer<typeof featureEngineeringConfigSchema>;
export type FeatureEngineeringRun = z.infer<typeof featureEngineeringRunSchema>;
export type ExperimentFieldMappingSuggestion = z.infer<typeof experimentFieldMappingSuggestionSchema>;
export type ExperimentAssetFieldMappingSuggestions = z.infer<typeof experimentAssetFieldMappingSuggestionsSchema>;
export type ExperimentFieldMappingSuggestionResponse = z.infer<typeof experimentFieldMappingSuggestionResponseSchema>;
export type SchemaRecognitionCandidate = z.infer<typeof schemaRecognitionCandidateSchema>;
export type SchemaRecognitionRun = z.infer<typeof schemaRecognitionRunSchema>;
export type ProductInnovationInput = z.infer<typeof productInnovationInputSchema>;
export type ProductInnovationRun = z.infer<typeof productInnovationRunSchema>;
export type ProductRequirementVersion = z.infer<typeof productRequirementVersionSchema>;
export type ExperimentConfirmedFieldMapping = z.infer<typeof experimentConfirmedFieldMappingSchema>;
export type ExperimentConfirmFieldMappingsRequest = z.infer<typeof experimentConfirmFieldMappingsRequestSchema>;
export type ExperimentConfirmedFieldMappingSet = z.infer<typeof experimentConfirmedFieldMappingSetSchema>;
export type ExperimentFieldDictionaryEntry = z.infer<typeof experimentFieldDictionaryEntrySchema>;
export type ExperimentFieldDictionaryUpsertRequest = z.infer<typeof experimentFieldDictionaryUpsertRequestSchema>;
export type ExperimentFieldDictionary = z.infer<typeof experimentFieldDictionarySchema>;
export type ExperimentCleaningQualitySummary = z.infer<typeof experimentCleaningQualitySummarySchema>;
export type ExperimentAssetCleaningPreview = z.infer<typeof experimentAssetCleaningPreviewSchema>;
export type ExperimentCleaningPreviewResponse = z.infer<typeof experimentCleaningPreviewResponseSchema>;
export type ExperimentAlignmentAssetSummary = z.infer<typeof experimentAlignmentAssetSummarySchema>;
export type ExperimentAlignmentPreviewResponse = z.infer<typeof experimentAlignmentPreviewResponseSchema>;
export type ExperimentFeatureSummary = z.infer<typeof experimentFeatureSummarySchema>;
export type ExperimentFeatureAnomalyHint = z.infer<typeof experimentFeatureAnomalyHintSchema>;
export type ExperimentFeaturePreviewResponse = z.infer<typeof experimentFeaturePreviewResponseSchema>;
export type ExperimentDatasetSnapshot = z.infer<typeof experimentDatasetSnapshotSchema>;
export type ExperimentModelingPlanPreview = z.infer<typeof experimentModelingPlanPreviewSchema>;
export type ExperimentTrainingAgentStage = z.infer<typeof experimentTrainingAgentStageSchema>;
export type ExperimentTrainingTaskPreview = z.infer<typeof experimentTrainingTaskPreviewSchema>;
export type ExperimentTrainingResultMetrics = z.infer<typeof experimentTrainingResultMetricsSchema>;
export type ExperimentTrainingResultSummary = z.infer<typeof experimentTrainingResultSummarySchema>;
export type ResultInterpretationRun = z.infer<typeof resultInterpretationRunSchema>;
export type ExperimentResearchBriefSummary = z.infer<typeof experimentResearchBriefSummarySchema>;
export type ExperimentSimulationRange = z.infer<typeof experimentSimulationRangeSchema>;
export type ExperimentSimulationCandidatePlan = z.infer<typeof experimentSimulationCandidatePlanSchema>;
export type ExperimentSimulationInputSummary = z.infer<typeof experimentSimulationInputSummarySchema>;
export type AgentRunStatus = z.infer<typeof agentRunStatusSchema>;
export type AgentRunNode = z.infer<typeof agentRunNodeSchema>;
export type AgentRunEvent = z.infer<typeof agentRunEventSchema>;
export type AgentGuidancePreview = z.infer<typeof agentGuidancePreviewSchema>;
export type HumanDecision = z.infer<typeof humanDecisionSchema>;
export type ExperimentAgentRun = z.infer<typeof experimentAgentRunSchema>;
export type AgentRuntimeStatus = z.infer<typeof agentRuntimeStatusSchema>;
export type AgentCommandTask = z.infer<typeof agentCommandTaskSchema>;
export type AgentCommandSummary = z.infer<typeof agentCommandSummarySchema>;
export type AgentQueueStatus = z.infer<typeof agentQueueStatusSchema>;
export type AgentManifest = z.infer<typeof agentManifestSchema>;
export type AgentCatalogSnapshot = z.infer<typeof agentCatalogSnapshotSchema>;
export type ResearchTrial = z.infer<typeof researchTrialSchema>;
export type ResearchCampaign = z.infer<typeof researchCampaignSchema>;
export type ModelEvaluationReport = z.infer<typeof modelEvaluationReportSchema>;
export type ProcessProductionLine = z.infer<typeof processProductionLineSchema>;
export type ProcessTaskRequest = z.infer<typeof processTaskRequestSchema>;
export type GeneratedProcessTask = z.infer<typeof generatedProcessTaskSchema>;
export type ProcessCandidatePlan = z.infer<typeof processCandidatePlanSchema>;
export type ProcessSurface = z.infer<typeof processSurfaceSchema>;
export type ProcessFeedbackRequest = z.infer<typeof processFeedbackRequestSchema>;
export type ProcessFeedback = z.infer<typeof processFeedbackSchema>;
export type SimulationPredictRequest = z.infer<typeof simulationPredictRequestSchema>;
export type SimulationPredictResponse = z.infer<typeof simulationPredictResponseSchema>;
export type PromotedModelPrediction = z.infer<typeof promotedModelPredictionSchema>;
export type PromotedModelRecord = z.infer<typeof promotedModelRecordSchema>;
export type DeviceAdapterPackSelector = z.infer<typeof deviceAdapterPackSelectorSchema>;
export type DeviceAdapterPackReference = z.infer<typeof deviceAdapterPackReferenceSchema>;
export type DeviceAdapterPack = z.infer<typeof deviceAdapterPackSchema>;
export type DeviceAdapterPackCreate = z.infer<typeof deviceAdapterPackCreateSchema>;
export type DeviceAdapterPackComparison = z.infer<typeof deviceAdapterPackComparisonSchema>;
export type FeatureBindingSuggestionCandidate = z.infer<typeof featureBindingSuggestionCandidateSchema>;
export type FeatureBindingSuggestionRun = z.infer<typeof featureBindingSuggestionRunSchema>;
export type FeatureBindingVersion = z.infer<typeof featureBindingVersionSchema>;
export type ModelAssetSummary = z.infer<typeof modelAssetSummarySchema>;
export type ModelAssetDetail = z.infer<typeof modelAssetDetailSchema>;
export type CompositeModelPrediction = z.infer<typeof compositeModelPredictionSchema>;
export type SimulationScenario = z.infer<typeof simulationScenarioSchema>;
export type SimulationLlmStatus = z.infer<typeof simulationLlmStatusSchema>;
export type SimulationRunStatus = z.infer<typeof simulationRunStatusSchema>;
export type SimulationRunStage = z.infer<typeof simulationRunStageSchema>;
export type SimulationRunEvent = z.infer<typeof simulationRunEventSchema>;
export type SimulationTrialSnapshot = z.infer<typeof simulationTrialSnapshotSchema>;
export type ExperimentSimulationRun = z.infer<typeof experimentSimulationRunSchema>;
export type OptimizationParameters = z.infer<typeof optimizationParametersSchema>;
export type OptimizationCandidatePlan = z.infer<typeof optimizationCandidatePlanSchema>;
export type ExperimentOptimizationRun = z.infer<typeof experimentOptimizationRunSchema>;
export type ExperimentalValidationBatch = z.infer<typeof experimentalValidationBatchSchema>;
export type FeedbackRetrainingRun = z.infer<typeof feedbackRetrainingRunSchema>;
export type SupplementaryExperimentDesignRun = z.infer<typeof supplementaryExperimentDesignRunSchema>;
export type SupplementaryExecutionBatch = z.infer<typeof supplementaryExecutionBatchSchema>;
export type SupplementaryMeasurementBatch = z.infer<typeof supplementaryMeasurementBatchSchema>;
export type ExperimentLifecycleStage = z.infer<typeof experimentLifecycleStageSchema>;
export type ExperimentLifecycleOverview = z.infer<typeof experimentLifecycleOverviewSchema>;
export type ExperimentLifecycleSummary = z.infer<typeof experimentLifecycleSummarySchema>;
export type HumanActionItem = z.infer<typeof humanActionItemSchema>;
export type HumanActionCenter = z.infer<typeof humanActionCenterSchema>;
export type DataAnalysisProgressStep = z.infer<typeof dataAnalysisProgressStepSchema>;
export type DataAnalysisProgress = z.infer<typeof dataAnalysisProgressSchema>;
export type DemoModelAdmission = z.infer<typeof demoModelAdmissionSchema>;
export type AgentTaskProjection = z.infer<typeof agentTaskProjectionSchema>;
export type AgentTaskCenter = z.infer<typeof agentTaskCenterSchema>;
export type ResearchReport = z.infer<typeof researchReportSchema>;
export type EnterpriseKnowledgeEntry = z.infer<typeof enterpriseKnowledgeEntrySchema>;
export type EnterpriseKnowledgeUsage = z.infer<typeof enterpriseKnowledgeUsageSchema>;
