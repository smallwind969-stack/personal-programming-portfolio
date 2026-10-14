import type { ResultInterpretationRun } from "@/lib/schemas";
import { createResultInterpretationRun, getResultInterpretationRun } from "@/lib/api";
import { ResultInterpretationRunCard } from "@/components/experiments/result-interpretation-run-card";

declare const run: ResultInterpretationRun;
run.authoritativeMetrics.r2 satisfies number;
run.metricInterpretations[0].value satisfies number;
run.nextExperimentSuggestions[0].requiresHumanReview satisfies boolean;
createResultInterpretationRun satisfies (experimentId: string, commandId: string) => Promise<ResultInterpretationRun>;
getResultInterpretationRun satisfies (experimentId: string, runId: string) => Promise<ResultInterpretationRun>;
void ResultInterpretationRunCard;
