import { SimulationRuntimeWorkbench } from "./simulation-runtime-workbench";
import type { ExperimentSimulationRun, ExperimentWorkspaceOverview } from "../../lib/schemas";

SimulationRuntimeWorkbench satisfies (props: {
  experimentId: string;
  initialRun: ExperimentSimulationRun;
  productionContext: ExperimentWorkspaceOverview["productionContext"];
}) => React.ReactNode;
