import { analysisIntakeView } from "@/components/experiments/analysis-intake-view";
import type { DataCollectionLocalizationRun } from "@/lib/schemas";

declare const run: DataCollectionLocalizationRun;

const noData: "waitingForFile" = analysisIntakeView(null);
const hasEvidence: "reviewEvidence" = analysisIntakeView(run);

void noData;
void hasEvidence;
