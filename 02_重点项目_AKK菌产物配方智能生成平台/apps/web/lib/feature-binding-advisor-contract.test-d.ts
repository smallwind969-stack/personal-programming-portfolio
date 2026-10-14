import {
  confirmSimulationModelBinding,
  enqueueFeatureBindingSuggestion,
  getAgentCommand,
  getFeatureBindingSuggestionRun,
  getDeviceAdapterPacks,
  getPromotedModels,
} from "./api";
import type {
  AgentCommandTask,
  FeatureBindingSuggestionRun,
  FeatureBindingVersion,
  PromotedModelRecord,
  DeviceAdapterPack,
  DeviceAdapterPackSelector,
} from "./schemas";

getPromotedModels satisfies (experimentId: string) => Promise<PromotedModelRecord[]>;
enqueueFeatureBindingSuggestion satisfies (
  experimentId: string,
  modelVersion: string,
  adapterPack?: DeviceAdapterPackSelector,
) => Promise<AgentCommandTask>;
getDeviceAdapterPacks satisfies (enterpriseKey?: string) => Promise<DeviceAdapterPack[]>;
getAgentCommand satisfies (taskId: string) => Promise<AgentCommandTask>;
getFeatureBindingSuggestionRun satisfies (
  experimentId: string,
  runId: string,
) => Promise<FeatureBindingSuggestionRun>;
confirmSimulationModelBinding satisfies (
  experimentId: string,
  payload: Omit<FeatureBindingVersion, "experimentId" | "createdAt" | "status">,
) => Promise<FeatureBindingVersion>;
