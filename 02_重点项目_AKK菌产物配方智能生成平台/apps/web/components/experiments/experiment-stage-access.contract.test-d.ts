import type { ComponentProps } from "react";

import { ExperimentStageAccess } from "@/components/experiments/experiment-stage-access";
import type { ExperimentStageSummary } from "@/lib/schemas";

declare const stage: ExperimentStageSummary;

const props = {
  experimentId: "exp-contract",
  stage,
  children: null,
} satisfies ComponentProps<typeof ExperimentStageAccess>;

void props;
