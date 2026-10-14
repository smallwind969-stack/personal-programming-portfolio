import {
  AkkProduct,
  FormulaGenerationRequest,
  FormulaResult,
  ExperimentArchiveResponse,
  ExperimentRecord,
  ExperimentWorkspaceOverview,
  ExperimentCreateRequest,
  SampleExperimentCreate,
  SampleExperimentResult,
  ExperimentAlignmentPreviewResponse,
  ExperimentCleaningPreviewResponse,
  ExperimentFileAuditSummary,
  ExperimentFileAsset,
  ExperimentAssetIntegrityResult,
  ExperimentFileDeleteResult,
  DataCollectionLocalizationRun,
  CleaningAlignmentConfig,
  CleaningAlignmentRun,
  FeatureEngineeringConfig,
  FeatureEngineeringRun,
  ExperimentConfirmFieldMappingsRequest,
  ExperimentConfirmedFieldMappingSet,
  ExperimentDatasetSnapshot,
  ExperimentModelingPlanPreview,
  ExperimentResearchBriefSummary,
  ExperimentSimulationInputSummary,
  ExperimentTrainingResultSummary,
  ResultInterpretationRun,
  ExperimentTrainingTaskPreview,
  ExperimentAgentRun,
  AgentRuntimeStatus,
  AgentCommandTask,
  AgentCommandSummary,
  AgentQueueStatus,
  AgentCatalogSnapshot,
  ResearchCampaign,
  ModelEvaluationReport,
  AgentGuidancePreview,
  ExperimentFieldDictionary,
  ExperimentFieldDictionaryUpsertRequest,
  ExperimentFeaturePreviewResponse,
  ExperimentFieldMappingSuggestionResponse,
  ExperimentTextFileUploadRequest,
  SchemaRecognitionRun,
  ProductInnovationInput,
  ProductInnovationRun,
  ProductRequirementVersion,
  GeneratedProcessTask,
  KnowledgeChunk,
  KnowledgeItem,
  EnterpriseKnowledgeEntry,
  EnterpriseKnowledgeUsage,
  LlmStatus,
  ProcessFeedback,
  ProcessFeedbackRequest,
  ProcessProductionLine,
  ProcessTaskRequest,
  SimulationLlmStatus,
  SimulationPredictRequest,
  SimulationPredictResponse,
  SimulationScenario,
  PromotedModelPrediction,
  PromotedModelRecord,
  ModelAssetSummary,
  ModelAssetDetail,
  DeviceAdapterPack,
  DeviceAdapterPackCreate,
  DeviceAdapterPackComparison,
  DeviceAdapterPackSelector,
  FeatureBindingSuggestionRun,
  FeatureBindingVersion,
  CompositeModelPrediction,
  ExperimentSimulationRun,
  SimulationTrialSnapshot,
  ExperimentOptimizationRun,
  ExperimentalValidationBatch,
  FeedbackRetrainingRun,
  SupplementaryExperimentDesignRun,
  SupplementaryExecutionBatch,
  SupplementaryMeasurementBatch,
  ExperimentLifecycleOverview,
  ExperimentLifecycleSummary,
  HumanActionCenter,
  DataAnalysisProgress,
  DemoModelAdmission,
  OptimizationParameters,
  AgentTaskCenter,
  ResearchReport,
  akkProductSchema,
  experimentArchiveResponseSchema,
  experimentAlignmentPreviewResponseSchema,
  experimentCleaningPreviewResponseSchema,
  experimentFileAssetSchema,
  sampleExperimentResultSchema,
  experimentAssetIntegrityResultSchema,
  experimentFileDeleteResultSchema,
  dataCollectionLocalizationRunSchema,
  cleaningAlignmentRunSchema,
  featureEngineeringRunSchema,
  experimentFileAuditSummarySchema,
  experimentConfirmedFieldMappingSetSchema,
  experimentDatasetSnapshotSchema,
  experimentModelingPlanPreviewSchema,
  experimentResearchBriefSummarySchema,
  experimentSimulationInputSummarySchema,
  experimentTrainingResultSummarySchema,
  resultInterpretationRunSchema,
  experimentTrainingTaskPreviewSchema,
  experimentAgentRunSchema,
  agentRuntimeStatusSchema,
  agentCommandTaskSchema,
  agentCommandSummarySchema,
  agentQueueStatusSchema,
  agentCatalogSnapshotSchema,
  researchCampaignSchema,
  modelEvaluationReportSchema,
  agentGuidancePreviewSchema,
  experimentFieldDictionarySchema,
  experimentFeaturePreviewResponseSchema,
  experimentFieldMappingSuggestionResponseSchema,
  experimentRecordSchema,
  experimentWorkspaceOverviewSchema,
  schemaRecognitionRunSchema,
  productInnovationRunSchema,
  productRequirementVersionSchema,
  formulaResultSchema,
  generatedProcessTaskSchema,
  knowledgeChunkSchema,
  knowledgeItemSchema,
  llmStatusSchema,
  processFeedbackSchema,
  processProductionLineSchema,
  simulationLlmStatusSchema,
  simulationPredictResponseSchema,
  simulationScenarioSchema,
  promotedModelPredictionSchema,
  promotedModelRecordSchema,
  modelAssetSummarySchema,
  modelAssetDetailSchema,
  deviceAdapterPackSchema,
  deviceAdapterPackComparisonSchema,
  featureBindingSuggestionRunSchema,
  featureBindingVersionSchema,
  compositeModelPredictionSchema,
  experimentSimulationRunSchema,
  simulationTrialSnapshotSchema,
  experimentOptimizationRunSchema,
  experimentalValidationBatchSchema,
  feedbackRetrainingRunSchema,
  supplementaryExperimentDesignRunSchema,
  supplementaryExecutionBatchSchema,
  supplementaryMeasurementBatchSchema,
  experimentLifecycleOverviewSchema,
  experimentLifecycleSummarySchema,
  humanActionCenterSchema,
  dataAnalysisProgressSchema,
  demoModelAdmissionSchema,
  agentTaskCenterSchema,
  researchReportSchema,
  enterpriseKnowledgeEntrySchema,
  enterpriseKnowledgeUsageSchema,
} from "@/lib/schemas";

function getBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.SERVER_API_BASE_URL ?? "http://127.0.0.1:8000";
  }
  return "/api";
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const errorBody = await response.json() as { detail?: unknown };
      if (typeof errorBody.detail === "string") detail = errorBody.detail;
    } catch {
      // Keep the HTTP fallback when the response is not JSON.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function getAkkProducts(): Promise<AkkProduct[]> {
  const data = await requestJson<unknown[]>("/akk-products");
  return data.map((item) => akkProductSchema.parse(item));
}

export async function getAkkProduct(productId: string): Promise<AkkProduct> {
  const data = await requestJson<unknown>(`/akk-products/${productId}`);
  return akkProductSchema.parse(data);
}

export async function generateFormula(
  payload: FormulaGenerationRequest,
): Promise<FormulaResult> {
  const data = await requestJson<unknown>("/formula/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return formulaResultSchema.parse(data);
}

export async function getFormulaResult(resultId: string): Promise<FormulaResult> {
  const data = await requestJson<unknown>(`/formula-results/${resultId}`);
  return formulaResultSchema.parse(data);
}

export async function getFormulaResults(): Promise<FormulaResult[]> {
  const data = await requestJson<unknown[]>("/formula-results");
  return data.map((item) => formulaResultSchema.parse(item));
}

export async function getKnowledgeItems(query?: string): Promise<KnowledgeItem[]> {
  const qs = query ? `?query=${encodeURIComponent(query)}` : "";
  const data = await requestJson<unknown[]>(`/knowledge${qs}`);
  return data.map((item) => knowledgeItemSchema.parse(item));
}

export async function getKnowledgeChunks(query?: string): Promise<KnowledgeChunk[]> {
  const qs = query ? `?query=${encodeURIComponent(query)}&limit=8` : "?limit=8";
  const data = await requestJson<unknown[]>(`/knowledge/chunks${qs}`);
  return data.map((item) => knowledgeChunkSchema.parse(item));
}

export async function getLlmStatus(): Promise<LlmStatus> {
  const data = await requestJson<unknown>("/llm/status");
  return llmStatusSchema.parse(data);
}

export async function getExperimentRecords(resultId?: string): Promise<ExperimentRecord[]> {
  const query = resultId ? `?result_id=${encodeURIComponent(resultId)}` : "";
  const data = await requestJson<unknown[]>(`/experiments${query}`);
  return data.map((item) => experimentRecordSchema.parse(item));
}

export async function getExperimentArchive(): Promise<ExperimentArchiveResponse> {
  const data = await requestJson<unknown>("/experiments/archive");
  return experimentArchiveResponseSchema.parse(data);
}

export async function getExperimentWorkspaceOverview(
  experimentId: string,
): Promise<ExperimentWorkspaceOverview> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/overview`,
  );
  return experimentWorkspaceOverviewSchema.parse(data);
}

export async function getDataAnalysisProgress(
  experimentId: string,
): Promise<DataAnalysisProgress> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/analysis-progress`,
  );
  return dataAnalysisProgressSchema.parse(data);
}

export async function createExperimentWorkspace(
  payload: ExperimentCreateRequest,
): Promise<ExperimentWorkspaceOverview> {
  const data = await requestJson<unknown>("/experiments/workspaces", {
    method: "POST", body: JSON.stringify(payload),
  });
  return experimentWorkspaceOverviewSchema.parse(data);
}

export async function createSampleExperimentWorkspace(
  payload: SampleExperimentCreate = { templateKey: "algae-culture" },
): Promise<SampleExperimentResult> {
  const data = await requestJson<unknown>("/experiments/sample-workspaces", {
    method: "POST", body: JSON.stringify(payload),
  });
  return sampleExperimentResultSchema.parse(data);
}

export async function getLatestExperimentSimulationRun(experimentId: string): Promise<ExperimentSimulationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/simulation-runs/latest`);
  return experimentSimulationRunSchema.parse(data);
}

export async function createExperimentSimulationRun(experimentId: string): Promise<ExperimentSimulationRun> {
  await runDomainAgentCommand(experimentId, "simulation", "new", "simulationCreate");
  return getLatestExperimentSimulationRun(experimentId);
}

export async function advanceExperimentSimulationRun(experimentId: string, runId: string): Promise<ExperimentSimulationRun> {
  await runDomainAgentCommand(experimentId, "simulation", runId, "simulationAdvance");
  return getLatestExperimentSimulationRun(experimentId);
}

export async function stopExperimentSimulationRun(experimentId: string, runId: string): Promise<ExperimentSimulationRun> {
  await runDomainAgentCommand(experimentId, "simulation", runId, "simulationStop");
  return getLatestExperimentSimulationRun(experimentId);
}

export async function restartExperimentSimulationRun(experimentId: string, runId: string): Promise<ExperimentSimulationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/simulation-runs/${encodeURIComponent(runId)}/restart`, { method: "POST" });
  return experimentSimulationRunSchema.parse(data);
}

export async function createExperimentSimulationTrial(experimentId: string, runId: string, payload: SimulationPredictRequest): Promise<SimulationTrialSnapshot> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/simulation-runs/${encodeURIComponent(runId)}/trial`, { method: "POST", body: JSON.stringify(payload) });
  return simulationTrialSnapshotSchema.parse(data);
}

export async function failExperimentSimulationRun(experimentId: string, runId: string, reason: string, affectedVersions: string[]): Promise<ExperimentSimulationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/simulation-runs/${encodeURIComponent(runId)}/fail`, { method: "POST", body: JSON.stringify({ reason, affectedVersions }) });
  return experimentSimulationRunSchema.parse(data);
}

export async function retryExperimentSimulationRun(experimentId: string, runId: string): Promise<ExperimentSimulationRun> {
  await runDomainAgentCommand(experimentId, "simulation", runId, "simulationRetry");
  return getLatestExperimentSimulationRun(experimentId);
}

export async function getLatestExperimentAgentRun(experimentId: string): Promise<ExperimentAgentRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/latest`);
  return experimentAgentRunSchema.parse(data);
}

export async function getAgentRuntimeStatus(): Promise<AgentRuntimeStatus> {
  const data = await requestJson<unknown>("/agent-runtime/status");
  return agentRuntimeStatusSchema.parse(data);
}

export async function advanceExperimentAgentRun(experimentId: string, runId: string, expectedRevision: number): Promise<ExperimentAgentRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/${encodeURIComponent(runId)}/advance`, { method: "POST", body: JSON.stringify({ expectedRevision, commandId: crypto.randomUUID() }) });
  return experimentAgentRunSchema.parse(data);
}

