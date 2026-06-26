import { ProductTable } from "@/components/product/product-table";
import { getAkkProducts } from "@/lib/api";

export default async function ProductsPage() {
  const products = await getAkkProducts();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">AKK 原料库</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          汇总当前可用于商品方案设计的 AKK 相关产物、功能性质、应用适配性和风险信息。
        </p>
      </div>
      <ProductTable products={products} />
    </div>
  );
}
