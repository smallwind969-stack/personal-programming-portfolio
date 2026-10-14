import type { ComponentProps } from "react";

import { ExperimentOverview } from "@/components/experiments/experiment-overview";
import { ExperimentWorkspaceNav } from "@/components/experiments/experiment-workspace-nav";
import type { ExperimentWorkspaceOverview } from "@/lib/schemas";

declare const overview: ExperimentWorkspaceOverview;

const overviewProps = { overview } satisfies ComponentProps<typeof ExperimentOverview>;
const navProps = {
  experimentId: overview.experimentId,
  name: overview.name,
  stages: overview.stages,
} satisfies ComponentProps<typeof ExperimentWorkspaceNav>;

void overviewProps;
void navProps;
