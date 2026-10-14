import { ExperimentModelingPlanPreview } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";

export function ExperimentModelingPlanCard({
  plan,
}: {
  plan: ExperimentModelingPlanPreview;
}) {
  const isReady = plan.status === "draft_ready";

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>建模任务预览</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            基于当前数据集快照自动生成演示版训练草案，明确目标字段、候选特征、评估指标与风险提示，
            让后续建模过程可解释、可追踪。
          </p>
        </div>
        <Badge tone={isReady ? "success" : "warning"}>
          {isReady ? "draft_ready" : "not_ready"}
        </Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <MiniMetric label="目标字段" value={plan.targetField || "-"} />
        <MiniMetric label="候选特征数" value={plan.candidateFeatures.length.toString()} />
        <MiniMetric label="训练集占比" value={`${Math.round(plan.trainSplitRatio * 100)}%`} />
        <MiniMetric label="验证集占比" value={`${Math.round(plan.validationSplitRatio * 100)}%`} />
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-[1fr_1fr]">
        <div className="rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          <div>快照 ID：{plan.snapshotId || "-"}</div>
          <div>推荐模型：{plan.recommendedModelType || "-"}</div>
          <div>候选特征：{plan.candidateFeatures.length > 0 ? plan.candidateFeatures.join(" / ") : "-"}</div>
          <div>评估指标：{plan.evaluationMetrics.join(" / ")}</div>
        </div>

        <div className="rounded-lg bg-slate-50 p-3">
          <div className="text-xs font-semibold text-slate-950">风险提示</div>
          <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
            {plan.riskHints.length > 0
              ? plan.riskHints.map((hint) => <div key={hint}>- {hint}</div>)
              : "当前没有额外风险提示。"}
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
