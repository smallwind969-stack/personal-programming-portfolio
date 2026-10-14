import type { SchemaRecognitionRun } from "@/lib/schemas";
import { createSchemaRecognitionRun, getSchemaRecognitionRun } from "@/lib/api";
import { SchemaRecognitionRunCard } from "@/components/experiments/schema-recognition-run-card";

declare const run: SchemaRecognitionRun;
run.mode satisfies "llm_assisted" | "rule_fallback" | "rule_only";
run.candidates[0].requiresHumanReview satisfies boolean;
run.conflictCount satisfies number;
createSchemaRecognitionRun satisfies (experimentId: string, commandId: string) => Promise<SchemaRecognitionRun>;
getSchemaRecognitionRun satisfies (experimentId: string, runId: string) => Promise<SchemaRecognitionRun>;
void SchemaRecognitionRunCard;
