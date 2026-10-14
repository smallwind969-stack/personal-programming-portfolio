"use client";

import { useMemo, useState } from "react";
import { createSupplementaryMeasurementBatch, reviewSupplementaryMeasurementBatch, submitSupplementaryMeasurementBatch } from "@/lib/api";
import { OptimizationParameters, SupplementaryExecutionBatch, SupplementaryMeasurementBatch } from "@/lib/schemas";

const gateLabels: Record<string, string> = {
  executionCompleted: "来源执行批次已完成", sourceAssetsVerified: "测量来源文件已验证",
  actualParametersWithinTolerance: "实际参数处于冻结参数容差内", targetMetricMatchesModel: "目标指标与父模型一致",
  minimumTargetReplicates: "目标指标至少三个独立重复", uniqueTargetReplicates: "重复编号唯一",
  targetUnitsConsistent: "目标单位一致", measurementMethodsPresent: "测量方法完整",
  noContamination: "未观察到污染", noEquipmentAbnormalities: "无设备异常", humanConfirmed: "研发负责人已人工确认",
};

export function SupplementaryMeasurementWorkbench({ experimentId, completedExecutions, initialBatches }: {
  experimentId: string; completedExecutions: SupplementaryExecutionBatch[]; initialBatches: SupplementaryMeasurementBatch[];
}) {
  const [batches, setBatches] = useState(initialBatches);
  const [activeId, setActiveId] = useState(initialBatches.at(-1)?.measurementBatchId ?? "");
  const [executionId, setExecutionId] = useState("");
  const [operator, setOperator] = useState("研发负责人");
  const [values, setValues] = useState(["", "", ""]);
  const [unit, setUnit] = useState("");
  const [method, setMethod] = useState("");
  const [sourceAssetId, setSourceAssetId] = useState("");
  const [parameterEdits, setParameterEdits] = useState<Partial<Record<keyof OptimizationParameters, string>>>({});
  const [contamination, setContamination] = useState(false);
  const [abnormality, setAbnormality] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = batches.find((item) => item.measurementBatchId === activeId);
  const usedExecutions = useMemo(() => new Set(batches.map((item) => item.executionBatchId)), [batches]);
  const available = completedExecutions.filter((item) => !usedExecutions.has(item.batchId));

  async function execute(action: () => Promise<SupplementaryMeasurementBatch>) {
    setBusy(true); setError(null);
    try {
      const updated = await action();
      setBatches((current) => [...current.filter((item) => item.measurementBatchId !== updated.measurementBatchId), updated]);
      setActiveId(updated.measurementBatchId); setNotes("");
      if (!sourceAssetId) setSourceAssetId(updated.allowedSourceAssetIds[0] ?? "");
    } catch (value) { setError(value instanceof Error ? value.message : "真实测量交接失败"); }
    finally { setBusy(false); }
  }

  const actualDraft = active ? {
    temperatureC: parameterEdits.temperatureC ?? String(active.frozenParameters.temperatureC),
    ph: parameterEdits.ph ?? String(active.frozenParameters.ph),
    cultureHours: parameterEdits.cultureHours ?? String(active.frozenParameters.cultureHours),
    stirringRpm: parameterEdits.stirringRpm ?? String(active.frozenParameters.stirringRpm),
  } : null;

  function submit() {
    if (!active || !actualDraft || values.some((value) => !value.trim()) || !unit.trim() || !method.trim() || !sourceAssetId) {
      setError("请填写实际参数、三个真实重复测量、单位、方法和来源文件"); return;
    }
    const measuredAt = new Date().toISOString();
    void execute(() => submitSupplementaryMeasurementBatch(experimentId, active.measurementBatchId, {
      actualParameters: Object.fromEntries(Object.entries(actualDraft).map(([key, value]) => [key, Number(value)])) as OptimizationParameters,
      measurements: values.map((value, index) => ({
        metricName: active.targetMetric, value: Number(value), unit: unit.trim(), replicate: index + 1,
        measuredAt, method: method.trim(), sourceAssetId, isModelTarget: true,
      })),
      contaminationObserved: contamination,
      equipmentAbnormalities: abnormality.trim() ? [abnormality.trim()] : [],
      notes: notes.trim(),
    }));
  }

  return <section className="rounded-2xl border border-[#dce4de] bg-white p-6">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs text-[#2f7054]">真实测量与数据回流</p><h2 className="mt-2 text-xl font-semibold">补实验测量与反馈资格</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">这里不自动生成数值。研发人员必须录入真实测量并引用执行批次中的原始文件，质量门禁和人工复核通过后才形成反馈数据资产。</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">测量任务 {batches.length}</span></div>
    {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    <div className="mt-5 grid gap-4 lg:grid-cols-[300px_1fr]">
      <aside className="space-y-2 rounded-xl border bg-slate-50 p-3"><p className="px-2 text-xs font-medium text-slate-600">真实测量任务</p>{batches.length === 0 && <p className="px-2 py-5 text-sm text-slate-500">完成补实验执行后才能建立。</p>}{batches.map((item) => <button key={item.measurementBatchId} onClick={() => { setActiveId(item.measurementBatchId); setSourceAssetId(item.allowedSourceAssetIds[0] ?? ""); }} className={`w-full rounded-lg border p-3 text-left ${activeId === item.measurementBatchId ? "border-[#246448] bg-white" : "border-transparent"}`}><div className="flex justify-between gap-2"><b className="text-sm">{item.executionBatchCode}</b><span className="text-[10px] text-[#2f7054]">{item.status === "draft" ? "待录入" : item.status === "needsReview" ? "待复核" : item.status === "confirmed" ? "已形成反馈资产" : "已驳回"}</span></div><p className="mt-1 text-xs text-slate-500">目标：{item.targetMetric}</p></button>)}</aside>
      <div>
        {!active && <div className="rounded-xl border p-5"><h3 className="font-semibold">从已完成执行批次建立测量任务</h3><p className="mt-2 text-xs text-slate-600">建立任务只继承血缘和文件，不会填入测量结果。</p><div className="mt-4 grid gap-3 md:grid-cols-[1fr_180px_auto]"><Select label="已完成执行批次" value={executionId} onChange={setExecutionId} options={available.map((item) => ({ value: item.batchId, label: `${item.batchCode} · ${item.candidateName}` }))}/><Field label="负责人" value={operator} onChange={setOperator}/><button disabled={busy || !executionId} onClick={() => void execute(() => createSupplementaryMeasurementBatch(experimentId, executionId, operator))} className="mt-6 h-10 rounded-lg bg-[#174333] px-4 text-sm text-white disabled:opacity-35">建立测量任务</button></div></div>}
        {active && <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4"><Metric label="执行批次" value={active.executionBatchCode}/><Metric label="计划版本" value={active.planVersion}/><Metric label="父模型" value={active.parentModelVersion}/><Metric label="模型目标" value={active.targetMetric}/></div>
          <div className="rounded-xl border p-4"><b className="text-sm">允许引用的已验证来源文件</b><div className="mt-2 flex flex-wrap gap-2">{active.allowedSourceAssetIds.map((assetId) => <span key={assetId} className="rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-800">{active.sourceAssetNames[assetId]} · 已验证</span>)}</div></div>
          {active.status === "draft" && actualDraft && <div className="space-y-4 rounded-xl border p-4"><div><b className="text-sm">实际执行参数</b><p className="mt-1 text-xs text-slate-500">默认显示冻结参数；如实填写实际偏差，系统会按容差检查。</p><div className="mt-3 grid gap-3 md:grid-cols-4">{([ ["temperatureC", "温度（℃）"], ["ph", "pH"], ["cultureHours", "培养时间（h）"], ["stirringRpm", "搅拌速度（rpm）"] ] as const).map(([key, label]) => <Field key={key} label={label} value={actualDraft[key]} onChange={(value) => setParameterEdits((current) => ({ ...current, [key]: value }))}/>)}</div></div><div><b className="text-sm">{active.targetMetric} · 三个真实独立重复</b><div className="mt-3 grid gap-3 md:grid-cols-3">{values.map((value, index) => <Field key={index} label={`重复 ${index + 1}`} value={value} onChange={(next) => setValues((current) => current.map((item, itemIndex) => itemIndex === index ? next : item))}/>)}</div></div><div className="grid gap-3 md:grid-cols-3"><Field label="单位" value={unit} onChange={setUnit}/><Field label="测量方法/仪器" value={method} onChange={setMethod}/><Select label="来源原始文件" value={sourceAssetId} onChange={setSourceAssetId} options={active.allowedSourceAssetIds.map((assetId) => ({ value: assetId, label: active.sourceAssetNames[assetId] }))}/></div><div className="grid gap-3 md:grid-cols-2"><Field label="设备异常（无则留空）" value={abnormality} onChange={setAbnormality}/><Field label="真实实验备注" value={notes} onChange={setNotes}/></div><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={contamination} onChange={(event) => setContamination(event.target.checked)}/>观察到污染</label><button disabled={busy} onClick={submit} className="rounded-lg bg-[#174333] px-5 py-2.5 text-sm text-white disabled:opacity-35">提交真实测量质量检查</button></div>}
          {active.qualityGate && <div className="rounded-xl border p-4"><b className="text-sm">反馈数据质量门禁</b><div className="mt-3 grid gap-2 md:grid-cols-2">{Object.entries(active.qualityGate.checks).map(([key, passed]) => <div key={key} className={`rounded-lg border p-3 text-xs ${passed ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}><b>{passed ? "通过" : "未通过"}</b> · {gateLabels[key] ?? key}</div>)}</div>{active.qualityGate.reasons.length > 0 && <p className="mt-3 text-xs text-amber-800">{active.qualityGate.reasons.join("；")}</p>}</div>}
          {active.status === "needsReview" && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><b className="text-sm">研发负责人复核</b><p className="mt-1 text-xs text-amber-900">任何技术门禁失败时，批准按钮保持禁用，不能人工绕过。</p><div className="mt-3 grid gap-3 md:grid-cols-[180px_1fr_auto_auto]"><Field label="复核人" value={operator} onChange={setOperator}/><Field label="复核依据" value={notes} onChange={setNotes}/><button disabled={busy || notes.trim().length < 2 || Object.entries(active.qualityGate?.checks ?? {}).some(([key, value]) => key !== "humanConfirmed" && !value)} onClick={() => void execute(() => reviewSupplementaryMeasurementBatch(experimentId, active.measurementBatchId, "approved", operator, notes))} className="mt-6 h-10 rounded-lg bg-[#174333] px-4 text-sm text-white disabled:opacity-35">确认反馈资产</button><button disabled={busy || notes.trim().length < 2} onClick={() => void execute(() => reviewSupplementaryMeasurementBatch(experimentId, active.measurementBatchId, "rejected", operator, notes))} className="mt-6 h-10 rounded-lg border px-4 text-sm disabled:opacity-35">驳回</button></div></div>}
          {active.status === "confirmed" && <p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-900">反馈数据资产已形成：{active.qualityGate?.feedbackDatasetVersion}。它只获得后续重训练资格，当前模型和仿真准入未改变。</p>}
          {active.status === "rejected" && <p className="rounded-lg bg-rose-50 p-4 text-sm text-rose-800">本次测量任务已驳回，原始测量与人工意见继续保留，不会生成反馈数据资产。</p>}
          <p className="text-[10px] text-slate-400">{active.disclaimer}</p>
        </div>}
      </div>
    </div>
  </section>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-slate-50 p-3"><p className="text-[10px] text-slate-500">{label}</p><p className="mt-1 truncate text-xs font-medium">{value}</p></div>; }
function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label className="text-xs text-slate-600">{label}<input value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm"/></label>; }
function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[] }) { return <label className="text-xs text-slate-600">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm"><option value="">请选择</option>{options.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>; }
