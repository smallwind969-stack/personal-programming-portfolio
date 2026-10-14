import { GlobalRunCenter } from "@/components/runs/global-run-center";
import { getAgentQueueStatus, getAgentTaskCenter, getExperimentArchive, getHumanActionCenter, getRecentAgentCommands } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const [archive, queue, commands, humanActions] = await Promise.all([
    getExperimentArchive(),
    getAgentQueueStatus(),
    getRecentAgentCommands(50),
    getHumanActionCenter(),
  ]);
  const taskCenters = await Promise.all(
    archive.experiments.map((experiment) =>
      getAgentTaskCenter(experiment.experimentId).catch(() => null),
    ),
  );
  return <GlobalRunCenter archive={archive} commands={commands} humanActions={humanActions} queue={queue} taskCenters={taskCenters.filter((item) => item !== null)} />;
}
