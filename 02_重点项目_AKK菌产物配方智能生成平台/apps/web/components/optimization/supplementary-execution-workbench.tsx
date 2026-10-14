"use client";

import { ChangeEvent, useMemo, useState } from "react";
import {
  attachSupplementaryExecutionAssets,
  createSupplementaryExecutionBatch,
  reviewSupplementaryExecutionBatch,
  startSupplementaryExecutionBatch,
  updateSupplementaryExecutionStep,
  uploadExperimentTextFile,
} from "@/lib/api";
import { SupplementaryExecutionBatch, SupplementaryExperimentDesignRun } from "@/lib/schemas";

const statusLabels = {
  planned: "待开始", inProgress: "执行中", awaitingData: "等待原始数据",
  needsReview: "等待人工复核", completed: "已完成", cancelled: "已取消",
};
const stepStatusLabels = { pending: "等待", inProgress: "当前环节", completed: "已完成" };

export function SupplementaryExecutionWorkbench({ experimentId, approvedDesigns, initialBatches }: {
  experimentId: string;
  approvedDesigns: SupplementaryExperimentDesignRun[];
  initialBatches: SupplementaryExecutionBatch[];
}) {
  const [batches, setBatches] = useState(initialBatches);
  const [activeId, setActiveId] = useState(initialBatches.at(-1)?.batchId ?? "");
  const [designId, setDesignId] = useState(approvedDesigns.at(-1)?.runId ?? "");
  const design = approvedDesigns.find((item) => item.runId === designId);
  const existingCandidateIds = useMemo(() => new Set(batches.map((item) => `${item.planVersion}:${item.candidateId}`)), [batches]);
  const availableCandidates = design?.candidates.filter((item) => design.selectedCandidateIds.includes(item.candidateId) && !existingCandidateIds.has(`${design.planVersion}:${item.candidateId}`)) ?? [];
  const [candidateId, setCandidateId] = useState("");
  const [batchCode, setBatchCode] = useState(`SUP-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}-01`);
  const [operator, setOperator] = useState("研发负责人");
  const [plannedAt, setPlannedAt] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
  const [replicateCount, setReplicateCount] = useState("3");
  const [samplingText, setSamplingText] = useState("培养结束后采样\n目标指标至少三个独立重复\n保留设备原始导出文件");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = batches.find((item) => item.batchId === activeId);

  async function execute(action: () => Promise<SupplementaryExecutionBatch>) {
    setBusy(true); setError(null);
    try {
      const updated = await action();
      setBatches((current) => [...current.filter((item) => item.batchId !== updated.batchId), updated]);
      setActiveId(updated.batchId); setNote("");
    } catch (value) { setError(value instanceof Error ? value.message : "执行批次操作失败"); }
    finally { setBusy(false); }
  }

  function createBatch() {
    if (!design?.planVersion || !candidateId) return;
    const requirements = samplingText.split("\n").map((item) => item.trim()).filter(Boolean);
    void execute(() => createSupplementaryExecutionBatch(experimentId, {
      designRunId: design.runId, planVersion: design.planVersion!, candidateId,
      batchCode, scale: "lab", operator, plannedAt: new Date(plannedAt).toISOString(),
      replicateCount: Number(replicateCount), samplingRequirements: requirements,
    }));
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !active) return;
    setBusy(true); setError(null);
    try {
      const asset = await uploadExperimentTextFile(experimentId, { fileName: file.name, content: await file.text() });
      const updated = await attachSupplementaryExecutionAssets(experimentId, active.batchId, [asset.assetId], operator, "补实验设备原始数据");
      setBatches((current) => [...current.filter((item) => item.batchId !== updated.batchId), updated]);
    } catch (value) { setError(value instanceof Error ? value.message : "原始数据上传失败"); }
    finally { setBusy(false); event.target.value = ""; }
  }

  const currentStep = active?.steps.find((item) => item.status === "inProgress");
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-xs text-[#2f7054]">现实验证执行</p><h2 className="mt-2 text-xl font-semibold">补实验执行批次</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">把获批方案转成可执行实验。平台记录步骤、等待状态和真实数据，但不会伪造测量结果，也不会直接控制设备。</p></div>
      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">执行批次 {batches.length}</span>
    </div>
    {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

    <div className="mt-5 grid gap-4 lg:grid-cols-[320px_1fr]">
      <aside className="space-y-2 rounded-xl border bg-slate-50 p-3">
        <p className="px-2 text-xs font-medium text-slate-600">已建立的执行批次</p>
        {batches.length === 0 && <p className="px-2 py-5 text-sm text-slate-500">尚无批次，请从已批准计划建立。</p>}
        {batches.map((item) => <button key={item.batchId} onClick={() => setActiveId(item.batchId)} className={`w-full rounded-lg border p-3 text-left ${activeId === item.batchId ? "border-[#246448] bg-white" : "border-transparent"}`}><div className="flex justify-between gap-2"><b className="text-sm">{item.batchCode}</b><span className="text-[10px] text-[#2f7054]">{statusLabels[item.status]}</span></div><p className="mt-1 text-xs text-slate-500">{item.candidateName}</p></button>)}
      </aside>

      <div>
        {!active && <div className="rounded-xl border p-5"><h3 className="font-semibold">从已批准补实验计划建立批次</h3><div className="mt-4 grid gap-3 md:grid-cols-2"><Select label="已批准计划" value={designId} onChange={(value) => { setDesignId(value); setCandidateId(""); }} options={approvedDesigns.map((item) => ({ value: item.runId, label: item.planVersion ?? item.runId }))}/><Select label="待执行候选方案" value={candidateId} onChange={setCandidateId} options={availableCandidates.map((item) => ({ value: item.candidateId, label: item.displayName }))}/><Field label="执行批次编号" value={batchCode} onChange={setBatchCode}/><Field label="计划开始时间" value={plannedAt} onChange={setPlannedAt} type="datetime-local"/><Field label="独立重复次数" value={replicateCount} onChange={setReplicateCount} type="number"/><Field label="负责人" value={operator} onChange={setOperator}/><label className="text-xs text-slate-600 md:col-span-2">采样要求（每行一项）<textarea value={samplingText} onChange={(event) => setSamplingText(event.target.value)} className="mt-2 min-h-24 w-full rounded-lg border p-3 text-sm"/></label></div><button disabled={busy || !design?.planVersion || !candidateId || Number(replicateCount) < 3} onClick={createBatch} className="mt-4 rounded-lg bg-[#174333] px-5 py-2.5 text-sm text-white disabled:opacity-35">建立执行批次</button></div>}

        {active && <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4"><Metric label="当前状态" value={statusLabels[active.status]}/><Metric label="计划版本" value={active.planVersion}/><Metric label="模型与报告" value={`${active.modelVersion} · ${active.reportId}`}/><Metric label="独立重复" value={`${active.replicateCount} 次`}/></div>
          <div className="grid gap-3 md:grid-cols-4"><Parameter label="温度" value={`${active.frozenParameters.temperatureC} ℃`}/><Parameter label="pH" value={String(active.frozenParameters.ph)}/><Parameter label="培养时间" value={`${active.frozenParameters.cultureHours} h`}/><Parameter label="搅拌速度" value={`${active.frozenParameters.stirringRpm} rpm`}/></div>
          <div className="rounded-xl border p-4"><b className="text-sm">采样要求</b><ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-600">{active.samplingRequirements.map((item) => <li key={item}>{item}</li>)}</ul></div>
          <div className="space-y-2">{active.steps.map((step) => <div key={step.stepKey} className={`grid gap-3 rounded-xl border p-4 md:grid-cols-[120px_1fr_auto] ${step.status === "inProgress" ? "border-amber-300 bg-amber-50" : step.status === "completed" ? "border-emerald-200 bg-emerald-50/50" : "bg-slate-50"}`}><div><span className="text-[10px] text-slate-500">环节 {step.order}</span><p className="text-xs font-medium">{stepStatusLabels[step.status]}</p></div><div><b className="text-sm">{step.title}</b><p className="mt-1 text-xs leading-5 text-slate-600">{step.requirement}</p>{step.note && <p className="mt-1 text-xs text-[#2f7054]">记录：{step.note}</p>}</div>{step.status === "inProgress" && active.status !== "needsReview" && <button disabled={busy || note.trim().length < 2 || (step.stepKey === "dataArchive" && active.assets.length === 0)} onClick={() => void execute(() => updateSupplementaryExecutionStep(experimentId, active.batchId, step.stepKey, "completed", operator, note))} className="h-9 rounded-lg bg-[#174333] px-4 text-xs text-white disabled:opacity-35">完成本环节</button>}</div>)}</div>
          {active.status === "planned" && <button disabled={busy} onClick={() => void execute(() => startSupplementaryExecutionBatch(experimentId, active.batchId, operator, "负责人确认开始执行"))} className="rounded-lg bg-[#174333] px-5 py-2.5 text-sm text-white">开始执行</button>}
          {currentStep && active.status !== "planned" && active.status !== "needsReview" && <Field label={`“${currentStep.title}”执行记录`} value={note} onChange={setNote}/>} 
          {(active.status === "awaitingData" || currentStep?.stepKey === "dataArchive") && <div className="rounded-xl border border-dashed border-[#6b927f] bg-[#f3f8f5] p-4"><b className="text-sm">上传真实设备原始数据</b><p className="mt-1 text-xs text-slate-600">支持当前解析链路可读取的 CSV、TXT、TSV、JSON。上传后校验内容摘要并关联本批次。</p><input disabled={busy} type="file" accept=".csv,.txt,.tsv,.json" onChange={upload} className="mt-3 block text-xs"/></div>}
          {active.assets.length > 0 && <div className="rounded-xl border p-4"><b className="text-sm">已关联数据资产</b>{active.assets.map((asset) => <div key={asset.assetId} className="mt-2 flex justify-between gap-3 rounded-lg bg-slate-50 p-3 text-xs"><span>{asset.originalName}</span><span className="text-emerald-700">完整性已验证</span></div>)}</div>}
          {active.status === "needsReview" && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><b className="text-sm">人工完成复核</b><p className="mt-1 text-xs text-amber-900">批准只确认执行记录完整，不会创建测量结果或触发模型训练。</p><div className="mt-3 grid gap-3 md:grid-cols-[180px_1fr_auto_auto]"><Field label="复核人" value={operator} onChange={setOperator}/><Field label="复核依据" value={note} onChange={setNote}/><button disabled={busy || note.trim().length < 2} onClick={() => void execute(() => reviewSupplementaryExecutionBatch(experimentId, active.batchId, "approved", operator, note))} className="mt-6 h-10 rounded-lg bg-[#174333] px-4 text-sm text-white disabled:opacity-35">确认完成</button><button disabled={busy || note.trim().length < 2} onClick={() => void execute(() => reviewSupplementaryExecutionBatch(experimentId, active.batchId, "rejected", operator, note))} className="mt-6 h-10 rounded-lg border px-4 text-sm disabled:opacity-35">退回整改</button></div></div>}
          {active.status === "completed" && <p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-900">执行记录已由 {active.reviewedBy} 人工确认。真实测量值仍需进入反馈数据提交与质量门禁，当前模型未自动变更。</p>}
          <p className="text-[10px] text-slate-400">{active.disclaimer}</p>
        </div>}
      </div>
    </div>
  </section>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-slate-50 p-3"><p className="text-[10px] text-slate-500">{label}</p><p className="mt-1 truncate text-xs font-medium">{value}</p></div>; }
function Parameter({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border bg-white p-3"><span className="text-xs text-slate-500">{label}</span><b className="mt-1 block text-sm">{value}</b></div>; }
function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) { return <label className="text-xs text-slate-600">{label}<input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm"/></label>; }
function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[] }) { return <label className="text-xs text-slate-600">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm"><option value="">请选择</option>{options.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>; }
