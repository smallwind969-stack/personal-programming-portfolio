import type {
  AgentGuidancePreview,
  AgentRunNode,
  ExperimentAgentRun,
} from "./schemas";
import {
  advanceExperimentAgentRun,
  applyExperimentAgentGuidance,
  enqueueExperimentAgentCommand,
  getAgentCommand,
  getAgentQueueStatus,
  getAgentCatalog,
  cancelAgentCommand,
  replayAgentCommand,
  getLatestExperimentAgentRun,
  previewExperimentAgentGuidance,
  restartExperimentAgentRun,
  reviewExperimentAgentRun,
  stopExperimentAgentRun,
} from "./api";

declare const node: AgentRunNode;
declare const run: ExperimentAgentRun;
declare const guidance: AgentGuidancePreview;

node.methodSummary satisfies string[];
run.nodes satisfies AgentRunNode[];
guidance.affectedNodes satisfies string[];
getLatestExperimentAgentRun satisfies (experimentId: string) => Promise<ExperimentAgentRun>;
advanceExperimentAgentRun satisfies (experimentId: string, runId: string, expectedRevision: number) => Promise<ExperimentAgentRun>;
stopExperimentAgentRun satisfies (experimentId: string, runId: string) => Promise<ExperimentAgentRun>;
restartExperimentAgentRun satisfies (experimentId: string, runId: string) => Promise<ExperimentAgentRun>;
reviewExperimentAgentRun satisfies (experimentId: string, runId: string, payload: { decision: "approved" | "rejected"; reason: string; operator: string; impactScope: string[] }) => Promise<ExperimentAgentRun>;
previewExperimentAgentGuidance satisfies (experimentId: string, runId: string, prompt: string) => Promise<AgentGuidancePreview>;
applyExperimentAgentGuidance satisfies (experimentId: string, runId: string, guidanceId: string) => Promise<ExperimentAgentRun>;
enqueueExperimentAgentCommand satisfies (experimentId: string, runId: string, action: "advance" | "stop", expectedRevision: number) => Promise<import("./schemas").AgentCommandTask>;
getAgentCommand satisfies (taskId: string) => Promise<import("./schemas").AgentCommandTask>;
getAgentQueueStatus satisfies () => Promise<import("./schemas").AgentQueueStatus>;
getAgentCatalog satisfies () => Promise<import("./schemas").AgentCatalogSnapshot>;
cancelAgentCommand satisfies (taskId: string, reason: string) => Promise<import("./schemas").AgentCommandTask>;
replayAgentCommand satisfies (taskId: string) => Promise<import("./schemas").AgentCommandTask>;
