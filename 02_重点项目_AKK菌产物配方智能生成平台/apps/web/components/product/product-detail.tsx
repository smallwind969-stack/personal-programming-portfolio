import { ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { formatApplication, formatCategory, formatPriority, getProductRole } from "@/lib/display";
import { AkkProduct } from "@/lib/schemas";
import { EvidenceBadge, RiskBadge } from "./product-badges";

function BulletList({ items }: { items: string[] }) {
  return (
    <div className="space-y-2 text-sm leading-6 text-slate-700">
      {items.map((item) => (
        <div className="rounded-md border border-border bg-white px-3 py-2" key={item}>{item}</div>
      ))}
    </div>
  );
}

export function ProductDetail({ product }: { product: AkkProduct }) {
  const stabilityItems = product.keyProperties.filter((property) => {
    const text = `${property.propertyName} ${property.propertyId}`.toLowerCase();
    return text.includes("稳定") || text.includes("溶解") || text.includes("分散") || text.includes("黏度") || text.includes("viscosity") || text.includes("gel");
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-primary">内部研发实验建议</p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-950">{product.productName}</h1>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">{product.description}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-md border border-border bg-white px-2 py-1 text-xs">
              {getProductRole(product.productCategory)}
            </span>
            <span className="rounded-md border border-border bg-white px-2 py-1 text-xs">
              {formatCategory(product.productCategory)}
            </span>
            <EvidenceBadge evidenceLevel={product.evidenceLevel} />
            <RiskBadge riskLevel={product.riskLevel} />
          </div>
        </div>
        <ButtonLink href="/formula/new">进入配方生成</ButtonLink>
      </div>

      <Card className="border-emerald-200 bg-emerald-50 shadow-none">
        <CardTitle>研发边界</CardTitle>
        <p className="mt-2 text-sm leading-6 text-emerald-950">
          本页面只用于内部研发评估。系统给出的用途、浓度窗口、风险和验证指标不能直接作为上市配方或生产指令，
          需要经过小试、中试、检测复核和人工审核后才能进入下一阶段。
        </p>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardTitle>基础档案</CardTitle>
          <dl className="mt-4 grid gap-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-border pb-2">
              <dt className="text-muted-foreground">对象编号</dt>
              <dd className="font-medium">{product.productId}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-border pb-2">
              <dt className="text-muted-foreground">研发类型</dt>
              <dd className="font-medium">{formatCategory(product.productCategory)}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-border pb-2">
              <dt className="text-muted-foreground">研发角色</dt>
              <dd className="font-medium">{getProductRole(product.productCategory)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">资料来源</dt>
              <dd className="font-medium">论文、专利与内部 mock 档案</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardTitle>关键性质</CardTitle>
          <div className="mt-4 space-y-3">
            {product.keyProperties.map((property) => (
              <div className="rounded-md border border-border p-3" key={property.propertyId}>
                <div className="font-medium">{property.propertyName}: {property.propertyValue}</div>
                <p className="mt-1 text-sm text-muted-foreground">{property.description}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>模型假设与适配场景</CardTitle>
          <div className="mt-4 flex flex-wrap gap-2">
            {product.recommendedApplications.map((application) => (
              <span className="rounded-md bg-muted px-2 py-1 text-sm" key={application}>
                {formatApplication(application)}
              </span>
            ))}
          </div>
          <div className="mt-4">
            <BulletList items={product.functionalAssumptions} />
          </div>
        </Card>

        <Card>
          <CardTitle>稳定性与工艺关注点</CardTitle>
          <div className="mt-4 space-y-3">
            {(stabilityItems.length ? stabilityItems : product.keyProperties).map((property) => (
              <div className="rounded-md border border-border p-3" key={property.propertyId}>
                <div className="font-medium">{property.propertyName}</div>
                <div className="mt-1 text-sm text-muted-foreground">{property.propertyValue}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>风险与限制</CardTitle>
          <div className="mt-4">
            <BulletList items={product.constraints} />
          </div>
          <div className="mt-4 space-y-3">
            {product.riskItems.map((risk) => (
              <div className="rounded-md border border-border p-3" key={risk.riskId}>
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium">{risk.riskName}</div>
                  <RiskBadge riskLevel={risk.riskLevel} />
                </div>
                <p className="mt-1 text-sm text-slate-700">{risk.description}</p>
                <p className="mt-1 text-sm text-muted-foreground">{risk.mitigationSuggestion}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>证据与验证指标</CardTitle>
          <div className="mt-4 flex gap-2">
            <EvidenceBadge evidenceLevel={product.evidenceLevel} />
            <RiskBadge riskLevel={product.riskLevel} />
          </div>
          <div className="mt-4 space-y-3">
            {product.validationMetrics.map((metric) => (
              <div className="rounded-md border border-border p-3" key={metric.metricId}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-medium">{metric.metricName}</div>
                  <span className="rounded-md bg-muted px-2 py-1 text-xs">{formatPriority(metric.priority)}</span>
                </div>
                <p className="mt-1 text-sm text-slate-700">{metric.methodSuggestion}</p>
                <p className="mt-1 text-sm text-muted-foreground">{metric.expectedRange}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
