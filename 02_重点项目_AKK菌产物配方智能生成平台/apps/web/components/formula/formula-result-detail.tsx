import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";
import { formatPriority, formatRisk } from "@/lib/display";
import { AkkProduct, FormulaResult } from "@/lib/schemas";

export function FormulaResultDetail({
  products,
  result,
}: {
  products: AkkProduct[];
  result: FormulaResult;
}) {
  const candidate = result.candidates[0];
  const highRiskCount = candidate.riskItems.filter((risk) => risk.riskLevel === "high").length;
  const requiredMetricCount = candidate.validationMetrics.filter((metric) => metric.priority === "required").length;
  const reviewLabel = highRiskCount > 0 ? "建议复测后再推进" : candidate.confidenceScore >= 0.7 ? "可进入下一轮小试" : "待补充验证";

  return (
    <div className="space-y-4 text-[13px]">
      <section className="rounded-lg border border-emerald-100 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-100 px-5 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <ButtonLink href="/" variant="secondary">返回设计台</ButtonLink>
            <ButtonLink href="/formula/results" variant="secondary">查看方案库</ButtonLink>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone={highRiskCount > 0 ? "warning" : "success"}>{reviewLabel}</Badge>
            <Badge tone="success">内部研发建议</Badge>
            <Badge>Research use only</Badge>
          </div>
        </div>

        <div className="grid gap-5 px-5 py-4 xl:grid-cols-[1fr_380px]">
          <div>
            <div className="text-xs font-medium text-emerald-700">AKK 商品方案建议书</div>
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">{candidate.candidateName}</h1>
            <p className="mt-2 max-w-4xl leading-6 text-muted-foreground">
              面向下游品牌的商品概念、AKK 原料组合、知识库引用、预测风险和实验验证计划。
              当前结果只作为打样和研发沟通起点，不作为可直接上市的最终食品配方。
            </p>
            <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-900">
              审核建议：{reviewLabel}。请结合实验平台中的稳定性、感官、成本和关键标志物数据进行下一轮判断。
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <SummaryMetric label="原料数" value={`${candidate.composition.length}`} />
            <SummaryMetric label="高风险" value={`${highRiskCount}`} tone={highRiskCount > 0 ? "warning" : "success"} />
            <SummaryMetric label="必测项" value={`${requiredMetricCount}`} />
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Card>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>推荐配比</CardTitle>
            <Badge>合计 {totalRatio(candidate.composition).toFixed(0)}%</Badge>
          </div>
          <FormulaDonut composition={candidate.composition} />
          <div className="mt-4 space-y-2">
            {candidate.composition.map((ingredient, index) => (
              <div className="flex items-center justify-between gap-3" key={ingredient.productId}>
                <div className="flex min-w-0 items-center gap-2">
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${donutColors[index % donutColors.length].dot}`} />
                  <span className="truncate text-slate-700">{ingredient.productName}</span>
                </div>
                <span className="font-semibold text-slate-950">{ingredient.ratioPercent}%</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>方案判断</CardTitle>
              <p className="mt-2 leading-6 text-muted-foreground">
                {candidate.predictions[0]?.explanation ?? "当前 AKK 原料组合适合作为商品概念打样起点。"}
              </p>
            </div>
            <Badge tone="success">置信度 {(candidate.confidenceScore * 100).toFixed(0)}%</Badge>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {candidate.predictions.map((prediction) => (
              <div className="rounded-lg border border-border bg-slate-50 p-3" key={prediction.predictionId}>
                <div className="text-xs text-muted-foreground">{prediction.targetName}</div>
                <div className="mt-1 text-lg font-semibold text-slate-950">{prediction.predictedValue}</div>
                <div className="mt-1 text-xs text-slate-500">置信度 {(prediction.confidenceScore * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-lg bg-emerald-50 p-3">
            <div className="text-xs font-semibold text-emerald-800">产品优势总结</div>
            <ul className="mt-2 space-y-1.5 leading-6 text-slate-700">
              {candidate.productAdvantages.slice(0, 4).map((advantage) => (
                <li key={advantage}>· {advantage}</li>
              ))}
            </ul>
          </div>
        </Card>
      </section>

      <Card>
        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div>
            <CardTitle>为什么采用这个配比</CardTitle>
            <div className="mt-3 space-y-3">
              {candidate.composition.map((ingredient) => {
                const product = products.find((item) => item.productId === ingredient.productId);
                return (
                  <div className="rounded-lg border border-border bg-slate-50 p-3" key={ingredient.productId}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-slate-950">{ingredient.productName}</div>
                      <Badge>{ingredient.ratioPercent}%</Badge>
                    </div>
                    <p className="mt-2 leading-6 text-slate-700">{buildRatioReason(ingredient.ratioPercent)}</p>
                    {product ? (
                      <div className="mt-2 text-xs text-slate-600">
                        原料风险：{formatRisk(product.riskLevel)}；证据等级：{product.evidenceLevel}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <CardTitle>知识库引用依据</CardTitle>
            <div className="mt-3 space-y-3">
              {candidate.knowledgeReferences.slice(0, 5).map((reference) => (
                <div className="rounded-lg border border-border bg-white p-3" key={reference.knowledgeId}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-slate-950">{reference.title}</div>
                    <Badge>证据 {reference.evidenceLevel}</Badge>
                  </div>
                  <p className="mt-2 leading-6 text-slate-700">{reference.relevanceReason}</p>
                  {reference.keyPassages.length ? (
                    <div className="mt-2 rounded-md bg-emerald-50 p-2 text-xs leading-5 text-slate-700">
                      {reference.keyPassages[0]}
                    </div>
                  ) : null}
                  <div className="mt-2 text-xs text-muted-foreground">
                    检索得分：{reference.retrievalScore?.toFixed(1) ?? "-"}。引用用途：解释 AKK 原料适配性、安全边界或食品基质风险。
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardTitle>协同辅料建议</CardTitle>
          <div className="mt-3">
            <DataTable>
              <thead>
                <tr>
                  <Th>辅料</Th>
                  <Th>建议用量</Th>
                  <Th>加入理由</Th>
                  <Th>注意点</Th>
                </tr>
              </thead>
              <tbody>
                {candidate.companionIngredients.slice(0, 4).map((ingredient) => (
                  <tr key={ingredient.ingredientId}>
                    <Td>
                      <div className="font-medium text-slate-950">{ingredient.ingredientName}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{ingredient.category}</div>
                    </Td>
                    <Td>{ingredient.suggestedUsage}</Td>
                    <Td>{ingredient.purpose}</Td>
                    <Td>{ingredient.riskNote}</Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          </div>
        </Card>

        <Card>
          <CardTitle>风险与验证计划</CardTitle>
          <div className="mt-3">
            <DataTable>
              <thead>
                <tr>
                  <Th>风险/指标</Th>
                  <Th>等级</Th>
                  <Th>验证方式</Th>
                </tr>
              </thead>
              <tbody>
                {candidate.riskItems.slice(0, 3).map((risk) => (
                  <tr key={risk.riskId}>
                    <Td>
                      <div className="font-medium text-slate-950">{risk.riskName}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{risk.description}</div>
                    </Td>
                    <Td><Badge tone={risk.riskLevel === "high" ? "danger" : "warning"}>{formatRisk(risk.riskLevel)}</Badge></Td>
                    <Td>{risk.mitigationSuggestion}</Td>
                  </tr>
                ))}
                {candidate.validationMetrics.slice(0, 4).map((metric) => (
                  <tr key={metric.metricId}>
                    <Td>
                      <div className="font-medium text-slate-950">{metric.metricName}</div>
                      <div className="mt-1 text-xs text-muted-foreground">目标：{metric.expectedRange}</div>
                    </Td>
                    <Td><Badge>{formatPriority(metric.priority)}</Badge></Td>
                    <Td>{metric.methodSuggestion}</Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          </div>
        </Card>
      </section>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>下一步动作</CardTitle>
          <ButtonLink href="/" variant="primary">继续设计新方案</ButtonLink>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <CompactList title="打样动作" items={candidate.experimentSuggestions.slice(0, 4)} />
          <CompactList title="升级建议" items={candidate.upgradeSuggestions.slice(0, 4)} />
        </div>
      </Card>
    </div>
  );
}

const donutColors = [
  { dot: "bg-emerald-600", ring: "#047857" },
  { dot: "bg-cyan-600", ring: "#0891b2" },
  { dot: "bg-amber-500", ring: "#f59e0b" },
  { dot: "bg-slate-500", ring: "#64748b" },
];

function FormulaDonut({ composition }: { composition: { productName: string; ratioPercent: number }[] }) {
  let start = 0;
  const total = totalRatio(composition) || 100;
  const gradient = composition
    .map((ingredient, index) => {
      const end = start + (ingredient.ratioPercent / total) * 100;
      const color = donutColors[index % donutColors.length].ring;
      const slice = `${color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
      start = end;
      return slice;
    })
    .join(", ");

  return (
    <div className="mx-auto mt-4 grid h-44 w-44 place-items-center rounded-full" style={{ background: `conic-gradient(${gradient})` }}>
      <div className="grid h-24 w-24 place-items-center rounded-full bg-white text-center shadow-inner">
        <div>
          <div className="text-xl font-semibold text-slate-950">{total.toFixed(0)}%</div>
          <div className="text-xs text-muted-foreground">AKK 配比</div>
        </div>
      </div>
    </div>
  );
}

function SummaryMetric({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "success" | "warning" }) {
  const toneClass = {
    default: "border-slate-200 bg-slate-50 text-slate-700",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
  };
  return (
    <div className={`rounded-lg border p-3 ${toneClass[tone]}`}>
      <div className="text-xs">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function CompactList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-border bg-slate-50 p-3">
      <div className="font-semibold text-slate-950">{title}</div>
      <ul className="mt-2 space-y-1.5 leading-6 text-slate-700">
        {items.map((item) => (
          <li key={item}>· {item}</li>
        ))}
      </ul>
    </div>
  );
}

function buildRatioReason(ratioPercent: number) {
  if (ratioPercent >= 50) {
    return "作为主导 AKK 原料使用，用于形成商品核心卖点；该比例适合作为首轮小试起点，后续根据感官和稳定性调整。";
  }
  if (ratioPercent >= 20) {
    return "作为功能强化组分使用，用于补足主原料在口感、稳定性或功能概念上的表达，适合做 A/B 梯度比较。";
  }
  return "作为辅助修饰组分使用，重点观察其对质构、复水、风味或成本的影响，避免过量带来感官和稳定性风险。";
}

function totalRatio(composition: { ratioPercent: number }[]) {
  return composition.reduce((sum, ingredient) => sum + ingredient.ratioPercent, 0);
}
