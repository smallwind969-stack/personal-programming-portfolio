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

export type AkkProduct = z.infer<typeof akkProductSchema>;
export type FormulaGenerationRequest = z.infer<typeof formulaGenerationRequestSchema>;
export type FormulaResult = z.infer<typeof formulaResultSchema>;
export type KnowledgeItem = z.infer<typeof knowledgeItemSchema>;
export type KnowledgeChunk = z.infer<typeof knowledgeChunkSchema>;
export type LlmStatus = z.infer<typeof llmStatusSchema>;
export type ExperimentRecord = z.infer<typeof experimentRecordSchema>;
