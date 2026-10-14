"use client";

import { useMemo, useState } from "react";
import { createValidationBatch, reviewValidationBatch, submitValidationBatch } from "@/lib/api";
import { ExperimentalValidationBatch, ExperimentOptimizationRun, OptimizationParameters } from "@/lib/schemas";

const gateLabels: Record<string, string> = {
  lineageComplete: "模型、仿真、工艺版本血缘完整",
  actualParametersWithinTolerance: "实际参数在批准容差内",
  minimumTargetReplicates: "目标指标至少 3 个重复样",
  targetUnitsConsistent: "目标指标单位一致",
  measurementMethodsPresent: "测量方法记录完整",
  noContamination: "未观察到污染",
  noEquipmentAbnormalities: "无设备异常",
  humanConfirmed: "研发负责人已确认",
};

export function ExperimentalFeedbackWorkbench({ experimentId, approvedRuns, initialBatches }: {
  experimentId: string;
  approvedRuns: ExperimentOptimizationRun[];
  initialBatches: ExperimentalValidationBatch[];
}) {
  const [batches, setBatches] = useState(initialBatches);
  const [selectedRunId, setSelectedRunId] = useState(approvedRuns.at(-1)?.runId ?? "");
  const [batchCode, setBatchCode] = useState(`LAB-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}-01`);
  const [operator, setOperator] = useState("研发负责人");
  const [plannedAt, setPlannedAt] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
  const [activeId, setActiveId] = useState(initialBatches.at(-1)?.validationBatchId ?? "");
  const [values, setValues] = useState(["", "", ""]);
  const [unit, setUnit] = useState("AU");
  const [method, setMethod] = useState("分光光度计 600 nm");
  const [contamination, setContamination] = useState(false);
  const [abnormality, setAbnormality] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedRun = approvedRuns.find((run) => run.runId === selectedRunId);
  const active = batches.find((batch) => batch.validationBatchId === activeId);
  const targetMetric = selectedRun?.submittedModelEvidence[0]?.targetField ?? active?.qualityGate?.targetMetric ?? "模型目标";
  const actual = active?.approvedParameters ?? selectedRun?.submittedParameters;
  const [parameters, setParameters] = useState<Record<keyof OptimizationParameters, string>>({ temperatureC: "", ph: "", cultureHours: "", stirringRpm: "" });
  const parameterDraft = useMemo(() => ({
    temperatureC: parameters.temperatureC || String(actual?.temperatureC ?? ""),
    ph: parameters.ph || String(actual?.ph ?? ""),
    cultureHours: parameters.cultureHours || String(actual?.cultureHours ?? ""),
    stirringRpm: parameters.stirringRpm || String(actual?.stirringRpm ?? ""),
  }), [parameters, actual]);

  async function execute(action: () => Promise<ExperimentalValidationBatch>) {
    setBusy(true); setError(null);
    try {
      const updated = await action();
      setBatches((current) => [...current.filter((item) => item.validationBatchId !== updated.validationBatchId), updated]);
      setActiveId(updated.validationBatchId);
    } catch (value) {
      setError(value instanceof Error ? value.message : "操作失败");
    } finally { setBusy(false); }
  }

  function createBatch() {
    if (!selectedRun?.officialParameterVersion || !selectedRun.newResultVersion) return;
    void execute(() => createValidationBatch(experimentId, {
      optimizationRunId: selectedRun.runId,
      parameterVersion: selectedRun.officialParameterVersion!,
      predictedResultVersion: selectedRun.newResultVersion!,
      batchCode, scale: "lab", operator,
      plannedAt: new Date(plannedAt).toISOString(),
    }));
  }

  function submitBatch() {
    if (!active || values.some((value) => !value.trim()) || Object.values(parameterDraft).some((value) => !value.trim())) {
      setError("请完整填写实际参数与 3 个重复测量值"); return;
    }
    const actualParameters = Object.fromEntries(Object.entries(parameterDraft).map(([key, value]) => [key, Number(value)])) as OptimizationParameters;
    const measuredAt = new Date().toISOString();
    void execute(() => submitValidationBatch(experimentId, active.validationBatchId, {
      actualParameters,
      measurements: values.map((value, index) => ({ metricName: targetMetric, value: Number(value), unit, replicate: index + 1, measuredAt, method, sourceAssetId: null, isModelTarget: true })),
      contaminationObserved: contamination,
      equipmentAbnormalities: abnormality.trim() ? [abnormality.trim()] : [],
      notes: "真实实验批次回流",
    }));
  }

  return <section className="rounded-2xl border border-[#dce4de] bg-white p-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-xs text-[#2f7054]">真实实验反馈 · 模型闭环</p><h2 className="mt-2 text-xl font-semibold">验证批次与重训练资格</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">把已批准工艺带回真实小试或中试，记录实际参数和重复测量。质量门禁通过后只生成可重训练数据资产，不会自动替换当前模型。</p></div>
      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">已登记 {batches.length} 批</span>
    </div>
    {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

    {!active || active.status !== "draft" ? <div className="mt-5 grid gap-3 md:grid-cols-4">
      <label className="text-xs text-slate-600">已批准优化方案<select value={selectedRunId} onChange={(event) => setSelectedRunId(event.target.value)} className="mt-2 h-10 w-full rounded-lg border px-3 text-sm"><option value="">请选择</option>{approvedRuns.map((run) => <option key={run.runId} value={run.runId}>V{run.version} · {run.officialParameterVersion}</option>)}</select></label>
      <Field label="真实批次编号" value={batchCode} onChange={setBatchCode}/>
      <Field label="计划执行时间" value={plannedAt} onChange={setPlannedAt} type="datetime-local"/>
      <label className="flex items-end"><button disabled={busy || !selectedRun || !batchCode.trim()} onClick={createBatch} className="h-10 w-full rounded-lg bg-[#174333] px-4 text-sm text-white disabled:opacity-35">建立验证批次</button></label>
    </div> : null}

    {active && <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
      <div className="flex flex-wrap justify-between gap-2"><div><b>{active.batchCode}</b><p className="mt-1 text-xs text-slate-500">{active.parameterVersion} → {active.parentModelVersion}</p></div><span className="h-fit rounded-full bg-white px-3 py-1 text-xs">{active.status === "draft" ? "待录入" : active.status === "needsReview" ? "待人工确认" : active.status === "confirmed" ? "已形成训练资产" : "已驳回"}</span></div>
      {active.status === "draft" && <div className="mt-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-4">{([ ["temperatureC", "实际温度（℃）"], ["ph", "实际 pH"], ["cultureHours", "实际培养时间（小时）"], ["stirringRpm", "实际搅拌速度（rpm）"] ] as const).map(([key, label]) => <Field key={key} label={label} value={parameterDraft[key]} onChange={(value) => setParameters((current) => ({ ...current, [key]: value }))}/>)}</div>
        <div><p className="text-xs font-medium text-slate-700">{targetMetric} · 三个独立重复测量</p><div className="mt-2 grid gap-3 md:grid-cols-3">{values.map((value, index) => <Field key={index} label={`重复样 ${index + 1}`} value={value} onChange={(next) => setValues((current) => current.map((item, itemIndex) => itemIndex === index ? next : item))}/>)}</div></div>
        <div className="grid gap-3 md:grid-cols-3"><Field label="单位" value={unit} onChange={setUnit}/><Field label="测量方法" value={method} onChange={setMethod}/><Field label="设备异常（无则留空）" value={abnormality} onChange={setAbnormality}/></div>
        <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={contamination} onChange={(event) => setContamination(event.target.checked)}/>观察到污染</label>
        <button disabled={busy} onClick={submitBatch} className="rounded-lg bg-[#174333] px-4 py-2 text-sm text-white disabled:opacity-35">提交数据质量检查</button>
      </div>}
      {active.qualityGate && <div className="mt-4"><div className="grid gap-2 md:grid-cols-2">{Object.entries(active.qualityGate.checks).map(([key, passed]) => <div key={key} className={`rounded-lg border p-3 text-xs ${passed ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}><b>{passed ? "通过" : "待处理"}</b> · {gateLabels[key] ?? key}</div>)}</div>{active.qualityGate.reasons.length > 0 && <p className="mt-3 text-xs text-amber-800">{active.qualityGate.reasons.join("；")}</p>}</div>}
      {active.status === "needsReview" && <div className="mt-4 grid gap-3 md:grid-cols-[180px_1fr_auto_auto]"><Field label="审核人" value={operator} onChange={setOperator}/><Field label="审核依据" value={reason} onChange={setReason}/><button disabled={busy || reason.trim().length < 2 || Object.entries(active.qualityGate?.checks ?? {}).some(([key, passed]) => key !== "humanConfirmed" && !passed)} onClick={() => void execute(() => reviewValidationBatch(experimentId, active.validationBatchId, "approved", operator, reason))} className="mt-6 h-10 rounded-lg bg-[#174333] px-4 text-sm text-white disabled:opacity-35">确认并建资产</button><button disabled={busy || reason.trim().length < 2} onClick={() => void execute(() => reviewValidationBatch(experimentId, active.validationBatchId, "rejected", operator, reason))} className="mt-6 h-10 rounded-lg border px-4 text-sm disabled:opacity-35">驳回</button></div>}
      {active.status === "confirmed" && <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-900">已生成数据资产：{active.qualityGate?.feedbackDatasetVersion}。下一步须创建独立重训练活动并重新评估，当前模型不会自动变更。</p>}
    </div>}
  </section>;
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="text-xs text-slate-600">{label}<input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm"/></label>;
}
