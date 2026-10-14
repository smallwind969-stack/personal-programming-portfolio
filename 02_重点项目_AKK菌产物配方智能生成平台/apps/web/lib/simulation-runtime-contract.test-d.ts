import type { ExperimentSimulationRun, SimulationTrialSnapshot } from "./schemas";
import {
  advanceExperimentSimulationRun,
  createExperimentSimulationRun,
  createExperimentSimulationTrial,
  getLatestExperimentSimulationRun,
  restartExperimentSimulationRun,
  stopExperimentSimulationRun,
} from "./api";
import type { SimulationPredictRequest } from "./schemas";

declare const run: ExperimentSimulationRun;
declare const snapshot: SimulationTrialSnapshot;
run.stages satisfies { stageKey: string; waitingReason: string | null }[];
snapshot.baselineDifferences satisfies string[];
getLatestExperimentSimulationRun satisfies (experimentId: string) => Promise<ExperimentSimulationRun>;
createExperimentSimulationRun satisfies (experimentId: string) => Promise<ExperimentSimulationRun>;
advanceExperimentSimulationRun satisfies (experimentId: string, runId: string) => Promise<ExperimentSimulationRun>;
stopExperimentSimulationRun satisfies (experimentId: string, runId: string) => Promise<ExperimentSimulationRun>;
restartExperimentSimulationRun satisfies (experimentId: string, runId: string) => Promise<ExperimentSimulationRun>;
createExperimentSimulationTrial satisfies (experimentId: string, runId: string, payload: SimulationPredictRequest) => Promise<SimulationTrialSnapshot>;
