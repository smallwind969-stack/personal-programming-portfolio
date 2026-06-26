import { FormulaDesignWorkbench } from "@/components/formula/formula-design-workbench";
import { getAkkProducts, getLlmStatus } from "@/lib/api";

export default async function NewFormulaPage() {
  const [products, llmStatus] = await Promise.all([
    getAkkProducts(),
    getLlmStatus().catch(() => undefined),
  ]);
  return <FormulaDesignWorkbench llmStatus={llmStatus} products={products} />;
}