export async function enqueueExperimentAgentCommand(experimentId: string, runId: string, action: "advance" | "stop", expectedRevision: number): Promise<AgentCommandTask> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/${encodeURIComponent(runId)}/commands`, {
    method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), action, expectedRevision, payload: {}, maxAttempts: 3 }),
  });
  return agentCommandTaskSchema.parse(data);
}

export async function getAgentCommand(taskId: string): Promise<AgentCommandTask> {
  const data = await requestJson<unknown>(`/agent-runtime/commands/${encodeURIComponent(taskId)}`);
  return agentCommandTaskSchema.parse(data);
}

export async function getRecentAgentCommands(limit = 50, experimentId?: string): Promise<AgentCommandSummary[]> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (experimentId) query.set("experimentId", experimentId);
  const data = await requestJson<unknown[]>(`/agent-runtime/commands?${query.toString()}`);
  return data.map((item) => agentCommandSummarySchema.parse(item));
}

export async function getAgentQueueStatus(): Promise<AgentQueueStatus> {
  const data = await requestJson<unknown>("/agent-runtime/queue/status");
  return agentQueueStatusSchema.parse(data);
}

export async function getAgentCatalog(): Promise<AgentCatalogSnapshot> {
  const data = await requestJson<unknown>("/agent-runtime/catalog");
  return agentCatalogSnapshotSchema.parse(data);
}

export async function listResearchCampaigns(experimentId: string): Promise<ResearchCampaign[]> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-campaigns`);
  return researchCampaignSchema.array().parse(data);
}

export async function getResearchCampaign(experimentId: string, campaignId: string): Promise<ResearchCampaign> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-campaigns/${encodeURIComponent(campaignId)}`);
  return researchCampaignSchema.parse(data);
}

export async function createResearchCampaign(experimentId: string, datasetSnapshotId: string, baselineMetrics: { mae: number; rmse: number; r2: number }): Promise<ResearchCampaign> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-campaigns`, { method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), datasetSnapshotId, agentKey: "modeling", baselineMetrics, fixedBudgetSeconds: 300 }) });
  return researchCampaignSchema.parse(data);
}

export async function enqueueResearchTrial(experimentId: string, campaignId: string, hypothesis: string, parameterPatch: Record<string, unknown>): Promise<AgentCommandTask> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-campaigns/${encodeURIComponent(campaignId)}/trials`, { method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), hypothesis, parameterPatch, priority: 3 }) });
  return agentCommandTaskSchema.parse(data);
}

export async function enqueueNextResearchIteration(experimentId: string, campaignId: string): Promise<AgentCommandTask> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-campaigns/${encodeURIComponent(campaignId)}/iterate`, { method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), priority: 4 }) });
  return agentCommandTaskSchema.parse(data);
}

export async function promoteResearchTrial(experimentId: string, campaignId: string, trialId: string, operator: string, reason: string): Promise<ResearchCampaign> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-campaigns/${encodeURIComponent(campaignId)}/promotion`, { method: "POST", body: JSON.stringify({ trialId, decision: "approved", operator, reason }) });
  return researchCampaignSchema.parse(data);
}

export async function getDemoModelAdmission(experimentId: string): Promise<DemoModelAdmission | null> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/demo-model-admission`);
  return data === null ? null : demoModelAdmissionSchema.parse(data);
}

export async function createDemoModelAdmission(
  experimentId: string, campaignId: string, trialId: string, operator: string, reason: string,
): Promise<DemoModelAdmission> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/demo-model-admission`, {
    method: "POST", body: JSON.stringify({ campaignId, trialId, operator, reason }),
  });
  return demoModelAdmissionSchema.parse(data);
}

export async function createModelEvaluationReport(
  experimentId: string,
): Promise<ModelEvaluationReport> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/model-evaluation-reports`,
    { method: "POST" },
  );
  return modelEvaluationReportSchema.parse(data);
}

export async function getModelEvaluationReports(
  experimentId: string,
): Promise<ModelEvaluationReport[]> {
  const data = await requestJson<unknown[]>(
    `/experiments/${encodeURIComponent(experimentId)}/model-evaluation-reports`,
  );
  return data.map((item) => modelEvaluationReportSchema.parse(item));
}

export async function reviewModelEvaluationReport(
  experimentId: string,
  reportId: string,
  decision: "approved" | "rejected",
  operator: string,
  reason: string,
): Promise<ModelEvaluationReport> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/model-evaluation-reports/${encodeURIComponent(reportId)}/review`,
    {
      method: "POST",
      body: JSON.stringify({ decision, operator, reason }),
    },
  );
  return modelEvaluationReportSchema.parse(data);
}

export async function cancelAgentCommand(taskId: string, reason: string): Promise<AgentCommandTask> {
  const data = await requestJson<unknown>(`/agent-runtime/commands/${encodeURIComponent(taskId)}/cancel`, { method: "POST", body: JSON.stringify({ reason }) });
  return agentCommandTaskSchema.parse(data);
}

export async function replayAgentCommand(taskId: string): Promise<AgentCommandTask> {
  const data = await requestJson<unknown>(`/agent-runtime/commands/${encodeURIComponent(taskId)}/replay`, { method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID() }) });
  return agentCommandTaskSchema.parse(data);
}

export async function stopExperimentAgentRun(experimentId: string, runId: string): Promise<ExperimentAgentRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/${encodeURIComponent(runId)}/stop`, { method: "POST" });
  return experimentAgentRunSchema.parse(data);
}

export async function restartExperimentAgentRun(experimentId: string, runId: string, guidanceId?: string): Promise<ExperimentAgentRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/${encodeURIComponent(runId)}/restart`, { method: "POST", body: JSON.stringify({ guidanceId }) });
  return experimentAgentRunSchema.parse(data);
}

export async function reviewExperimentAgentRun(
  experimentId: string,
  runId: string,
  payload: { decision: "approved" | "rejected"; reason: string; operator: string; impactScope: string[] },
): Promise<ExperimentAgentRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/${encodeURIComponent(runId)}/review`, { method: "POST", body: JSON.stringify(payload) });
  return experimentAgentRunSchema.parse(data);
}

