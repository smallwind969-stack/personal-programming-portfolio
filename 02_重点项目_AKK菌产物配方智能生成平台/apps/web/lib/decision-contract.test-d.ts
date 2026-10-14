import type { z } from "zod";

import {
  decisionRequirementSchema,
  decisionTraceSchema,
} from "@/lib/decision-schema";

type Requirement = z.infer<typeof decisionRequirementSchema>;
type Trace = z.infer<typeof decisionTraceSchema>;

const requirement: Requirement = {
  productType: "功能性果冻",
  attributes: [],
  missingConstraints: [],
  confidence: 0.9,
};

declare const trace: Trace;
const objective:
  | "maximize_output"
  | "balanced"
  | "minimize_resource" = trace.plans[0].objective;

void requirement;
void objective;
