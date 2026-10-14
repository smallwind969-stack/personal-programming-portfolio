import { ExperimentSimulationInputSummary } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";

export function ExperimentSimulationInputCard({
  simulation,
}: {
  simulation: ExperimentSimulationInputSummary;
}) {
  const ready = simulation.status !== "not_ready";

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>仿真输入 / 条件调参卡</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            将研发建议进一步转成可用于仿真模拟的输入对象，展示推荐区间、候选方案和仍需人工确认的参数。
          </p>
        </div>
        <Badge tone={ready ? "success" : "warning"}>{simulation.status}</Badge>
      </div>

      <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
        <div className="text-sm font-semibold text-slate-950">
          目标字段：{simulation.targetField || "尚未生成仿真输入"}
        </div>
        <div>目标说明：{simulation.objective || "-"}</div>
        <div>生成时间：{simulation.generatedAt || "-"}</div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {Object.entries(simulation.recommendedRanges).map(([field, range]) => (
          <div key={field} className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold text-slate-950">{field}</div>
            <div className="mt-2 text-xs leading-5 text-slate-700">
              {range.min} - {range.max} {range.unit}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-3">
        {simulation.candidatePlans.map((plan) => (
          <div key={plan.planName} className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-sm font-semibold text-slate-950">{plan.planName}</div>
            <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
              <div>温度：{plan.temperatureC} ℃</div>
              <div>pH：{plan.ph}</div>
              <div>时长：{plan.durationHours} h</div>
              <div>原因：{plan.reason}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold text-slate-950">人工确认参数</div>
        <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
          {simulation.manualConfirmationItems.length > 0
            ? simulation.manualConfirmationItems.map((item) => <div key={item}>- {item}</div>)
            : "当前暂无人工确认参数。"}
        </div>
      </div>
    </Card>
  );
}
