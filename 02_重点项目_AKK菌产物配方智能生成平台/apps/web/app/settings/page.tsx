import { ModelCapabilityCenter } from "@/components/settings/model-capability-center";
import { getAgentQueueStatus, getAgentRuntimeStatus, getLlmStatus } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [llm, queue, runtime] = await Promise.all([
    getLlmStatus(), getAgentQueueStatus(), getAgentRuntimeStatus(),
  ]);
  return <ModelCapabilityCenter initialStatus={llm} queue={queue} runtime={runtime}/>;
}
