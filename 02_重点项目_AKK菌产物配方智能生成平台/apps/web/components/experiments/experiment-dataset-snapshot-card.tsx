"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { createExperimentDatasetSnapshot } from "@/lib/api";
import type { ExperimentDatasetSnapshot } from "@/lib/schemas";

export function ExperimentDatasetSnapshotCard({
  experimentId,
  snapshot,
  canCreate = true,
  blockedReason,
}: {
  experimentId: string;
  snapshot: ExperimentDatasetSnapshot;
  canCreate?: boolean;
  blockedReason?: string;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState(
    snapshot.status === "modeling_ready"
      ? `最新快照：${snapshot.snapshotId}`
      : "尚未创建数据集快照。",
  );

  async function onCreateSnapshot() {
    try {
      const created = await createExperimentDatasetSnapshot(experimentId);
      setMessage(`已创建建模数据集快照：${created.snapshotId}`);
      startTransition(() => router.refresh());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "数据集快照创建失败。");
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>建模数据集快照</CardTitle>
          <p className="mt-1 text-xs leading-6 text-muted-foreground">
            将已确认的数据、字段映射和清洗对齐结果锁定为可追溯版本，供训练、仿真和报告复现。
          </p>
        </div>
        <Badge tone={snapshot.status === "modeling_ready" ? "success" : "warning"}>
          {snapshot.status === "modeling_ready" ? "可用于建模" : "尚未创建"}
        </Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-6">
        <MiniMetric label="建模文件" value={snapshot.assetCount.toString()} />
        <MiniMetric label="来源证据" value={snapshot.evidenceAssetCount.toString()} />
        <MiniMetric label="字段映射" value={snapshot.mappingCount.toString()} />
        <MiniMetric label="对齐行数" value={snapshot.alignedRowCount.toString()} />
        <MiniMetric label="特征数" value={snapshot.featureCount.toString()} />
        <MiniMetric label="异常数" value={snapshot.anomalyCount.toString()} />
      </div>

      <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
        <div>快照 ID：{snapshot.snapshotId || "-"}</div>
        <div>内容哈希：{snapshot.contentHash ? snapshot.contentHash.slice(0, 16) : "-"}</div>
        <div>清洗运行：{snapshot.cleaningRunId || "-"}</div>
        <div>清洗输出哈希：{snapshot.cleaningOutputHash?.slice(0, 16) || "-"}</div>
        <div>建模资产：{snapshot.analysisAssetIds.length ? snapshot.analysisAssetIds.join("、") : "-"}</div>
        <div>来源证据：{snapshot.sourceEvidenceAssetIds.length ? snapshot.sourceEvidenceAssetIds.join("、") : "-"}</div>
        <div>创建时间：{snapshot.createdAt || "-"}</div>
        <div>{message}</div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={isPending || !canCreate} onClick={onCreateSnapshot}>
          {isPending ? "创建中……" : "创建/刷新数据集快照"}
        </Button>
        <span className="text-xs text-muted-foreground">
          {canCreate ? "快照会锁定当前清洗结果，便于后续建模和实验复现。" : blockedReason}
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
