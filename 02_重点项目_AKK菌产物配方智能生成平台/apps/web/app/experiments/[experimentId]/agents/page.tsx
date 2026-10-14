import { AgentTaskCenterView } from "@/components/experiments/agent-task-center-view";
import { getAgentTaskCenter } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AgentTaskCenterPage({ params }: Readonly<{ params: Promise<{ experimentId: string }> }>) {
  const { experimentId } = await params;
  return <AgentTaskCenterView center={await getAgentTaskCenter(experimentId)}/>;
}