export async function previewExperimentAgentGuidance(experimentId: string, runId: string, prompt: string): Promise<AgentGuidancePreview> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/${encodeURIComponent(runId)}/guidance/preview`, { method: "POST", body: JSON.stringify({ prompt }) });
  return agentGuidancePreviewSchema.parse(data);
}

export async function applyExperimentAgentGuidance(experimentId: string, runId: string, guidanceId: string): Promise<ExperimentAgentRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-runs/${encodeURIComponent(runId)}/guidance/apply`, { method: "POST", body: JSON.stringify({ guidanceId, confirmed: true }) });
  return experimentAgentRunSchema.parse(data);
}

export async function getExperimentFileAuditSummary(
  experimentId: string,
): Promise<ExperimentFileAuditSummary> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/file-audit-summary`,
  );
  return experimentFileAuditSummarySchema.parse(data);
}

export async function getExperimentFileAssets(
  experimentId: string,
): Promise<ExperimentFileAsset[]> {
  const data = await requestJson<unknown[]>(
    `/experiments/${encodeURIComponent(experimentId)}/files`,
  );
  return data.map((item) => experimentFileAssetSchema.parse(item));
}

export async function verifyExperimentFileAsset(
  experimentId: string, assetId: string,
): Promise<ExperimentAssetIntegrityResult> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/files/${encodeURIComponent(assetId)}/integrity`,
  );
  return experimentAssetIntegrityResultSchema.parse(data);
}

export async function deleteExperimentFileAsset(
  experimentId: string, assetId: string, operator: string, reason: string,
): Promise<ExperimentFileDeleteResult> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/files/${encodeURIComponent(assetId)}`,
    { method: "DELETE", body: JSON.stringify({ operator, reason }) },
  );
  return experimentFileDeleteResultSchema.parse(data);
}

export async function uploadExperimentTextFile(
  experimentId: string,
  payload: ExperimentTextFileUploadRequest,
): Promise<ExperimentFileAsset> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/files`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return experimentFileAssetSchema.parse(data);
}

export async function getExperimentDataIntakeRuns(
  experimentId: string,
): Promise<DataCollectionLocalizationRun[]> {
  const data = await requestJson<unknown[]>(
    `/experiments/${encodeURIComponent(experimentId)}/data-intake-runs`,
  );
  return data.map((item) => dataCollectionLocalizationRunSchema.parse(item));
}

export async function createCleaningAlignmentRun(
  experimentId: string, config: Partial<CleaningAlignmentConfig> = {},
): Promise<CleaningAlignmentRun> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/cleaning-alignment-runs`,
    { method: "POST", body: JSON.stringify(config) },
  );
  return cleaningAlignmentRunSchema.parse(data);
}

export async function getCleaningAlignmentRuns(
  experimentId: string,
): Promise<CleaningAlignmentRun[]> {
  const data = await requestJson<unknown[]>(
    `/experiments/${encodeURIComponent(experimentId)}/cleaning-alignment-runs`,
  );
  return data.map((item) => cleaningAlignmentRunSchema.parse(item));
}

export async function reviewCleaningAlignmentRun(
  experimentId: string, runId: string, operator: string, reason: string,
): Promise<CleaningAlignmentRun> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/cleaning-alignment-runs/${encodeURIComponent(runId)}/review`,
    { method: "POST", body: JSON.stringify({ operator, reason }) },
  );
  return cleaningAlignmentRunSchema.parse(data);
}

export async function createFeatureEngineeringRun(
  experimentId: string,
  config: FeatureEngineeringConfig,
): Promise<FeatureEngineeringRun> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/feature-engineering-runs`,
    { method: "POST", body: JSON.stringify(config) },
  );
  return featureEngineeringRunSchema.parse(data);
}

export async function getFeatureEngineeringRuns(
  experimentId: string,
): Promise<FeatureEngineeringRun[]> {
  const data = await requestJson<unknown[]>(
    `/experiments/${encodeURIComponent(experimentId)}/feature-engineering-runs`,
  );
  return data.map((item) => featureEngineeringRunSchema.parse(item));
}

export async function confirmFeatureEngineeringRun(
  experimentId: string,
  featureSetId: string,
  payload: {
    operator: string;
    reason: string;
    selectedFeatureNames: string[];
  },
): Promise<FeatureEngineeringRun> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/feature-engineering-runs/${encodeURIComponent(featureSetId)}/confirm`,
    { method: "POST", body: JSON.stringify(payload) },
  );
  return featureEngineeringRunSchema.parse(data);
}

export async function getExperimentFieldMappingSuggestions(
  experimentId: string,
): Promise<ExperimentFieldMappingSuggestionResponse> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/field-mapping-suggestions`,
  );
  return experimentFieldMappingSuggestionResponseSchema.parse(data);
}

export async function createSchemaRecognitionRun(experimentId: string, commandId: string): Promise<SchemaRecognitionRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/schema-recognition-runs`, {
    method: "POST", body: JSON.stringify({ commandId }),
  });
  return schemaRecognitionRunSchema.parse(data);
}

export async function getSchemaRecognitionRun(experimentId: string, runId: string): Promise<SchemaRecognitionRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/schema-recognition-runs/${encodeURIComponent(runId)}`);
  return schemaRecognitionRunSchema.parse(data);
}

export async function createProductInnovationRun(experimentId: string, commandId: string, input: ProductInnovationInput): Promise<ProductInnovationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/product-innovation-runs`, { method: "POST", body: JSON.stringify({ commandId, input }) });
  return productInnovationRunSchema.parse(data);
}

export async function getProductInnovationRun(experimentId: string, runId: string): Promise<ProductInnovationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/product-innovation-runs/${encodeURIComponent(runId)}`);
  return productInnovationRunSchema.parse(data);
}

export async function getLatestProductInnovationRun(experimentId: string): Promise<ProductInnovationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/product-innovation-runs/latest`);
  return productInnovationRunSchema.parse(data);
}

