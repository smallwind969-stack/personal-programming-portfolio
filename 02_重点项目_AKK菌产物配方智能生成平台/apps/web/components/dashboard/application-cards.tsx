import { Card, CardTitle } from "@/components/ui/card";
import { formatApplication } from "@/lib/display";
import { AkkProduct } from "@/lib/schemas";

export function ApplicationCards({ products }: { products: AkkProduct[] }) {
  const applicationCounts = products
    .flatMap((product) => product.recommendedApplications)
    .reduce<Record<string, number>>((acc, application) => {
      acc[application] = (acc[application] ?? 0) + 1;
      return acc;
    }, {});

  return (
    <Card>
      <CardTitle>推荐应用方向</CardTitle>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {Object.entries(applicationCounts).map(([application, count]) => (
          <div className="rounded-md border border-border bg-[#fbfdfc] p-4" key={application}>
            <div className="text-sm font-semibold text-slate-950">{formatApplication(application)}</div>
            <div className="mt-2 text-xs text-muted-foreground">已有 {count} 个适配产物</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
