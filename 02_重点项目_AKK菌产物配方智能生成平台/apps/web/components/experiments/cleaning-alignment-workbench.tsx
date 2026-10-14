"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { createCleaningAlignmentRun, reviewCleaningAlignmentRun } from "@/lib/api";
import type { CleaningAlignmentRun } from "@/lib/schemas";

export function CleaningAlignmentWorkbench({
  experimentId,
  initialRun,
}: {
  experimentId: string;
  initialRun: CleaningAlignmentRun | null;
}) {
  const router = useRouter();
  const [run, setRun] = useState(initialRun);
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(
    initialRun ? "已恢复最近一次清洗对齐记录。" : "尚未执行数据清洗与时间轴对齐。",
  );

  async function create() {
    setBusy(true);
    setMessage("正在执行单位换算、时间规范化与多设备数据对齐……");
    try {
      const created = await createCleaningAlignmentRun(experimentId);
      setRun(created);
      setMessage(
        created.status === "needsReview"
          ? "发现数据质量问题，请复核后人工放行。"
          : "清洗对齐完成，输入指纹与输出哈希已锁定。",
      );
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "清洗对齐运行失败。");
    } finally {
      setBusy(false);
    }
  }

  async function review() {
    if (!run || reason.trim().length < 2) return;
    setBusy(true);
    try {
      const confirmed = await reviewCleaningAlignmentRun(
        experimentId,
        run.runId,
        operator,
        reason,
      );
      setRun(confirmed);
      setMessage("质量问题与人工判断已记录，现在可以创建建模数据集快照。");
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "人工复核提交失败。");
    } finally {
      setBusy(false);
    }
  }

  const qualityEntries = run
    ? [
        ["缺失值", run.quality.missingValueCount],
        ["无效数值", run.quality.invalidNumericCount],
        ["无效时间", run.quality.invalidTimestampCount],
        ["重复时间", run.quality.duplicateTimestampCount],
        ["未映射字段", run.quality.unmappedColumnCount],
      ]
    : [];

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>数据清洗与时间轴对齐</CardTitle>
          <p className="mt-1 max-w-3xl text-xs leading-6 text-muted-foreground">
            执行真实单位换算、时间格式统一和多设备数据合并；全过程保留公式、样例、输入指纹和输出哈希。
          </p>
        </div>
        <Badge tone={run?.status === "confirmed" || run?.status === "completed" ? "success" : "warning"}>
          {run?.status === "confirmed"
            ? "人工已放行"
            : run?.status === "completed"
              ? "自动检查通过"
              : run?.status === "needsReview"
                ? "等待人工复核"
                : "尚未运行"}
        </Badge>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={busy} onClick={create}>
          {busy ? "处理中……" : run ? "重新运行清洗对齐" : "开始清洗对齐"}
        </Button>
        <span className="text-xs text-muted-foreground">{message}</span>
      </div>

      {run ? (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {qualityEntries.map(([label, value]) => (
              <MiniMetric key={label} label={String(label)} value={String(value)} />
            ))}
          </div>

          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[760px] text-left text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-3 py-2">原字段</th>
                  <th className="px-3 py-2">标准字段</th>
                  <th className="px-3 py-2">单位</th>
                  <th className="px-3 py-2">换算公式</th>
                  <th className="px-3 py-2">换算前</th>
                  <th className="px-3 py-2">换算后</th>
                </tr>
              </thead>
              <tbody>
                {run.conversionEvidence.map((item, index) => (
                  <tr className="border-t border-slate-100" key={`${item.originalColumn}-${index}`}>
                    <td className="px-3 py-2">{item.originalColumn}</td>
                    <td className="px-3 py-2">{item.standardField}</td>
                    <td className="px-3 py-2">{item.sourceUnit || "-"} → {item.targetUnit || "-"}</td>
                    <td className="px-3 py-2 font-mono">{item.formula}</td>
                    <td className="px-3 py-2">{item.sampleBefore ?? "-"}</td>
                    <td className="px-3 py-2">{item.sampleAfter ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-6 text-slate-600">
            <div>运行 ID：{run.runId}</div>
            <div>输入指纹：{run.inputFingerprint}</div>
            <div>输出哈希：{run.outputHash}</div>
            <div>对齐结果：{run.alignedRowCount} 行</div>
          </div>

          {run.status === "needsReview" ? (
            <div className="mt-4 grid gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 md:grid-cols-[180px_1fr_auto]">
              <input
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
                onChange={(event) => setOperator(event.target.value)}
                value={operator}
              />
              <input
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
                onChange={(event) => setReason(event.target.value)}
                placeholder="填写人工判断依据（至少 2 个字）"
                value={reason}
              />
              <Button disabled={busy || reason.trim().length < 2} onClick={review}>
                记录依据并放行
              </Button>
            </div>
          ) : null}
        </>
      ) : null}
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