export async function confirmProductRequirement(experimentId: string, runId: string, commandId: string, operator: string, reason: string): Promise<ProductRequirementVersion> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/product-innovation-runs/${encodeURIComponent(runId)}/confirm`, {
    method: "POST", body: JSON.stringify({ commandId, operator, reason }),
  });
  return productRequirementVersionSchema.parse(data);
}

export async function getLatestProductRequirementVersion(experimentId: string): Promise<ProductRequirementVersion> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/product-requirement-versions/latest`);
  return productRequirementVersionSchema.parse(data);
}

export async function confirmExperimentFieldMappings(
  experimentId: string,
  payload: ExperimentConfirmFieldMappingsRequest,
): Promise<ExperimentConfirmedFieldMappingSet> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/field-mappings/confirm`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return experimentConfirmedFieldMappingSetSchema.parse(data);
}

export async function getExperimentConfirmedFieldMappings(
  experimentId: string,
): Promise<ExperimentConfirmedFieldMappingSet> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/field-mappings`,
  );
  return experimentConfirmedFieldMappingSetSchema.parse(data);
}

export async function upsertExperimentFieldDictionary(
  experimentId: string,
  payload: ExperimentFieldDictionaryUpsertRequest,
): Promise<ExperimentFieldDictionary> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/field-dictionary`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return experimentFieldDictionarySchema.parse(data);
}

export async function getExperimentFieldDictionary(
  experimentId: string,
): Promise<ExperimentFieldDictionary> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/field-dictionary`,
  );
  return experimentFieldDictionarySchema.parse(data);
}

export async function getExperimentCleaningPreview(
  experimentId: string,
): Promise<ExperimentCleaningPreviewResponse> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/cleaning-preview`,
  );
  return experimentCleaningPreviewResponseSchema.parse(data);
}

export async function getExperimentAlignmentPreview(
  experimentId: string,
): Promise<ExperimentAlignmentPreviewResponse> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/alignment-preview`,
  );
  return experimentAlignmentPreviewResponseSchema.parse(data);
}

export async function getExperimentFeaturePreview(
  experimentId: string,
): Promise<ExperimentFeaturePreviewResponse> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/feature-preview`,
  );
  return experimentFeaturePreviewResponseSchema.parse(data);
}

export async function createExperimentDatasetSnapshot(
  experimentId: string,
): Promise<ExperimentDatasetSnapshot> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/dataset-snapshots`,
    {
      method: "POST",
    },
  );
  return experimentDatasetSnapshotSchema.parse(data);
}

export async function getLatestExperimentDatasetSnapshot(
  experimentId: string,
): Promise<ExperimentDatasetSnapshot> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/dataset-snapshots/latest`,
  );
  return experimentDatasetSnapshotSchema.parse(data);
}

export async function getExperimentModelingPlanPreview(
  experimentId: string,
): Promise<ExperimentModelingPlanPreview> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/modeling-plan-preview`,
  );
  return experimentModelingPlanPreviewSchema.parse(data);
}

export async function createExperimentTrainingTask(
  experimentId: string,
): Promise<ExperimentTrainingTaskPreview> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/training-tasks`,
    {
      method: "POST",
    },
  );
  return experimentTrainingTaskPreviewSchema.parse(data);
}

export async function getLatestExperimentTrainingTask(
  experimentId: string,
): Promise<ExperimentTrainingTaskPreview> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/training-tasks/latest`,
  );
  return experimentTrainingTaskPreviewSchema.parse(data);
}

export async function getLatestExperimentTrainingResult(
  experimentId: string,
): Promise<ExperimentTrainingResultSummary> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/training-results/latest`,
  );
  return experimentTrainingResultSummarySchema.parse(data);
}

export async function createResultInterpretationRun(experimentId: string, commandId: string): Promise<ResultInterpretationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/result-interpretation-runs`, {
    method: "POST", body: JSON.stringify({ commandId }),
  });
  return resultInterpretationRunSchema.parse(data);
}

export async function getResultInterpretationRun(experimentId: string, runId: string): Promise<ResultInterpretationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/result-interpretation-runs/${encodeURIComponent(runId)}`);
  return resultInterpretationRunSchema.parse(data);
}

export async function getLatestExperimentResearchBrief(
  experimentId: string,
): Promise<ExperimentResearchBriefSummary> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/research-brief/latest`,
  );
  return experimentResearchBriefSummarySchema.parse(data);
}

export async function getLatestExperimentSimulationInput(
  experimentId: string,
): Promise<ExperimentSimulationInputSummary> {
  const data = await requestJson<unknown>(
    `/experiments/${encodeURIComponent(experimentId)}/simulation-inputs/latest`,
  );
  return experimentSimulationInputSummarySchema.parse(data);
}

export async function getProductionLines(): Promise<ProcessProductionLine[]> {
  const data = await requestJson<unknown[]>("/process/production-lines");
  return data.map((item) => processProductionLineSchema.parse(item));
}

