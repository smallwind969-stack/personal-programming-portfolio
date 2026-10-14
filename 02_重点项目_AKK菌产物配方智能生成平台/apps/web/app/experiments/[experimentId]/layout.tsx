import type { ReactNode } from "react";

import { ExperimentWorkspaceNav } from "@/components/experiments/experiment-workspace-nav";
import { getExperimentWorkspaceOverview } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ExperimentLayout({ children, params }: Readonly<{ children: ReactNode; params: Promise<{ experimentId: string }> }>) {
  const { experimentId } = await params;
  const overview = await getExperimentWorkspaceOverview(experimentId);
  return <div className="grid gap-4 lg:grid-cols-[13.5rem_1fr]"><ExperimentWorkspaceNav experimentId={overview.experimentId} name={overview.name} stages={overview.stages} /><section className="min-w-0">{children}</section></div>;
}
