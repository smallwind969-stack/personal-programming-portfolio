import { ButtonLink } from "@/components/ui/button";
import { DataTable, Td, Th } from "@/components/ui/table";
import { formatApplication, formatCategory } from "@/lib/display";
import { AkkProduct } from "@/lib/schemas";
import { EvidenceBadge, RiskBadge } from "./product-badges";

export function ProductTable({ products }: { products: AkkProduct[] }) {
  return (
    <DataTable>
      <thead>
        <tr>
          <Th>产物名称</Th>
          <Th>产物形态</Th>
          <Th>主要功能</Th>
          <Th>应用适配性</Th>
          <Th>证据等级</Th>
          <Th>风险等级</Th>
          <Th>操作</Th>
        </tr>
      </thead>
      <tbody>
        {products.map((product) => (
          <tr key={product.productId}>
            <Td>
              <div className="font-medium text-slate-950">{product.productName}</div>
              <div className="mt-1 text-xs text-muted-foreground">原料档案</div>
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
                {product.recommendedApplications.map((application) => (
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
