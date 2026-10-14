import type { ComponentProps } from "react";

import { DataAnalysisProgressPanel } from "@/components/experiments/data-analysis-progress";
import { getDataAnalysisProgress } from "@/lib/api";
import {
  dataAnalysisProgressSchema,
  type DataAnalysisProgress,
} from "@/lib/schemas";

const progress = dataAnalysisProgressSchema.parse({
  experimentId: "exp-contract",
  experimentName: "契约实验",
  sourceType: "sample",
  progressPercent: 25,
  currentStepKey: "mappingReview",
  currentAction: "人工确认字段与单位",
  steps: [],
  disclaimer: "只读",
}) satisfies DataAnalysisProgress;

const props = { progress } satisfies ComponentProps<typeof DataAnalysisProgressPanel>;

void props;
void getDataAnalysisProgress;
