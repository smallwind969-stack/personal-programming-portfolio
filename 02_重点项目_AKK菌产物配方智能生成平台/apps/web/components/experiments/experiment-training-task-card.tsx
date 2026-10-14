"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { createExperimentTrainingTask } from "@/lib/api";
import { ExperimentTrainingTaskPreview } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

export function ExperimentTrainingTaskCard({
  experimentId,
  task,
}: {
  experimentId: string;
  task: ExperimentTrainingTaskPreview;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState(
    task.status === "not_created" ? "尚未创建训练任务。" : `当前任务：${task.taskId}`,
  );

  async function onCreateTask() {
    try {
      const created = await createExperimentTrainingTask(experimentId);
      setMessage(`已创建训练任务：${created.taskId}`);
      startTransition(() => router.refresh());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "训练任务创建失败。");
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>训练任务执行卡</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            将建模计划正式转成可追踪的协同任务，展示数据校验、模型拟合、报告解释三个阶段的状态流转。
          </p>
        </div>
        <Badge tone={resolveTone(task.status)}>{task.status}</Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <MiniMetric label="任务 ID" value={task.taskId || "-"} />
        <MiniMetric label="目标字段" value={task.planTargetField || "-"} />
        <MiniMetric label="推荐模型" value={task.recommendedModelType || "-"} />
        <MiniMetric label="指标数" value={task.evaluationMetrics.length.toString()} />
      </div>

      <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
        <div>数据快照：{task.snapshotId || "-"}</div>
        <div>评估指标：{task.evaluationMetrics.length > 0 ? task.evaluationMetrics.join(" / ") : "-"}</div>
        <div>创建时间：{task.createdAt || "-"}</div>
        <div>更新时间：{task.updatedAt || "-"}</div>
        <div>{message}</div>
      </div>

      <div className="mt-4 space-y-2">
        {task.agentStages.length > 0 ? (
          task.agentStages.map((stage) => (
            <div
              key={`${stage.agentName}-${stage.stageLabel}`}
              className="rounded-lg border border-slate-200 bg-white p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-semibold text-slate-950">
                  {stage.agentName} · {stage.stageLabel}
                </div>
                <Badge tone={resolveTone(stage.status)}>{stage.status}</Badge>
              </div>
              <div className="mt-1 text-xs leading-5 text-slate-600">{stage.detail}</div>
            </div>
          ))
        ) : (
          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
            创建训练任务后，这里会展示各环节的执行阶段。
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={isPending} onClick={onCreateTask}>
          {isPending ? "创建中..." : "创建 / 刷新训练任务"}
        </Button>
        <span className="text-xs text-muted-foreground">
          当前为演示版状态推进，后续可替换为你本地 LLM 与真实训练 worker。
        </span>
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

function resolveTone(status: string): "success" | "warning" | "default" {
  if (status === "completed") return "success";
  if (status === "running" || status === "queued") return "warning";
  return "default";
}
