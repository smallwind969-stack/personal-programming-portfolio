import { FormulaResultList } from "@/components/formula/formula-result-list";
import { getFormulaResults } from "@/lib/api";

export default async function FormulaResultsPage() {
  const results = await getFormulaResults();

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs font-medium text-primary">客户项目归档</div>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">商品方案库</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          查看已生成的商品方案名称、AKK 原料组合、推荐比例、风险项和验证任务。
        </p>
      </div>
      <FormulaResultList results={results} />
    </div>
  );
}