export async function generateProcessTask(payload: ProcessTaskRequest): Promise<GeneratedProcessTask> {
  const data = await requestJson<unknown>("/process/tasks/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return generatedProcessTaskSchema.parse(data);
}

export async function submitProcessFeedback(payload: ProcessFeedbackRequest): Promise<ProcessFeedback> {
  const data = await requestJson<unknown>("/process/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return processFeedbackSchema.parse(data);
}

export async function predictSimulation(payload: SimulationPredictRequest): Promise<SimulationPredictResponse> {
  const data = await requestJson<unknown>("/simulation/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return simulationPredictResponseSchema.parse(data);
}

export async function predictWithPromotedModel(experimentId: string, inputs: Record<string, number>, modelVersion?: string, allowExtrapolation = false): Promise<PromotedModelPrediction> {
  const data = await requestJson<unknown>(`/simulation/experiments/${encodeURIComponent(experimentId)}/promoted-model/predict`, {
    method: "POST", body: JSON.stringify({ inputs, modelVersion: modelVersion ?? null, allowExtrapolation }),
  });
  return promotedModelPredictionSchema.parse(data);
}

export async function getPromotedModels(experimentId: string): Promise<PromotedModelRecord[]> {
  const data = await requestJson<unknown[]>(`/simulation/experiments/${encodeURIComponent(experimentId)}/promoted-models`);
  return data.map((item) => promotedModelRecordSchema.parse(item));
}

export async function getModelAssets(): Promise<ModelAssetSummary[]> {
  const data = await requestJson<unknown[]>("/simulation/model-assets");
  return data.map((item) => modelAssetSummarySchema.parse(item));
}

export async function getModelAssetDetail(experimentId: string, modelVersion: string): Promise<ModelAssetDetail> {
  const data = await requestJson<unknown>(`/simulation/model-assets/${encodeURIComponent(experimentId)}/${encodeURIComponent(modelVersion)}`);
  return modelAssetDetailSchema.parse(data);
}

export async function enqueueFeatureBindingSuggestion(
  experimentId: string, modelVersion: string, adapterPack?: DeviceAdapterPackSelector,
): Promise<AgentCommandTask> {
  const commandId = `binding-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const data = await requestJson<unknown>(
    `/simulation/experiments/${encodeURIComponent(experimentId)}/models/${encodeURIComponent(modelVersion)}/binding-suggestion-runs/enqueue`,
    { method: "POST", body: JSON.stringify({ commandId, priority: 1, adapterPack: adapterPack ?? null }) },
  );
  return agentCommandTaskSchema.parse(data);
}

export async function getDeviceAdapterPacks(enterpriseKey?: string): Promise<DeviceAdapterPack[]> {
  const query = enterpriseKey ? `?enterpriseKey=${encodeURIComponent(enterpriseKey)}` : "";
  const data = await requestJson<unknown[]>(`/simulation/device-adapter-packs${query}`);
  return data.map((item) => deviceAdapterPackSchema.parse(item));
}

export async function createDeviceAdapterPack(payload: DeviceAdapterPackCreate): Promise<DeviceAdapterPack> {
  const data = await requestJson<unknown>("/simulation/device-adapter-packs/export", {
    method: "POST", body: JSON.stringify(payload),
  });
  return deviceAdapterPackSchema.parse(data);
}

export async function compareDeviceAdapterPacks(
  enterpriseKey: string, deviceType: string, baseVersion: string, targetVersion: string,
): Promise<DeviceAdapterPackComparison> {
  const query = new URLSearchParams({ enterpriseKey, deviceType, baseVersion, targetVersion });
  const data = await requestJson<unknown>(`/simulation/device-adapter-packs/compare?${query.toString()}`);
  return deviceAdapterPackComparisonSchema.parse(data);
}

export async function getFeatureBindingSuggestionRun(
  experimentId: string, runId: string,
): Promise<FeatureBindingSuggestionRun> {
  const data = await requestJson<unknown>(
    `/simulation/experiments/${encodeURIComponent(experimentId)}/binding-suggestion-runs/${encodeURIComponent(runId)}`,
  );
  return featureBindingSuggestionRunSchema.parse(data);
}

export async function confirmSimulationModelBinding(experimentId: string, payload: Omit<FeatureBindingVersion, "experimentId" | "createdAt" | "status">): Promise<FeatureBindingVersion> {
  const data = await requestJson<unknown>(`/simulation/experiments/${encodeURIComponent(experimentId)}/model-bindings`, {
    method: "POST", body: JSON.stringify(payload),
  });
  return featureBindingVersionSchema.parse(data);
}

export async function predictCompositeModel(experimentId: string, parameters: Record<string, unknown>, targetFields: string[], allowExtrapolation = false): Promise<CompositeModelPrediction> {
  const data = await requestJson<unknown>(`/simulation/experiments/${encodeURIComponent(experimentId)}/composite-predict`, {
    method: "POST", body: JSON.stringify({ parameters, targetFields, allowExtrapolation }),
  });
  return compositeModelPredictionSchema.parse(data);
}

export async function getSimulationScenarios(): Promise<SimulationScenario[]> {
  const data = await requestJson<unknown[]>("/simulation/scenarios");
  return data.map((item) => simulationScenarioSchema.parse(item));
}

export async function getSimulationLlmStatus(): Promise<SimulationLlmStatus> {
  const data = await requestJson<unknown>("/simulation/llm-status");
  return simulationLlmStatusSchema.parse(data);
}

export async function getLatestOptimizationRun(experimentId: string): Promise<ExperimentOptimizationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/optimization-runs/latest`);
  return experimentOptimizationRunSchema.parse(data);
}

export async function getOptimizationRuns(experimentId: string): Promise<ExperimentOptimizationRun[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/optimization-runs`);
  return data.map((item) => experimentOptimizationRunSchema.parse(item));
}

export async function getValidationBatches(experimentId: string): Promise<ExperimentalValidationBatch[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/validation-batches`);
  return data.map((item) => experimentalValidationBatchSchema.parse(item));
}

export async function createValidationBatch(experimentId: string, payload: {
  optimizationRunId: string; parameterVersion: string; predictedResultVersion: string;
  batchCode: string; scale: "lab" | "pilot"; operator: string; plannedAt: string;
}): Promise<ExperimentalValidationBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/validation-batches`, {
    method: "POST", body: JSON.stringify(payload),
  });
  return experimentalValidationBatchSchema.parse(data);
}

export async function submitValidationBatch(experimentId: string, batchId: string, payload: {
  actualParameters: OptimizationParameters;
  measurements: Array<{ metricName: string; value: number; unit: string; replicate: number; measuredAt: string; method: string; sourceAssetId: string | null; isModelTarget: boolean }>;
  contaminationObserved: boolean; equipmentAbnormalities: string[]; notes: string;
}): Promise<ExperimentalValidationBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/validation-batches/${encodeURIComponent(batchId)}/submit`, {
    method: "POST", body: JSON.stringify(payload),
  });
  return experimentalValidationBatchSchema.parse(data);
}

export async function reviewValidationBatch(experimentId: string, batchId: string, decision: "approved" | "rejected", operator: string, reason: string): Promise<ExperimentalValidationBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/validation-batches/${encodeURIComponent(batchId)}/review`, {
    method: "POST", body: JSON.stringify({ decision, operator, reason }),
  });
  return experimentalValidationBatchSchema.parse(data);
}

export async function getFeedbackRetrainingRuns(experimentId: string): Promise<FeedbackRetrainingRun[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/feedback-retraining-runs`);
  return data.map((item) => feedbackRetrainingRunSchema.parse(item));
}

