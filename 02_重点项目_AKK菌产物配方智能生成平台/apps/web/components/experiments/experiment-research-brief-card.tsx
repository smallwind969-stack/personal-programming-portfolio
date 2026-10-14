import { ExperimentResearchBriefSummary } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";

export function ExperimentResearchBriefCard({
  brief,
}: {
  brief: ExperimentResearchBriefSummary;
}) {
  const ready = brief.status !== "not_ready";

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>研发建议书摘要卡</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            将训练结果整理为面向研发汇报的摘要对象，串联目标、数据结论、模型结论、风险与下一步动作。
          </p>
        </div>
        <Badge tone={ready ? "success" : "warning"}>{brief.status}</Badge>
      </div>

      <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
        <div className="text-sm font-semibold text-slate-950">{brief.title || "尚未生成摘要"}</div>
        <div>任务 ID：{brief.taskId || "-"}</div>
        <div>生成时间：{brief.generatedAt || "-"}</div>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        <Block title="项目目标" body={brief.objective} />
        <Block title="数据结论" body={brief.dataSummary} />
        <Block title="模型结论" body={brief.modelSummary} />
        <Block title="风险与限制" body={brief.riskSummary} />
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        <ListBlock title="下一步动作" items={brief.nextActions} empty="当前暂无下一步动作。" />
        <ListBlock
          title="人工确认事项"
          items={brief.manualConfirmationItems}
          empty="当前暂无人工确认事项。"
        />
      </div>
    </Card>
  );
}

function Block({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold text-slate-950">{title}</div>
      <div className="mt-2 text-xs leading-5 text-slate-700">{body || "-"}</div>
    </div>
  );
}

function ListBlock({
  title,
  items,
  empty,
}: {
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold text-slate-950">{title}</div>
      <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
        {items.length > 0 ? items.map((item) => <div key={item}>- {item}</div>) : empty}
      </div>
    </div>
  );
}
