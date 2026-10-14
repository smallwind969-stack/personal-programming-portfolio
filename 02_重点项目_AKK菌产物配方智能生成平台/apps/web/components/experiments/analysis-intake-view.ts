import type { DataCollectionLocalizationRun } from "@/lib/schemas";

export function analysisIntakeView(run: null): "waitingForFile";
export function analysisIntakeView(run: DataCollectionLocalizationRun): "reviewEvidence";
export function analysisIntakeView(run: DataCollectionLocalizationRun | null): "waitingForFile" | "reviewEvidence";
export function analysisIntakeView(run: DataCollectionLocalizationRun | null) {
  return run === null ? "waitingForFile" as const : "reviewEvidence" as const;
}