export async function createFeedbackRetrainingRun(experimentId: string, payload: {
  commandId: string; parentModelVersion: string; feedbackDatasetVersions: string[]; fixedBudgetSeconds: number;
}): Promise<FeedbackRetrainingRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/feedback-retraining-runs`, {
    method: "POST", body: JSON.stringify(payload),
  });
  return feedbackRetrainingRunSchema.parse(data);
}

export async function advanceFeedbackRetrainingRun(experimentId: string, runId: string): Promise<FeedbackRetrainingRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/feedback-retraining-runs/${encodeURIComponent(runId)}/advance`, { method: "POST" });
  return feedbackRetrainingRunSchema.parse(data);
}

export async function reviewFeedbackRetrainingRun(experimentId: string, runId: string, decision: "approved" | "rejected", operator: string, reason: string): Promise<FeedbackRetrainingRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/feedback-retraining-runs/${encodeURIComponent(runId)}/review`, {
    method: "POST", body: JSON.stringify({ decision, operator, reason }),
  });
  return feedbackRetrainingRunSchema.parse(data);
}

export async function getSupplementaryDesignRuns(experimentId: string): Promise<SupplementaryExperimentDesignRun[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-design-runs`);
  return data.map((item) => supplementaryExperimentDesignRunSchema.parse(item));
}

export async function createSupplementaryDesignRun(experimentId: string, reportId: string): Promise<SupplementaryExperimentDesignRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-design-runs`, {
    method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), reportId }),
  });
  return supplementaryExperimentDesignRunSchema.parse(data);
}

export async function selectSupplementaryDesignCandidates(experimentId: string, runId: string, candidateIds: string[]): Promise<SupplementaryExperimentDesignRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-design-runs/${encodeURIComponent(runId)}/selection`, {
    method: "PATCH", body: JSON.stringify({ candidateIds }),
  });
  return supplementaryExperimentDesignRunSchema.parse(data);
}

export async function reviewSupplementaryDesignRun(experimentId: string, runId: string, decision: "approved" | "rejected", operator: string, reason: string): Promise<SupplementaryExperimentDesignRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-design-runs/${encodeURIComponent(runId)}/review`, {
    method: "POST", body: JSON.stringify({ decision, operator, reason }),
  });
  return supplementaryExperimentDesignRunSchema.parse(data);
}

export async function getSupplementaryExecutionBatches(experimentId: string): Promise<SupplementaryExecutionBatch[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-execution-batches`);
  return data.map((item) => supplementaryExecutionBatchSchema.parse(item));
}

export async function createSupplementaryExecutionBatch(experimentId: string, input: {
  designRunId: string; planVersion: string; candidateId: string; batchCode: string;
  scale: "lab" | "pilot"; operator: string; plannedAt: string; replicateCount: number;
  samplingRequirements: string[];
}): Promise<SupplementaryExecutionBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-execution-batches`, {
    method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), ...input }),
  });
  return supplementaryExecutionBatchSchema.parse(data);
}

export async function startSupplementaryExecutionBatch(experimentId: string, batchId: string, operator: string, note: string): Promise<SupplementaryExecutionBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-execution-batches/${encodeURIComponent(batchId)}/start`, {
    method: "POST", body: JSON.stringify({ operator, note }),
  });
  return supplementaryExecutionBatchSchema.parse(data);
}

export async function updateSupplementaryExecutionStep(experimentId: string, batchId: string, stepKey: string, status: "inProgress" | "completed", operator: string, note: string): Promise<SupplementaryExecutionBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-execution-batches/${encodeURIComponent(batchId)}/steps/${encodeURIComponent(stepKey)}`, {
    method: "POST", body: JSON.stringify({ operator, status, note }),
  });
  return supplementaryExecutionBatchSchema.parse(data);
}

export async function attachSupplementaryExecutionAssets(experimentId: string, batchId: string, assetIds: string[], operator: string, note: string): Promise<SupplementaryExecutionBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-execution-batches/${encodeURIComponent(batchId)}/assets`, {
    method: "POST", body: JSON.stringify({ operator, assetIds, note }),
  });
  return supplementaryExecutionBatchSchema.parse(data);
}

export async function reviewSupplementaryExecutionBatch(experimentId: string, batchId: string, decision: "approved" | "rejected", operator: string, reason: string): Promise<SupplementaryExecutionBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-execution-batches/${encodeURIComponent(batchId)}/review`, {
    method: "POST", body: JSON.stringify({ decision, operator, reason }),
  });
  return supplementaryExecutionBatchSchema.parse(data);
}

export async function getSupplementaryMeasurementBatches(experimentId: string): Promise<SupplementaryMeasurementBatch[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-measurement-batches`);
  return data.map((item) => supplementaryMeasurementBatchSchema.parse(item));
}

export async function createSupplementaryMeasurementBatch(experimentId: string, executionBatchId: string, operator: string): Promise<SupplementaryMeasurementBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-measurement-batches`, {
    method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), executionBatchId, operator }),
  });
  return supplementaryMeasurementBatchSchema.parse(data);
}

export async function submitSupplementaryMeasurementBatch(experimentId: string, batchId: string, input: {
  actualParameters: OptimizationParameters;
  measurements: { metricName: string; value: number; unit: string; replicate: number; measuredAt: string; method: string; sourceAssetId: string; isModelTarget: boolean }[];
  contaminationObserved: boolean; equipmentAbnormalities: string[]; notes: string;
}): Promise<SupplementaryMeasurementBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-measurement-batches/${encodeURIComponent(batchId)}/submit`, {
    method: "POST", body: JSON.stringify(input),
  });
  return supplementaryMeasurementBatchSchema.parse(data);
}

export async function reviewSupplementaryMeasurementBatch(experimentId: string, batchId: string, decision: "approved" | "rejected", operator: string, reason: string): Promise<SupplementaryMeasurementBatch> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/supplementary-measurement-batches/${encodeURIComponent(batchId)}/review`, {
    method: "POST", body: JSON.stringify({ decision, operator, reason }),
  });
  return supplementaryMeasurementBatchSchema.parse(data);
}

export async function getExperimentLifecycle(experimentId: string): Promise<ExperimentLifecycleOverview> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/lifecycle`);
  return experimentLifecycleOverviewSchema.parse(data);
}

