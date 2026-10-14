import { ProductLibrary } from "@/components/product/product-table";
import { getAkkProducts } from "@/lib/api";

export default async function ProductsPage() {
  const products = await getAkkProducts();

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium text-primary">内部研发实验建议</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">AKK 产物与底物知识库</h1>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">
          汇总当前可用于产品方案探索、培养底物筛选、食品基质验证和包埋原型的小试对象。
          所有内容仅作为内部研发建议，正式生产前必须经过稳定性、安全性、感官和目标指标验证。
        </p>
      </div>
      <ProductLibrary products={products} />
    </div>
  );
}
