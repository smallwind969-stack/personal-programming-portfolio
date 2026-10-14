import { ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";
import { formatApplication, formatCategory, getProductRole } from "@/lib/display";
import { AkkProduct } from "@/lib/schemas";
import { EvidenceBadge, RiskBadge } from "./product-badges";

const roleOrder = ["AKK 功能产物", "论文底物与对照组", "食品基质与加工场景", "包埋与样品原型", "其他研发对象"];

function groupProducts(products: AkkProduct[]) {
  return roleOrder
    .map((role) => ({
      role,
      products: products.filter((product) => getProductRole(product.productCategory) === role),
    }))
    .filter((group) => group.products.length > 0);
}

function StatCard({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <Card className="shadow-none">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
      <div className="mt-1 text-xs leading-5 text-muted-foreground">{helper}</div>
    </Card>
  );
}

export function ProductLibrary({ products }: { products: AkkProduct[] }) {
  const evidenceA = products.filter((product) => product.evidenceLevel === "A").length;
  const evidenceB = products.filter((product) => product.evidenceLevel === "B").length;
  const highRisk = products.filter((product) => product.riskLevel === "high").length;
  const groups = groupProducts(products);

  return (
    <div className="space-y-6">
      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="研发对象总数" value={`${products.length} 个`} helper="由论文、专利和内部 mock 档案整理。" />
        <StatCard label="高证据对象" value={`${evidenceA + evidenceB} 个`} helper={`A级 ${evidenceA} 个，B级 ${evidenceB} 个。`} />
        <StatCard label="高风险对象" value={`${highRisk} 个`} helper="需要优先做安全、稳定性和边界验证。" />
        <StatCard label="分层模块" value={`${groups.length} 类`} helper="按产物、底物、基质和原型分组展示。" />
      </div>

      <div className="space-y-5">
        {groups.map((group) => (
          <section className="space-y-3" key={group.role}>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">{group.role}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {group.products.length} 个对象，建议在方案生成时结合证据等级、风险等级和验证指标共同判断。
                </p>
              </div>
            </div>
            <ProductTable products={group.products} />
          </section>
        ))}
      </div>
    </div>
  );
}

export function ProductTable({ products }: { products: AkkProduct[] }) {
  return (
    <DataTable>
      <thead>
        <tr>
          <Th>对象名称</Th>
          <Th>研发类型</Th>
          <Th>核心依据</Th>
          <Th>适配场景</Th>
          <Th>证据</Th>
          <Th>风险</Th>
          <Th>操作</Th>
        </tr>
      </thead>
      <tbody>
        {products.map((product) => (
          <tr key={product.productId}>
            <Td>
              <div className="font-medium text-slate-950">{product.productName}</div>
              <div className="mt-1 text-xs text-muted-foreground">{product.productId}</div>
            </Td>
            <Td>{formatCategory(product.productCategory)}</Td>
            <Td>
              <div className="space-y-1">
                {product.functionalAssumptions.slice(0, 2).map((item) => (
                  <div key={item}>{item}</div>
                ))}
              </div>
            </Td>
            <Td>
              <div className="flex flex-wrap gap-2">
                {product.recommendedApplications.slice(0, 4).map((application) => (
                  <span className="rounded-md bg-muted px-2 py-1 text-xs" key={application}>
                    {formatApplication(application)}
                  </span>
                ))}
              </div>
            </Td>
            <Td><EvidenceBadge evidenceLevel={product.evidenceLevel} /></Td>
            <Td><RiskBadge riskLevel={product.riskLevel} /></Td>
            <Td><ButtonLink href={`/products/${product.productId}`} variant="secondary">查看详情</ButtonLink></Td>
          </tr>
        ))}
      </tbody>
    </DataTable>
  );
}
