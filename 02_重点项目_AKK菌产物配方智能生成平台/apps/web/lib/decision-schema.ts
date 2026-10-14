import { z } from "zod";

export const requirementAttributeSchema = z.object({
  metric: z.string(),
  direction: z.enum(["maximize", "minimize", "target", "range"]),
  threshold: z.number().nullable().optional(),
  upperThreshold: z.number().nullable().optional(),
  unit: z.string().nullable().optional(),
  measurementMethod: z.string().nullable().optional(),
  sourceText: z.string().nullable().optional(),
});

export const decisionRequirementSchema = z.object({
  productType: z.string(),
  attributes: z.array(requirementAttributeSchema),
  missingConstraints: z.array(z.string()),
  confidence: z.number().nullable().optional(),
});

const modelLineageSchema = z.object({
  modelVersion: z.string(),
  modelCategory: z.string(),
  targetField: z.string(),
  targetUnit: z.string().nullable().optional(),
  datasetSnapshotId: z.string(),
  datasetFingerprint: z.string(),
  dataManifestUri: z.string().nullable().optional(),
  artifactFingerprint: z.string(),
  featureRanges: z.record(
    z.object({ min: z.number(), max: z.number() }),
  ),
  metrics: z.record(z.number()),
});

const predictionSchema = z.object({
  targetField: z.string(),
  value: z.number(),
  uncertainty: z.number().nullable().optional(),
  lineage: modelLineageSchema,
});

export const decisionPlanSchema = z.object({
  planId: z.string(),
  objective: z.enum([
    "maximize_output",
    "balanced",
    "minimize_resource",
  ]),
  parameters: z.record(z.number()),
  predictions: z.record(predictionSchema),
  objectiveScore: z.number(),
  scoreBreakdown: z.record(z.number()),
  constraintsPassed: z.boolean(),
});

export const decisionTraceSchema = z.object({
  runId: z.string(),
  tenantId: z.string(),
  userId: z.string(),
  rawRequirement: z.string(),
  requirement: decisionRequirementSchema,
  supplementalConstraints: z.record(z.unknown()),
  knowledgeVersion: z.string(),
  knowledgeIds: z.array(z.string()),
  dataVersions: z.array(z.string()),
  modelVersions: z.record(z.string()),
  search: z.record(z.unknown()),
  plans: z.array(decisionPlanSchema),
  risks: z.array(z.string()),
  applicability: z.array(z.string()),
  generatedAt: z.string(),
  confirmationStatus: z.enum(["pending", "confirmed"]),
  confirmation: z
    .object({
      planId: z.string(),
      approverUserId: z.string(),
      approverName: z.string(),
      tenantId: z.string(),
      note: z.string().nullable().optional(),
      confirmedAt: z.string(),
    })
    .nullable()
    .optional(),
});

export type DecisionRequirement = z.infer<typeof decisionRequirementSchema>;
export type DecisionTrace = z.infer<typeof decisionTraceSchema>;
export type DecisionPlan = z.infer<typeof decisionPlanSchema>;
