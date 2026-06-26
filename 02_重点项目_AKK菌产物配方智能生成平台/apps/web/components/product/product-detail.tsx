import { ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { formatApplication, formatCategory } from "@/lib/display";
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
    return text.includes("稳定") || text.includes("溶") || text.includes("分散") || text.includes("黏度") || text.includes("viscosity");
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950">{product.productName}</h1>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">{product.description}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-md border border-border bg-white px-2 py-1 text-xs">
              {formatCategory(product.productCategory)}
            </span>
            <EvidenceBadge evidenceLevel={product.evidenceLevel} />
            <RiskBadge riskLevel={product.riskLevel} />
          </div>
        </div>
        <ButtonLink href="/">进入商品设计台</ButtonLink>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardTitle>基础信息</CardTitle>
          <dl className="mt-4 grid gap-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-border pb-2">
              <dt className="text-muted-foreground">原料编号</dt>
              <dd className="font-medium">{product.productId}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-border pb-2">
              <dt className="text-muted-foreground">原料形态</dt>
              <dd className="font-medium">{formatCategory(product.productCategory)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">资料来源</dt>
              <dd className="font-medium">研发资料库</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardTitle>功能性质</CardTitle>
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
          <CardTitle>应用适配性</CardTitle>
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
          <CardTitle>稳定性概况</CardTitle>
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
          <CardTitle>安全与合规提示</CardTitle>
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
                <div className="font-medium">{metric.metricName}</div>
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
