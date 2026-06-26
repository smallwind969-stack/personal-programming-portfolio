import { ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { formatApplication } from "@/lib/display";
import { FormulaResult } from "@/lib/schemas";

export function RecentFormulas({ results }: { results: FormulaResult[] }) {
  return (
    <Card>
      <div className="flex items-center justify-between gap-4">
        <CardTitle>最近配方档案</CardTitle>
        <ButtonLink href="/formula/results" variant="secondary">查看全部</ButtonLink>
      </div>
      <div className="mt-4 space-y-3">
        {results.length ? (
          results.slice(0, 5).map((result) => (
            <div className="flex items-center justify-between gap-4 rounded-md border border-border p-3" key={result.resultId}>
              <div>
                <div className="font-medium text-slate-950">{formatApplication(result.applicationName)}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {result.resultId} · {new Date(result.createdAt).toLocaleString()}
                </div>
              </div>
              <ButtonLink href={`/formula/results/${result.resultId}`} variant="secondary">打开</ButtonLink>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">暂无配方档案。</p>
        )}
      </div>
    </Card>
  );
}
