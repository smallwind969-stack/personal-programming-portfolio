"use client";

import { useMemo, useState } from "react";
import { advanceFeedbackRetrainingRun, createFeedbackRetrainingRun, reviewFeedbackRetrainingRun } from "@/lib/api";
import { ExperimentalValidationBatch, FeedbackRetrainingRun } from "@/lib/schemas";

const statusLabel: Record<string, string> = {
  running: "重训练进行中", needsReview: "等待人工晋升", completed: "已晋升，待可靠性复核",
  rejected: "已驳回", failed: "运行失败", waiting: "等待", needsReviewStage: "待人工复核",
};
const gateLabels: Record<string, string> = {
  independentFeedbackHoldout: "至少 3 个独立真实反馈批次",
  candidateIsCampaignBest: "候选是研究活动当前最佳试验",
  minimumImprovement: "达到最低改进幅度",
  r2Threshold: "R² 达到准入阈值",
  maeThreshold: "MAE 达到准入阈值",
  improvesIncumbentR2: "R² 优于现役模型同集表现",
  maeNotRegressed: "MAE 未显著退化",
  rmseNotRegressed: "RMSE 未显著退化",
  artifactVerified: "候选模型产物完整",
};

export function FeedbackRetrainingWorkbench({ experimentId, batches, initialRuns }: {
  experimentId: string;
  batches: ExperimentalValidationBatch[];
  initialRuns: FeedbackRetrainingRun[];
}) {
  const [runs, setRuns] = useState(initialRuns);
  const [activeId, setActiveId] = useState(initialRuns.at(-1)?.runId ?? "");
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const groups = useMemo(() => {
    const result = new Map<string, string[]>();
    for (const batch of batches) {
      const version = batch.qualityGate?.feedbackDatasetVersion;
      if (batch.status !== "confirmed" || !batch.qualityGate?.eligible || !version) continue;
      result.set(batch.parentModelVersion, [...(result.get(batch.parentModelVersion) ?? []), version]);
    }
    return result;
  }, [batches]);
  const selectedGroup = [...groups.entries()].sort((left, right) => right[1].length - left[1].length)[0];
  const parentModelVersion = selectedGroup?.[0] ?? "";
  const feedbackVersions = selectedGroup?.[1] ?? [];
  const active = runs.find((run) => run.runId === activeId);

  async function execute(action: () => Promise<FeedbackRetrainingRun>) {
    setBusy(true); setError(null);
    try {
      const updated = await action();
      setRuns((current) => [...current.filter((item) => item.runId !== updated.runId), updated]);
      setActiveId(updated.runId);
    } catch (value) {
      setError(value instanceof Error ? value.message : "重训练操作失败");
    } finally { setBusy(false); }
  }

  return <section className="rounded-2xl border border-[#dce4de] bg-white p-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-xs text-[#2f7054]">现实反馈闭环</p><h2 className="mt-2 text-xl font-semibold">真实反馈重训练活动</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">历史数据与真实反馈形成不可变派生数据集。现役模型和候选模型在同一组未见过的独立反馈批次上比较，技术门禁通过后仍必须人工晋升。</p></div>
      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">活动 {runs.length} 个</span>
    </div>
    {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

    {!active || ["completed", "rejected", "failed"].includes(active.status) ? <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]"><Metric label="共同父模型" value={parentModelVersion || "暂无合格反馈"}/><Metric label="独立确认反馈批次" value={`${feedbackVersions.length} / 最少 3 个`}/><button disabled={busy || feedbackVersions.length < 3} onClick={() => void execute(() => createFeedbackRetrainingRun(experimentId, { commandId: crypto.randomUUID(), parentModelVersion, feedbackDatasetVersions: feedbackVersions, fixedBudgetSeconds: 300 }))} className="self-end rounded-lg bg-[#174333] px-5 py-2.5 text-sm text-white disabled:opacity-35">创建重训练活动</button></div>
      {feedbackVersions.length < 3 && <p className="mt-3 text-xs text-amber-800">当前证据不足：需要至少 3 个共享同一父模型的独立真实批次。同一批次的技术重复样不会被冒充为独立批次。</p>}
    </div> : null}

    {active && <div className="mt-5 space-y-4">
      <div className="grid gap-3 md:grid-cols-4"><Metric label="运行状态" value={statusLabel[active.status] ?? active.status}/><Metric label="父模型（保持只读）" value={active.parentModelVersion}/><Metric label="派生数据集" value={active.derivedDatasetId}/><Metric label="外部留出批次" value={String(active.externalHoldoutRowCount)}/></div>
      <div className="rounded-xl border border-slate-200 p-4"><div className="flex items-center justify-between"><b className="text-sm">模型更新进程</b>{active.status === "running" && <button disabled={busy} onClick={() => void execute(() => advanceFeedbackRetrainingRun(experimentId, active.runId))} className="rounded-lg bg-[#174333] px-4 py-2 text-xs text-white disabled:opacity-35">推进下一环节</button>}</div><div className="mt-3 grid gap-2 md:grid-cols-5">{active.stages.map((stage, index) => <div key={stage.stageId} className={`rounded-lg border p-3 text-xs ${stage.status === "completed" ? "border-emerald-200 bg-emerald-50" : stage.status === "running" || stage.status === "needsReview" ? "border-amber-200 bg-amber-50" : "border-slate-200 bg-slate-50"}`}><b>{index + 1}. {stage.stageName}</b><p className="mt-1 text-slate-600">{stage.status} · {stage.progressPercent}%</p><p className="mt-2 leading-5 text-slate-500">{stage.detail}</p>{stage.outputSummary.map((item) => <p key={item} className="mt-1 text-slate-700">· {item}</p>)}</div>)}</div></div>

      {Object.keys(active.incumbentMetrics).length > 0 && <div className="rounded-xl border border-slate-200 p-4"><b className="text-sm">同一外部留出集指标对比</b><div className="mt-3 overflow-x-auto"><table className="w-full min-w-[680px] text-left text-xs"><thead className="text-slate-500"><tr><th className="p-2">模型</th><th>R²</th><th>MAE</th><th>RMSE</th><th>相对现役 R²</th><th>产物</th></tr></thead><tbody><tr className="border-t"><td className="p-2 font-medium">现役模型</td><td>{format(active.incumbentMetrics.r2)}</td><td>{format(active.incumbentMetrics.mae)}</td><td>{format(active.incumbentMetrics.rmse)}</td><td>基准</td><td>已注册</td></tr>{active.candidates.map((candidate) => <tr key={candidate.trialId} className={`border-t ${candidate.trialId === active.championTrialId ? "bg-emerald-50" : ""}`}><td className="p-2 font-medium">{candidate.modelType ?? candidate.algorithm}{candidate.trialId === active.championTrialId ? " · 最佳" : ""}</td><td>{format(candidate.metrics.r2)}</td><td>{format(candidate.metrics.mae)}</td><td>{format(candidate.metrics.rmse)}</td><td>{signed(candidate.deltaFromIncumbent.r2)}</td><td>{candidate.artifactVerified ? "已校验" : "待校验"}</td></tr>)}</tbody></table></div></div>}

      {active.promotionGate && <div className="rounded-xl border border-slate-200 p-4"><b className="text-sm">不可绕过的模型晋升门禁</b><div className="mt-3 grid gap-2 md:grid-cols-3">{Object.entries(active.promotionGate.checks).map(([key, passed]) => <div key={key} className={`rounded-lg border p-3 text-xs ${passed ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-rose-200 bg-rose-50 text-rose-900"}`}><b>{passed ? "通过" : "阻止"}</b> · {gateLabels[key] ?? key}</div>)}</div>{active.promotionGate.reasons.length > 0 && <p className="mt-3 text-xs text-rose-800">{active.promotionGate.reasons.join("；")}</p>}</div>}

      {active.status === "needsReview" && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><b className="text-sm">人工模型晋升复核</b><p className="mt-2 text-xs leading-5 text-amber-900">批准后只把候选写入模型注册表，并立即生成独立可靠性报告；可靠性报告未经再次确认，仿真准入不会开放。</p><div className="mt-3 grid gap-3 md:grid-cols-[180px_1fr_auto_auto]"><Field label="审核人" value={operator} onChange={setOperator}/><Field label="审核依据" value={reason} onChange={setReason}/><button disabled={busy || !active.promotionGate?.eligible || reason.trim().length < 2} onClick={() => void execute(() => reviewFeedbackRetrainingRun(experimentId, active.runId, "approved", operator, reason))} className="mt-6 h-10 rounded-lg bg-[#174333] px-4 text-sm text-white disabled:opacity-35">批准候选晋升</button><button disabled={busy || reason.trim().length < 2} onClick={() => void execute(() => reviewFeedbackRetrainingRun(experimentId, active.runId, "rejected", operator, reason))} className="mt-6 h-10 rounded-lg border px-4 text-sm disabled:opacity-35">驳回</button></div></div>}
      {active.status === "completed" && <p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-900">候选已晋升为 {active.promotedModelVersion}，独立可靠性报告 {active.evaluationReportId} 正等待复核。当前不能跳过该复核直接进入仿真。</p>}
      <p className="break-all text-[10px] text-slate-400">数据指纹：{active.derivedDatasetFingerprint}</p>
    </div>}
  </section>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-white p-3"><p className="text-[10px] text-slate-500">{label}</p><p className="mt-1 truncate text-sm font-medium">{value}</p></div>; }
function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label className="text-xs text-slate-600">{label}<input value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm"/></label>; }
function format(value: number | undefined) { return value == null ? "--" : value.toFixed(4); }
function signed(value: number | undefined) { return value == null ? "--" : `${value >= 0 ? "+" : ""}${value.toFixed(4)}`; }
