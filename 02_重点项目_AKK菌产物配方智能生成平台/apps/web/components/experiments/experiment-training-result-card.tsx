import { ExperimentTrainingResultSummary } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";

export function ExperimentTrainingResultCard({
  result,
}: {
  result: ExperimentTrainingResultSummary;
}) {
  const hasResult = result.status !== "not_ready";

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>训练结果摘要卡</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            展示训练完成后的关键指标、置信度、主要风险和研发建议，作为后续报告生成与人工复核的解释入口。
          </p>
        </div>
        <Badge tone={hasResult ? "success" : "warning"}>{result.status}</Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <MiniMetric label="目标字段" value={result.targetField || "-"} />
        <MiniMetric label="置信度" value={result.confidenceLevel || "-"} />
        <MiniMetric label="MAE" value={result.metrics.mae.toFixed(2)} />
        <MiniMetric label="R²" value={result.metrics.r2.toFixed(2)} />
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          <div>任务 ID：{result.taskId || "-"}</div>
          <div>RMSE：{result.metrics.rmse.toFixed(2)}</div>
          <div>生成时间：{result.generatedAt || "-"}</div>
        </div>

        <div className="rounded-lg bg-slate-50 p-3">
          <div className="text-xs font-semibold text-slate-950">主要风险</div>
          <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
            {result.riskNotes.length > 0
              ? result.riskNotes.map((note) => <div key={note}>- {note}</div>)
              : "当前暂无风险说明。"}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="text-xs font-semibold text-slate-950">研发建议</div>
          <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
            {result.recommendations.length > 0
              ? result.recommendations.map((item) => <div key={item}>- {item}</div>)
              : "当前暂无研发建议。"}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="text-xs font-semibold text-slate-950">人工复核项</div>
          <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
            {result.manualReviewItems.length > 0
              ? result.manualReviewItems.map((item) => <div key={item}>- {item}</div>)
              : "当前暂无人工复核项。"}
          </div>
        </div>
      </div>
    </Card>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-950">{value}</div>
    </div>
  );
}
