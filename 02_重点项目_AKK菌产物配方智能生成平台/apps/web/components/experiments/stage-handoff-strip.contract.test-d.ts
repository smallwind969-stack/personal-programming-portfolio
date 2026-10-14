import type { ComponentProps } from "react";

import { StageHandoffStrip } from "@/components/experiments/stage-handoff-strip";
import type { ExperimentStageSummary } from "@/lib/schemas";

declare const stages: ExperimentStageSummary[];

const props = {
  experimentId: "exp-demo",
  phase: "simulation",
  stages,
} satisfies ComponentProps<typeof StageHandoffStrip>;

void props;
