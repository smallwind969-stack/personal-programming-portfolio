"use client";

import { useState } from "react";
import { createSupplementaryDesignRun, reviewSupplementaryDesignRun, selectSupplementaryDesignCandidates } from "@/lib/api";
import { ModelEvaluationReport, SupplementaryExperimentDesignRun } from "@/lib/schemas";

export function SupplementaryExperimentWorkbench({ experimentId, latestReport, initialRuns }: {
  experimentId: string;
  latestReport: ModelEvaluationReport | null;
  initialRuns: SupplementaryExperimentDesignRun[];
}) {
  const [runs, setRuns] = useState(initialRuns);
  const [activeId, setActiveId] = useState(initialRuns.at(-1)?.runId ?? "");
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = runs.find((run) => run.runId === activeId);

  async function execute(action: () => Promise<SupplementaryExperimentDesignRun>) {
    setBusy(true); setError(null);
    try {
      const updated = await action();
      setRuns((current) => [...current.filter((item) => item.runId !== updated.runId), updated]);
      setActiveId(updated.runId);
    } catch (value) {
      setError(value instanceof Error ? value.message : "补实验设计操作失败");
    } finally { setBusy(false); }
  }

  function toggle(candidateId: string) {
    if (!active || active.status !== "needsReview") return;
    const selected = active.selectedCandidateIds.includes(candidateId)
      ? active.selectedCandidateIds.filter((item) => item !== candidateId)
      : [...active.selectedCandidateIds, candidateId];
    if (selected.length === 0) { setError("至少保留一个候选方案"); return; }
    void execute(() => selectSupplementaryDesignCandidates(experimentId, active.runId, selected));
  }

  const canCreate = latestReport && !latestReport.recommendedAdmission;
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-6">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs text-[#2f7054]">信息增益实验设计</p><h2 className="mt-2 text-xl font-semibold">可靠性补实验设计</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">根据漂移、覆盖率、残差和特征重要性生成下一轮最有信息量的实验点。所有参数保持在已观察范围内，低可靠性模型预测仅用于实验排序。</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">设计 {runs.length} 个</span></div>
    {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

    {!active || active.status !== "needsReview" ? <div className="mt-5 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-[1fr_1fr_auto]"><Metric label="最新可靠性报告" value={latestReport?.reportId ?? "暂无报告"}/><Metric label="可靠性与准入" value={latestReport ? `${(latestReport.reliabilityScore * 100).toFixed(1)}% · ${latestReport.recommendedAdmission ? "已满足准入" : "需要补实验"}` : "不可生成"}/><button disabled={busy || !canCreate} onClick={() => latestReport && void execute(() => createSupplementaryDesignRun(experimentId, latestReport.reportId))} className="self-end rounded-lg bg-[#174333] px-5 py-2.5 text-sm text-white disabled:opacity-35">生成三套补实验方案</button>{latestReport?.recommendedAdmission && <p className="text-xs text-emerald-800 md:col-span-3">当前模型已满足可靠性准入，不需要为了展示而额外生成实验。</p>}</div> : null}

    {active && <div className="mt-5 space-y-4">
      <div className="grid gap-3 md:grid-cols-4"><Metric label="模型版本" value={active.modelVersion}/><Metric label="可靠性报告" value={active.reportId}/><Metric label="可靠性评分" value={`${(active.reliabilityScore * 100).toFixed(1)}%`}/><Metric label="绑定来源" value={active.bindingSource === "confirmed_binding" ? active.bindingVersion ?? "已确认绑定" : "标准字段别名回退 · 待人工核对"}/></div>
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><b className="text-sm">本轮需要解决的可靠性缺口</b><ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-900">{active.admissionReasons.map((item) => <li key={item}>{item}</li>)}</ul></div>
      <div className="grid gap-4 xl:grid-cols-3">{active.candidates.map((candidate) => { const selected = active.selectedCandidateIds.includes(candidate.candidateId); return <article key={candidate.candidateId} className={`rounded-xl border p-5 ${selected ? "border-[#246448] bg-emerald-50/40 ring-2 ring-[#246448]/10" : "border-slate-200"}`}><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] text-[#2f7054]">{candidate.strategyKey}</p><h3 className="mt-1 font-semibold">{candidate.displayName}</h3></div><button disabled={busy || active.status !== "needsReview"} onClick={() => toggle(candidate.candidateId)} className={`rounded-full px-3 py-1 text-xs ${selected ? "bg-[#174333] text-white" : "border bg-white"}`}>{selected ? "已选择" : "选择"}</button></div><p className="mt-3 text-sm leading-6 text-slate-600">{candidate.summary}</p><div className="mt-3 grid grid-cols-2 gap-2"><Metric label="信息增益" value={`${(candidate.informationGainScore * 100).toFixed(1)}%`}/><Metric label="边界风险" value={`${(candidate.boundaryRiskScore * 100).toFixed(1)}%`}/></div><div className="mt-3 grid grid-cols-2 gap-2 text-xs"><Parameter label="温度" value={`${candidate.processParameters.temperatureC} ℃`}/><Parameter label="pH" value={String(candidate.processParameters.ph)}/><Parameter label="培养时间" value={`${candidate.processParameters.cultureHours} h`}/><Parameter label="搅拌速度" value={`${candidate.processParameters.stirringRpm} rpm`}/></div><div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs"><p className="text-slate-500">探索性预测 · 不作为生产结果</p><b className="mt-1 block text-base">{candidate.exploratoryPrediction.toFixed(4)}</b><p className="mt-1 text-slate-500">区间 {candidate.intervalLower.toFixed(4)} – {candidate.intervalUpper.toFixed(4)}</p></div><Details title="解决缺口" items={candidate.addressesGaps}/><Details title="推导证据" items={candidate.evidence}/><p className="mt-3 break-all text-[9px] text-slate-400">模型特征：{Object.entries(candidate.modelFeatureValues).map(([key,value]) => `${key}=${value}`).join(" · ")}</p></article>; })}</div>
      {active.status === "needsReview" && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><b className="text-sm">人工批准补实验计划</b><p className="mt-2 text-xs leading-5 text-amber-900">批准只冻结候选计划。下一步还需建立真实实验批次并回流仪器数据，不会自动生成实验结果或发送设备控制命令。</p><div className="mt-3 grid gap-3 md:grid-cols-[180px_1fr_auto_auto]"><Field label="审核人" value={operator} onChange={setOperator}/><Field label="审核依据" value={reason} onChange={setReason}/><button disabled={busy || active.selectedCandidateIds.length === 0 || reason.trim().length < 2} onClick={() => void execute(() => reviewSupplementaryDesignRun(experimentId, active.runId, "approved", operator, reason))} className="mt-6 h-10 rounded-lg bg-[#174333] px-4 text-sm text-white disabled:opacity-35">批准实验计划</button><button disabled={busy || reason.trim().length < 2} onClick={() => void execute(() => reviewSupplementaryDesignRun(experimentId, active.runId, "rejected", operator, reason))} className="mt-6 h-10 rounded-lg border px-4 text-sm disabled:opacity-35">驳回</button></div></div>}
      {active.status === "approved" && <p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-900">补实验计划已冻结：{active.planVersion}。真实执行仍须进入实验批次流程并上传实际设备数据。</p>}
      <p className="break-all text-[10px] text-slate-400">模型产物：{active.modelArtifactFingerprint} · 数据：{active.datasetFingerprint}</p>
    </div>}
  </section>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-white p-3"><p className="text-[10px] text-slate-500">{label}</p><p className="mt-1 truncate text-sm font-medium">{value}</p></div>; }
function Parameter({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border bg-white p-2"><span className="text-slate-500">{label}</span><b className="mt-1 block">{value}</b></div>; }
function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label className="text-xs text-slate-600">{label}<input value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm"/></label>; }
function Details({ title, items }: { title: string; items: string[] }) { return <details className="mt-3"><summary className="cursor-pointer text-xs font-medium">{title}（{items.length}）</summary><ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>{item}</li>)}</ul></details>; }
