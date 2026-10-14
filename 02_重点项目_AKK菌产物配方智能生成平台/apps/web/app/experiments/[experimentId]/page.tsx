import { ExperimentOverview } from "@/components/experiments/experiment-overview";
import { ExperimentLifecycleOverviewCard } from "@/components/experiments/experiment-lifecycle-overview";
import { getExperimentDataIntakeRuns, getExperimentFileAssets, getExperimentLifecycle, getExperimentWorkspaceOverview } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ExperimentOverviewPage({ params }: Readonly<{ params: Promise<{ experimentId: string }> }>) {
  const { experimentId } = await params;
  const [overview, intakeRuns, lifecycle, fileAssets] = await Promise.all([
    getExperimentWorkspaceOverview(experimentId),
    getExperimentDataIntakeRuns(experimentId),
    getExperimentLifecycle(experimentId),
    getExperimentFileAssets(experimentId),
  ]);
  return <><ExperimentLifecycleOverviewCard lifecycle={lifecycle}/><ExperimentOverview overview={overview} initialIntakeRun={intakeRuns.at(-1) ?? null} fileAssets={fileAssets} /></>;
}
