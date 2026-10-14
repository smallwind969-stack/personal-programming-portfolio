import { FeatureBindingAdvisorPanel } from "./feature-binding-advisor-panel";
import type { DeviceAdapterPack, PromotedModelRecord, ExperimentWorkspaceOverview } from "@/lib/schemas";

FeatureBindingAdvisorPanel satisfies (props: {
  experimentId: string;
  promotedModels: PromotedModelRecord[];
  adapterPacks: DeviceAdapterPack[];
  activeBindingVersions: string[];
  parameterDefinitions: ExperimentWorkspaceOverview["productionContext"]["parameterDefinitions"];
}) => import("react").ReactNode;
