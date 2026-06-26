import { Card } from "@/components/ui/card";

export function DashboardMetrics({
  generatedFormulaCount,
  highRiskPlanCount,
  pendingValidationCount,
  productCount,
}: {
  generatedFormulaCount: number;
  highRiskPlanCount: number;
  pendingValidationCount: number;
  productCount: number;
}) {
  const metrics = [
    { label: "可用 AKK 产物", value: productCount },
    { label: "已生成配方", value: generatedFormulaCount },
    { label: "待验证方案", value: pendingValidationCount },
    { label: "中高风险方案", value: highRiskPlanCount },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <Card key={metric.label}>
          <div className="text-sm text-muted-foreground">{metric.label}</div>
          <div className="mt-3 text-3xl font-semibold text-slate-950">{metric.value}</div>
        </Card>
      ))}
    </div>
  );
}
