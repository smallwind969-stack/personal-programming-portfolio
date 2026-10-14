import type { ComponentProps } from "react";

import { ExperimentArchiveDashboard } from "@/components/experiments/experiment-archive-dashboard";
import { stageLabels, statusLabels } from "@/components/experiments/experiment-status";
import type { ExperimentArchiveResponse } from "@/lib/schemas";

const archive = {
  totalCount: 0,
  runningCount: 0,
  completedCount: 0,
  averageConfidenceScore: 0,
  experiments: [],
} satisfies ExperimentArchiveResponse;

const props = { archive } satisfies ComponentProps<typeof ExperimentArchiveDashboard>;

void props;
void stageLabels.dataAnalysis;
void statusLabels.needsReview;
