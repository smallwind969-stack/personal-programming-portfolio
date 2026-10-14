import { AgentExecutionCenter } from "./agent-execution-center";
import type { ExperimentAgentRun } from "../../lib/schemas";

AgentExecutionCenter satisfies (props: {
  experimentId: string;
  initialRun: ExperimentAgentRun;
}) => React.ReactNode;
