import type { ProductInnovationInput, ProductInnovationRun, ProductRequirementVersion } from "@/lib/schemas";
import { confirmProductRequirement, createProductInnovationRun, getLatestProductRequirementVersion, getProductInnovationRun } from "@/lib/api";
import { ProductInnovationWorkbench } from "@/components/experiments/product-innovation-workbench";

declare const input: ProductInnovationInput;
declare const run: ProductInnovationRun;
input.brief satisfies string;
run.materialRoles[0].purpose satisfies string;
run.requiresHumanReview satisfies boolean;
createProductInnovationRun satisfies (experimentId: string, commandId: string, input: ProductInnovationInput) => Promise<ProductInnovationRun>;
getProductInnovationRun satisfies (experimentId: string, runId: string) => Promise<ProductInnovationRun>;
confirmProductRequirement satisfies (experimentId: string, runId: string, commandId: string, operator: string, reason: string) => Promise<ProductRequirementVersion>;
getLatestProductRequirementVersion satisfies (experimentId: string) => Promise<ProductRequirementVersion>;
void ProductInnovationWorkbench;
