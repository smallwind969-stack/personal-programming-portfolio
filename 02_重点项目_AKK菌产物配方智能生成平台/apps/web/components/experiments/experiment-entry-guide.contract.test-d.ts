import type { ComponentProps } from "react";

import { ExperimentEntryGuide } from "@/components/experiments/experiment-entry-guide";
import type { DataCollectionLocalizationRun, ExperimentWorkspaceOverview } from "@/lib/schemas";

declare const overview: ExperimentWorkspaceOverview;
declare const intakeRun: DataCollectionLocalizationRun | null;

const props = { overview, intakeRun } satisfies ComponentProps<typeof ExperimentEntryGuide>;

void props;