export async function getExperimentLifecycleSummaries(): Promise<ExperimentLifecycleSummary[]> {
  const data = await requestJson<unknown[]>("/experiments/lifecycle-summaries");
  return data.map((item) => experimentLifecycleSummarySchema.parse(item));
}

export async function getHumanActionCenter(filters: { priority?: "high" | "medium" | "normal"; stageKey?: string; experimentId?: string } = {}): Promise<HumanActionCenter> {
  const query = new URLSearchParams();
  if (filters.priority) query.set("priority", filters.priority);
  if (filters.stageKey) query.set("stageKey", filters.stageKey);
  if (filters.experimentId) query.set("experimentId", filters.experimentId);
  const suffix = query.size ? `?${query.toString()}` : "";
  const data = await requestJson<unknown>(`/experiments/human-actions${suffix}`);
  return humanActionCenterSchema.parse(data);
}

export async function getAgentTaskCenter(experimentId: string): Promise<AgentTaskCenter> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-task-center`);
  return agentTaskCenterSchema.parse(data);
}

export async function getResearchReports(experimentId: string): Promise<ResearchReport[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/research-reports`);
  return data.map((item) => researchReportSchema.parse(item));
}

export async function createResearchReport(experimentId: string): Promise<ResearchReport> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-reports`, {
    method: "POST", body: JSON.stringify({ commandId: `report-${Date.now()}-${Math.random().toString(16).slice(2)}` }),
  });
  return researchReportSchema.parse(data);
}

export async function reviewResearchReport(
  experimentId: string, reportId: string,
  input: { operator: string; reason: string; approvedStatementIds: string[] },
): Promise<ResearchReport> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/research-reports/${encodeURIComponent(reportId)}/review`, {
    method: "POST", body: JSON.stringify(input),
  });
  return researchReportSchema.parse(data);
}

export async function depositResearchReportKnowledge(experimentId: string, reportId: string): Promise<EnterpriseKnowledgeEntry[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/research-reports/${encodeURIComponent(reportId)}/knowledge-deposit`, { method: "POST" });
  return data.map((item) => enterpriseKnowledgeEntrySchema.parse(item));
}

export async function getEnterpriseKnowledge(experimentId?: string): Promise<EnterpriseKnowledgeEntry[]> {
  const suffix = experimentId ? `?experimentId=${encodeURIComponent(experimentId)}` : "";
  const data = await requestJson<unknown[]>(`/experiments/enterprise-knowledge${suffix}`);
  return data.map((item) => enterpriseKnowledgeEntrySchema.parse(item));
}

export async function registerEnterpriseKnowledgeUsage(experimentId: string, input: { knowledgeIds: string[]; purpose: EnterpriseKnowledgeUsage["purpose"]; targetVersion: string; operator: string; note: string }): Promise<EnterpriseKnowledgeUsage> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/knowledge-usage`, { method: "POST", body: JSON.stringify({ ...input, knowledgeIds: input.knowledgeIds }) });
  return enterpriseKnowledgeUsageSchema.parse(data);
}

export async function getEnterpriseKnowledgeUsage(experimentId: string): Promise<EnterpriseKnowledgeUsage[]> {
  const data = await requestJson<unknown[]>(`/experiments/${encodeURIComponent(experimentId)}/knowledge-usage`);
  return data.map((item) => enterpriseKnowledgeUsageSchema.parse(item));
}

export async function createOptimizationRun(experimentId: string): Promise<ExperimentOptimizationRun> {
  await runDomainAgentCommand(experimentId, "optimization", "new", "optimizationCreate");
  return getLatestOptimizationRun(experimentId);
}

export async function selectOptimizationCandidate(experimentId: string, runId: string, planId: string, parameters: OptimizationParameters): Promise<ExperimentOptimizationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/optimization-runs/${encodeURIComponent(runId)}/selection`, { method: "PATCH", body: JSON.stringify({ planId, parameters }) });
  return experimentOptimizationRunSchema.parse(data);
}

export async function submitOptimizationRun(experimentId: string, runId: string): Promise<ExperimentOptimizationRun> {
  await runDomainAgentCommand(experimentId, "optimization", runId, "optimizationSubmit");
  return getLatestOptimizationRun(experimentId);
}

export async function advanceOptimizationRun(experimentId: string, runId: string): Promise<ExperimentOptimizationRun> {
  await runDomainAgentCommand(experimentId, "optimization", runId, "optimizationAdvance");
  return getLatestOptimizationRun(experimentId);
}

export async function restartDemoOptimizationRun(experimentId: string, runId: string): Promise<ExperimentOptimizationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/optimization-runs/${encodeURIComponent(runId)}/restart-demo`, { method: "POST" });
  return experimentOptimizationRunSchema.parse(data);
}

async function runDomainAgentCommand(experimentId: string, targetKind: "simulation" | "optimization", runId: string, action: "simulationCreate" | "simulationAdvance" | "simulationStop" | "simulationRetry" | "optimizationCreate" | "optimizationSubmit" | "optimizationAdvance"): Promise<AgentCommandTask> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/agent-commands`, {
    method: "POST", body: JSON.stringify({ commandId: crypto.randomUUID(), targetKind, runId, action, expectedRevision: 1, payload: {}, maxAttempts: 3, priority: action.endsWith("Stop") ? 10 : 0 }),
  });
  let task = agentCommandTaskSchema.parse(data);
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (task.status === "completed") return task;
    if (["deadLetter", "failed", "cancelled"].includes(task.status)) throw new Error(`后台任务 ${task.status}：${task.errorCategory ?? "unknown"} · ${task.errorMessage ?? "无详细信息"}`);
    await new Promise((resolve) => window.setTimeout(resolve, 500));
    task = await getAgentCommand(task.taskId);
  }
  throw new Error("后台任务等待超时，请检查 agent-worker 状态");
}

export async function reviewOptimizationRun(experimentId: string, runId: string, decision: "approved" | "rejected", reason: string, operator: string): Promise<ExperimentOptimizationRun> {
  const data = await requestJson<unknown>(`/experiments/${encodeURIComponent(experimentId)}/optimization-runs/${encodeURIComponent(runId)}/review`, { method: "POST", body: JSON.stringify({ decision, reason, operator, impactScope: ["新模型版本", "新实验结果版本"] }) });
  return experimentOptimizationRunSchema.parse(data);
}
