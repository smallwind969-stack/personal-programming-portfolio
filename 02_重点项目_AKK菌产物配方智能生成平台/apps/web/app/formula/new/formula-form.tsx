"use client";

import { FormulaDesignWorkbench } from "@/components/formula/formula-design-workbench";
import { AkkProduct } from "@/lib/schemas";

export function FormulaForm({
  products,
}: {
  initialProductId?: string;
  products: AkkProduct[];
}) {
  return <FormulaDesignWorkbench products={products} />;
}
