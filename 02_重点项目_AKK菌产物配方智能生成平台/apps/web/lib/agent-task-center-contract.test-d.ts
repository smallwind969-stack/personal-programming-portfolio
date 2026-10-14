import type { AgentTaskCenter, AgentTaskProjection } from "@/lib/schemas";
import { getAgentTaskCenter } from "@/lib/api";
import { AgentTaskCenterView } from "@/components/experiments/agent-task-center-view";

declare const center: AgentTaskCenter;
center.tasks satisfies AgentTaskProjection[];
getAgentTaskCenter satisfies (experimentId: string) => Promise<AgentTaskCenter>;
void AgentTaskCenterView;
