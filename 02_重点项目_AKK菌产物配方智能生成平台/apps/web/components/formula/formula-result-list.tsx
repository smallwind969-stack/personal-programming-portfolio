import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { formatApplication } from "@/lib/display";
import { FormulaResult } from "@/lib/schemas";

export function FormulaResultList({ results }: { results: FormulaResult[] }) {
  if (!results.length) {
    return (
      <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
        <div className="text-base font-semibold text-slate-950">还没有商品方案</div>
        <p className="mt-2 text-sm text-muted-foreground">先回到商品设计台，输入目标商品类型并生成第一份方案。</p>
        <div className="mt-4">
          <ButtonLink href="/" variant="primary">去设计方案</ButtonLink>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result) => {
        const candidate = result.candidates[0];
        const highRiskCount = candidate.riskItems.filter((risk) => risk.riskLevel === "high").length;
        const requiredTests = candidate.validationMetrics.filter((metric) => metric.priority === "required").length;
        const reviewTone = highRiskCount > 0 ? "warning" : candidate.confidenceScore >= 0.7 ? "success" : "default";
        const reviewLabel = highRiskCount > 0 ? "建议复测" : candidate.confidenceScore >= 0.7 ? "可推进小试" : "待验证";
        const companionSummary = candidate.companionIngredients.slice(0, 3).map((item) => item.ingredientName).join(" / ");
        const ratioSummary = candidate.composition
          .map((item) => `${item.productName} ${item.ratioPercent}%`)
          .join(" / ");

        return (
          <article className="rounded-lg border border-border bg-white p-4 shadow-sm" key={result.resultId}>
            <div className="grid gap-4 xl:grid-cols-[1.05fr_1.35fr_0.85fr_auto] xl:items-center">
              <div>
                <div className="text-base font-semibold text-slate-950">{candidate.candidateName}</div>
                <div className="mt-1 text-xs text-muted-foreground">{result.resultId}</div>
              </div>

              <div>
                <div className="text-xs text-muted-foreground">配方组成</div>
                <div className="mt-1 text-sm leading-5 text-slate-800">{ratioSummary}</div>
                {companionSummary ? (
                  <div className="mt-1 text-xs leading-5 text-muted-foreground">融合辅料：{companionSummary}</div>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge>{formatApplication(result.applicationName)}</Badge>
                <Badge tone={highRiskCount ? "warning" : "success"}>高风险 {highRiskCount}</Badge>
                <Badge>必测 {requiredTests}</Badge>
                <Badge tone={reviewTone}>{reviewLabel}</Badge>
              </div>

              <div className="flex items-center gap-3 xl:justify-end">
                <div className="text-right text-xs text-muted-foreground">
                  {new Date(result.createdAt).toLocaleString("zh-CN", { hour12: false })}
                </div>
                <ButtonLink href={`/formula/results/${encodeURIComponent(result.resultId)}`} variant="secondary">
                  查看方案
                </ButtonLink>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
