"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  advanceExperimentSimulationRun,
  createExperimentSimulationRun,
  createExperimentSimulationTrial,
  failExperimentSimulationRun,
  restartExperimentSimulationRun,
  retryExperimentSimulationRun,
  stopExperimentSimulationRun,
  predictCompositeModel,
} from "@/lib/api";
import type {
  ExperimentSimulationRun,
  SimulationPredictRequest,
  SimulationRunStage,
  SimulationTrialSnapshot,
  CompositeModelPrediction,
  ExperimentWorkspaceOverview,
} from "@/lib/schemas";
import { simulationPredictRequestSchema } from "@/lib/schemas";

const statusText = { waiting: "等待上游", running: "运行中", completed: "已完成", failed: "异常", stopped: "已停止" } as const;
const statusStyle = { waiting: "bg-slate-100 text-slate-600", running: "bg-blue-50 text-blue-700", completed: "bg-emerald-50 text-emerald-700", failed: "bg-rose-50 text-rose-700", stopped: "bg-stone-100 text-stone-700" } as const;

export function SimulationRuntimeWorkbench({ experimentId, initialRun, productionContext, demoMode = false }: { experimentId: string; initialRun: ExperimentSimulationRun; productionContext: ExperimentWorkspaceOverview["productionContext"]; demoMode?: boolean }) {
  const [run, setRun] = useState(initialRun);
  const [selectedStageId, setSelectedStageId] = useState(initialRun.currentStageId ?? initialRun.stages[0].stageId);
  const [parameters, setParameters] = useState<SimulationPredictRequest>(initialRun.officialParameters);
  const [latestTrial, setLatestTrial] = useState<SimulationTrialSnapshot | null>(initialRun.trialSnapshots.at(-1) ?? null);
  const [resultMode, setResultMode] = useState<"official" | "trial">(initialRun.officialResult ? "official" : "trial");
  const [emptyFields, setEmptyFields] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [composite, setComposite] = useState<CompositeModelPrediction | null>(null);

  const selectedStage = useMemo(() => run.stages.find((stage) => stage.stageId === selectedStageId) ?? run.stages[0], [run.stages, selectedStageId]);
  const activeIndex = run.currentStageId ? run.stages.findIndex((stage) => stage.stageId === run.currentStageId) : run.status === "completed" ? 6 : -1;
  const parametersValid = emptyFields.size === 0 && simulationPredictRequestSchema.safeParse(parameters).success;

  async function perform(action: string, operation: () => Promise<ExperimentSimulationRun>) {
    setBusy(action); setError(null);
    try {
      const next = await operation();
      if (next.runId !== run.runId) {
        setParameters(next.officialParameters);
        setLatestTrial(next.trialSnapshots.at(-1) ?? null);
        setEmptyFields(new Set());
        setResultMode(next.officialResult ? "official" : "trial");
      } else if (next.officialResult) {
        setResultMode("official");
      }
      setRun(next);
      if (next.currentStageId) setSelectedStageId(next.currentStageId);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "仿真操作失败"); }
    finally { setBusy(null); }
  }

  async function submitTrial() {
    if (run.version === 0) return;
    setBusy("trial"); setError(null);
    try {
      const snapshot = await createExperimentSimulationTrial(experimentId, run.runId, parameters);
      setLatestTrial(snapshot);
      setResultMode("trial");
      setRun((current) => ({ ...current, trialSnapshots: [...current.trialSnapshots, snapshot] }));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "临时试算失败"); }
    finally { setBusy(null); }
  }

  async function runPromotedModels() {
    setBusy("promoted-models"); setError(null);
    try {
      setComposite(await predictCompositeModel(experimentId, { ...parameters, ...parameters.customParameters }, ["optical_density_600", "scfa_score", "barrier_score"]));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "已晋升模型组合预测失败"); }
    finally { setBusy(null); }
  }

  function update<K extends keyof SimulationPredictRequest>(key: K, value: SimulationPredictRequest[K]) {
    setParameters((current) => ({ ...current, [key]: value }));
  }

  const setFieldEmpty = useCallback((field: string, empty: boolean) => {
    setEmptyFields((current) => {
      const next = new Set(current);
      if (empty) next.add(field); else next.delete(field);
      return next;
    });
  }, []);

  const canAdvance = run.status === "running";
  const canTrial = run.admissionAllowed && run.version > 0 && run.status !== "stopped";

  return (
    <div className="space-y-4">
      <SimulationDashboard run={run} />
      {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div> : null}
      {!run.admissionAllowed ? <AdmissionNotice run={run} /> : null}

      <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><h2 className="font-semibold text-slate-950">仿真运行环节</h2><p className="mt-1 text-xs text-slate-500">点击环节查看模型、输入、输出与等待原因。</p></div>
          <div className="flex flex-wrap gap-2">
            {run.version === 0 ? <button className="rounded-lg bg-[#174333] px-4 py-2 text-sm font-medium text-white disabled:opacity-40" disabled={!run.admissionAllowed || busy !== null} onClick={() => perform("create", () => createExperimentSimulationRun(experimentId))} type="button">创建正式仿真运行</button> : null}
            {run.version > 0 ? <button className="rounded-lg bg-[#174333] px-4 py-2 text-sm font-medium text-white disabled:opacity-40" disabled={!canAdvance || busy !== null} onClick={() => perform("advance", () => advanceExperimentSimulationRun(experimentId, run.runId))} type="button">{busy === "advance" ? "计算中…" : "推进一个仿真环节"}</button> : null}
            {run.status === "running" ? <button className="rounded-lg border border-rose-200 px-4 py-2 text-sm font-medium text-rose-700 disabled:opacity-40" disabled={busy !== null} onClick={() => perform("stop", () => stopExperimentSimulationRun(experimentId, run.runId))} type="button">终止运行</button> : null}
            {run.status === "running" ? <button className="rounded-lg border border-amber-200 px-4 py-2 text-sm font-medium text-amber-800 disabled:opacity-40" disabled={busy !== null} onClick={() => perform("fail", () => failExperimentSimulationRun(experimentId, run.runId, "mock 传感器读数中断", [run.modelVersion]))} type="button">模拟异常</button> : null}
            {run.status === "failed" ? <button className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 disabled:opacity-40" disabled={busy !== null} onClick={() => perform("retry", () => retryExperimentSimulationRun(experimentId, run.runId))} type="button">从异常环节重试</button> : null}
            {run.status === "stopped" ? <button className="rounded-lg border border-[#b8cfc2] px-4 py-2 text-sm font-medium text-[#174333] disabled:opacity-40" disabled={busy !== null} onClick={() => perform("restart", () => restartExperimentSimulationRun(experimentId, run.runId))} type="button">新版本重新开始</button> : null}
          </div>
        </div>
        <div className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-7">{run.stages.map((stage, index) => <StageButton key={stage.stageId} stage={stage} index={index} selected={stage.stageId === selectedStage.stageId} onSelect={() => setSelectedStageId(stage.stageId)} />)}</div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(22rem,.65fr)]">
        <div className="space-y-4">
          <VirtualProductionLine activeIndex={activeIndex} status={run.status} />
          <StageInspector stage={selectedStage} />
          <SimulationEvents run={run} />
        </div>
        <aside className={`space-y-4 ${demoMode ? "[&>section:nth-of-type(2)]:hidden" : ""}`}>
          <ParameterPanel context={productionContext} parameters={parameters} official={run.officialParameters} resetKey={run.runId} canTrial={canTrial && parametersValid} valid={parametersValid} busy={busy !== null} onEmptyChange={setFieldEmpty} onUpdate={update} onCustomUpdate={(key, value) => setParameters((current) => ({ ...current, customParameters: { ...current.customParameters, [key]: value } }))} onTrial={submitTrial} />
          <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="text-xs font-medium text-[#2f7054]">真实模型组合预测</div><h2 className="mt-1 font-semibold text-slate-950">已晋升模型仪表盘</h2><p className="mt-2 text-xs leading-5 text-slate-500">仅调用人工批准且完成特征绑定的模型；缺少模型的指标会明确显示为不可用。</p><button className="mt-4 w-full rounded-lg border border-[#397b5d] px-4 py-2 text-sm font-medium text-[#174333] disabled:opacity-40" disabled={!parametersValid || busy !== null} onClick={runPromotedModels} type="button">运行已晋升模型组合预测</button>{composite ? <div className="mt-4 space-y-2"><div className="text-xs text-slate-600">可靠性：<strong>{composite.reliability}</strong></div>{composite.targets.map((target) => <div className="rounded-lg bg-[#f6f8f6] p-3" key={target.targetField}><div className="flex justify-between text-xs"><span>{target.targetField}</span><strong className="font-mono">{target.prediction.toFixed(3)}</strong></div><div className="mt-1 text-[10px] text-slate-500">近似区间 {target.interval.lower.toFixed(3)} ～ {target.interval.upper.toFixed(3)} · {target.modelVersion}</div></div>)}{composite.unavailableTargets.length ? <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-800">暂无真实模型：{composite.unavailableTargets.join("、")}</div> : null}<p className="text-[10px] leading-5 text-slate-400">{composite.disclaimer}</p></div> : null}</section>
          {run.officialResult && latestTrial ? <div className="grid grid-cols-2 gap-2 rounded-xl border border-[#dce4de] bg-white p-2"><button className={`rounded-lg px-3 py-2 text-xs font-medium ${resultMode === "official" ? "bg-[#174333] text-white" : "text-slate-600"}`} onClick={() => setResultMode("official")} type="button">正式仿真结果</button><button className={`rounded-lg px-3 py-2 text-xs font-medium ${resultMode === "trial" ? "bg-[#174333] text-white" : "text-slate-600"}`} onClick={() => setResultMode("trial")} type="button">临时试算结果</button></div> : null}
          <TrialResult snapshot={resultMode === "official" ? run.officialResult : latestTrial ?? run.officialResult} />
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">{run.disclaimer}</div>
        </aside>
      </div>
    </div>
  );
}

function SimulationDashboard({ run }: { run: ExperimentSimulationRun }) {
  const metrics = [["仿真可靠性", run.reliabilityScore === null ? "--" : `${(run.reliabilityScore * 100).toFixed(1)}%`], ["依赖模型", run.modelVersion], ["总进度", `${run.progressPercent}%`], ["仿真时钟", `${run.simulatedMinutes} min`], ["预计剩余", `${run.estimatedRemainingMinutes} min`]];
  return <section className="rounded-2xl border border-[#dce4de] bg-[#173e32] p-6 text-white"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="text-xs text-emerald-100/60">阶段 02 · 仿真模拟</div><h1 className="mt-2 text-2xl font-semibold">虚拟产线运行终端</h1><p className="mt-2 text-sm text-emerald-50/70">运行 v{run.version} · {run.modelType} · {statusText[run.status]}</p></div><div className="grid grid-cols-2 gap-x-7 gap-y-3 text-right sm:grid-cols-5">{metrics.map(([label, value]) => <div key={label}><div className="text-[10px] text-emerald-100/55">{label}</div><div className="mt-1 max-w-28 truncate font-mono text-sm font-semibold" title={value}>{value}</div></div>)}</div></div><div className="mt-5 flex flex-wrap gap-2">{Object.entries(run.modelMetrics).map(([label, value]) => <span className="rounded border border-white/15 bg-white/5 px-2 py-1 font-mono text-[10px] text-emerald-50/75" key={label}>{label} {value}</span>)}</div>{run.failureReason ? <div className="mt-4 rounded-lg border border-rose-300/30 bg-rose-950/20 px-3 py-2 text-xs text-rose-100">异常：{run.failureReason}；最后成功环节：{run.lastSuccessfulStageId ?? "无"}；受影响版本：{run.affectedVersions.join("、")}</div> : null}<div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/15"><div className="h-full bg-[#79d0a5] transition-all" style={{ width: `${run.progressPercent}%` }} /></div></section>;
}

function AdmissionNotice({ run }: { run: ExperimentSimulationRun }) { return <section className="rounded-xl border border-amber-200 bg-amber-50 p-5"><div className="text-xs font-medium text-amber-800">仅允许查看产线结构</div><h2 className="mt-1 text-lg font-semibold text-slate-950">模型准入尚未通过，正式运行和临时试算已禁用</h2><ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-600">{run.admissionReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></section>; }

function StageButton({ stage, index, selected, onSelect }: { stage: SimulationRunStage; index: number; selected: boolean; onSelect: () => void }) { return <button className={`min-h-28 rounded-xl border p-3 text-left transition ${selected ? "border-[#397b5d] bg-[#f0f7f3] ring-1 ring-[#397b5d]" : "border-slate-200"}`} onClick={onSelect} type="button"><div className="font-mono text-[10px] text-slate-400">{String(index + 1).padStart(2, "0")}</div><div className="mt-2 text-xs font-semibold leading-5 text-slate-800">{stage.stageName}</div><span className={`mt-3 inline-flex rounded px-1.5 py-0.5 text-[9px] ${statusStyle[stage.status]}`}>{statusText[stage.status]}</span></button>; }

function VirtualProductionLine({ activeIndex, status }: { activeIndex: number; status: ExperimentSimulationRun["status"] }) {
  const equipment = [["原料罐", "物料准备"], ["反应设备", "核心过程"], ["下游单元", "分离处理"], ["收集罐", "产物收集"]];
  const mappedActive = activeIndex <= 1 ? -1 : activeIndex === 2 ? 0 : activeIndex === 3 ? 1 : activeIndex === 4 ? 2 : activeIndex >= 5 ? 3 : -1;
  return <section className="overflow-hidden rounded-2xl border border-[#dce4de] bg-[#f4f7f4] p-5"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-950">虚拟产线</h2><p className="mt-1 text-xs text-slate-500">设备与流向用于科研过程演示，不连接真实控制器。</p></div><span className="font-mono text-[10px] text-slate-400">DIGITAL LINE / MOCK</span></div><div className="mt-6 grid grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] items-center gap-2">{equipment.flatMap(([name, detail], index) => { const active = index === mappedActive && status === "running"; const completed = index < mappedActive || status === "completed"; const device = <div className={`relative rounded-2xl border px-3 py-7 text-center transition ${active ? "border-blue-400 bg-blue-50 shadow-[0_0_0_4px_rgba(59,130,246,.08)]" : completed ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white"}`} key={name}><div className={`mx-auto mb-3 h-14 w-12 rounded-b-xl rounded-t-md border-2 ${active ? "border-blue-500" : completed ? "border-emerald-500" : "border-slate-300"}`}><div className={`mt-5 h-5 ${active ? "animate-pulse bg-blue-200" : completed ? "bg-emerald-200" : "bg-slate-100"}`} /></div><div className="text-xs font-semibold text-slate-800">{name}</div><div className="mt-1 text-[10px] text-slate-400">{detail}</div></div>; const pipe = index < equipment.length - 1 ? <div className="flex items-center" key={`${name}-pipe`}><span className={`h-px w-5 ${completed || active ? "bg-emerald-500" : "bg-slate-300"}`} /><span className="text-xs text-slate-400">›</span></div> : null; return pipe ? [device, pipe] : [device]; })}</div></section>;
}

function StageInspector({ stage }: { stage: SimulationRunStage }) { const groups = [["环节输入", stage.inputSummary], ["模型与计算依据", stage.modelBasis], ["环节输出", stage.outputSummary.length ? stage.outputSummary : [stage.waitingReason ?? "等待执行"]]]; return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="flex items-start justify-between gap-3"><div><div className="text-xs text-slate-400">{stage.equipmentName}</div><h2 className="mt-1 text-lg font-semibold text-slate-950">{stage.stageName}</h2></div><span className={`rounded px-2 py-1 text-xs ${statusStyle[stage.status]}`}>{statusText[stage.status]} · {stage.progressPercent}%</span></div>{stage.waitingReason ? <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">等待原因：{stage.waitingReason}</div> : null}<div className="mt-4 grid gap-3 md:grid-cols-3">{groups.map(([label, items]) => <div className="rounded-xl bg-[#f6f8f6] p-4" key={label as string}><h3 className="text-xs font-semibold text-slate-700">{label}</h3><ul className="mt-2 space-y-1.5 text-xs leading-5 text-slate-500">{(items as string[]).map((item) => <li key={item}>— {item}</li>)}</ul></div>)}</div></section>; }

function ParameterPanel({ context, parameters, official, resetKey, canTrial, valid, busy, onEmptyChange, onUpdate, onCustomUpdate, onTrial }: { context: ExperimentWorkspaceOverview["productionContext"]; parameters: SimulationPredictRequest; official: SimulationPredictRequest; resetKey: string; canTrial: boolean; valid: boolean; busy: boolean; onEmptyChange: (field: string, empty: boolean) => void; onUpdate: <K extends keyof SimulationPredictRequest>(key: K, value: SimulationPredictRequest[K]) => void; onCustomUpdate: (key: string, value: number) => void; onTrial: () => void }) {
  const fields = [
    { key: "temperatureC", label: "温度", min: 20, max: 55, step: 0.1, unit: "℃" },
    { key: "ph", label: "pH", min: 4.5, max: 8.5, step: 0.01, unit: "pH" },
    { key: "stirringRpm", label: "搅拌速度", min: 0, max: 400, step: 1, unit: "rpm" },
    { key: "cultureHours", label: "培养时长", min: 12, max: 96, step: 1, unit: "小时" },
    { key: "anaerobicScore", label: "厌氧水平", min: 0, max: 1, step: 0.01, unit: "比例" },
    { key: "pressureMpa", label: "压力", min: 0, max: 450, step: 1, unit: "MPa" },
    { key: "carbonConcentration", label: "碳源浓度", min: 0, max: 4, step: 0.05, unit: "g/L" },
  ] as const;
  const customDefinitions = context.parameterDefinitions.filter((item) => !fields.some((field) => field.key === item.key));
  const editableCustomDefinitions = customDefinitions.filter((item) => item.min !== null && item.max !== null && item.defaultValue !== null);
  const uncalibratedCustomDefinitions = customDefinitions.filter((item) => !editableCustomDefinitions.includes(item));
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="text-xs font-medium text-[#2f7054]">临时参数试算</div><h2 className="mt-1 font-semibold text-slate-950">精确仪器参数</h2><p className="mt-2 text-xs leading-5 text-slate-500">修改只生成试算快照，不覆盖正式参数。输入框包含单位、范围和精度约束。</p>{uncalibratedCustomDefinitions.length ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3"><p className="text-xs font-medium text-amber-900">待校准或未接入的参数</p><div className="mt-2 flex flex-wrap gap-2">{uncalibratedCustomDefinitions.map((item) => <span className="rounded bg-white px-2 py-1 text-[10px] text-amber-900" key={item.key}>{item.label}{item.unit ? `（${item.unit}）` : ""} · 待校准</span>)}</div><p className="mt-2 text-[10px] leading-4 text-amber-800">完成范围校准和特征绑定后，才会开放进入试算。</p></div> : null}<div className="mt-4 grid grid-cols-2 gap-3">{fields.map((field) => { const definition = context.parameterDefinitions.find((item) => item.key === field.key); return <NumberField fieldKey={field.key} resetKey={resetKey} label={definition?.label ?? field.label} value={parameters[field.key]} official={official[field.key]} min={definition?.min ?? field.min} max={definition?.max ?? field.max} step={field.step} unit={definition?.unit ?? field.unit} onEmptyChange={onEmptyChange} onChange={(value) => onUpdate(field.key, value)} key={field.key} />; })}</div>{editableCustomDefinitions.length ? <div className="mt-4 border-t border-slate-100 pt-4"><p className="text-xs font-semibold text-slate-700">已校准自定义参数</p><div className="mt-3 grid grid-cols-2 gap-3">{editableCustomDefinitions.map((item) => <NumberField fieldKey={item.key} resetKey={resetKey} label={item.label} value={parameters.customParameters[item.key] ?? item.defaultValue as number} official={official.customParameters[item.key] ?? item.defaultValue as number} min={item.min as number} max={item.max as number} step={stepForUnit(item.unit)} unit={item.unit} onEmptyChange={onEmptyChange} onChange={(value) => onCustomUpdate(item.key, value)} key={item.key} />)}</div><p className="mt-2 text-[10px] text-slate-500">自定义值会写入试算快照；是否真正影响预测，取决于模型绑定状态。</p></div> : null}{!valid ? <div className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">存在必填项为空、超出范围或不符合精度的参数，请修正后再试算。</div> : null}<button className="mt-4 w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40" disabled={!canTrial || busy} onClick={onTrial} type="button">生成临时试算快照</button></section>;
}

function stepForUnit(unit: string): number { return unit === "pH" ? 0.01 : unit === "℃" ? 0.1 : 1; }

function NumberField({ fieldKey, resetKey, label, value, official, min, max, step, unit, onChange, onEmptyChange }: { fieldKey: string; resetKey: string; label: string; value: number; official: number; min: number; max: number; step: number; unit: string; onChange: (value: number) => void; onEmptyChange: (field: string, empty: boolean) => void }) { const [draft, setDraft] = useState(String(value)); useEffect(() => { setDraft(String(value)); onEmptyChange(fieldKey, false); }, [fieldKey, onEmptyChange, resetKey, value]); const changed = value !== official; const empty = draft.trim() === ""; return <label className="text-xs font-medium text-slate-600"><span className="flex justify-between"><span>{label}</span>{empty ? <span className="text-rose-700">必填</span> : changed ? <span className="text-amber-700">已修改</span> : null}</span><span className={`mt-2 flex h-10 overflow-hidden rounded-lg border bg-white focus-within:border-[#397b5d] ${empty ? "border-rose-300" : "border-slate-200"}`}><input aria-invalid={empty} className="min-w-0 flex-1 px-3 font-mono text-sm outline-none" max={max} min={min} onChange={(event) => { const raw = event.target.value; setDraft(raw); const isEmpty = raw.trim() === ""; onEmptyChange(fieldKey, isEmpty); const parsed = event.target.valueAsNumber; if (!isEmpty && !Number.isNaN(parsed)) onChange(parsed); }} step={step} type="number" value={draft} /><span className="flex min-w-12 items-center justify-center border-l border-slate-200 bg-slate-50 px-2 text-[10px] text-slate-500">{unit}</span></span><span className="mt-1 block text-[9px] font-normal text-slate-400">范围 {min}–{max} · 精度 {step}</span></label>; }

function TrialResult({ snapshot }: { snapshot: SimulationTrialSnapshot | null }) {
  if (!snapshot) return <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">等待临时试算或正式仿真结果</section>;
  const official = snapshot.snapshotId.startsWith("official-");
  const metrics = [["规则综合评分", snapshot.predictions.overallScore], ["生长辅助评分", snapshot.predictions.akkGrowthScore], ["代谢辅助评分", snapshot.predictions.scfaScore], ["分子量辅助值 kDa", snapshot.predictions.molecularWeightKda]];
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="flex items-start justify-between"><div><div className="text-xs font-medium text-[#2f7054]">{official ? "正式仿真结果" : "临时试算结果"}</div><h2 className="mt-1 font-semibold text-slate-950">{snapshot.snapshotId}</h2></div><span className={`rounded px-2 py-1 text-[10px] ${official ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>{official ? "正式运行快照" : "不写回正式版本"}</span></div><div className="mt-3 flex flex-wrap gap-2 text-xs"><span className="rounded bg-[#edf5f0] px-2 py-1 font-medium text-[#2f7054]">{snapshot.predictionSource === "promoted_model_composite" ? "已晋升模型预测" : "规则模型演示"}</span><span className="px-1 py-1 text-slate-600">预测置信度：<strong className="text-slate-900">{snapshot.confidence}</strong></span>{snapshot.extrapolated ? <span className="rounded bg-amber-50 px-2 py-1 font-medium text-amber-800">存在训练范围外推</span> : null}</div>{snapshot.modelTargets.length > 0 ? <div className="mt-4 space-y-2">{snapshot.modelTargets.map((target) => <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-3" key={`${target.modelVersion}-${target.targetField}`}><div className="flex items-start justify-between gap-3"><div><div className="text-[10px] text-emerald-700">数学模型目标 · {target.targetField}</div><div className="mt-1 font-mono text-xl font-semibold text-slate-950">{target.prediction.toFixed(4)}</div></div><div className="text-right font-mono text-[9px] leading-5 text-slate-500">{target.modelVersion}<br />{target.bindingVersion}</div></div><div className="mt-2 text-[10px] text-slate-500">近似 95% 区间 {target.interval.lower.toFixed(4)} – {target.interval.upper.toFixed(4)} · 未独立校准</div></div>)}</div> : null}<div className="mt-4 text-[10px] font-semibold uppercase tracking-wider text-slate-400">规则模型辅助指标</div><div className="mt-2 grid grid-cols-2 gap-2">{metrics.map(([label, value]) => <div className="rounded-lg bg-[#f6f8f6] p-3" key={label}><div className="text-[10px] text-slate-500">{label}</div><div className="mt-1 font-mono text-lg font-semibold text-slate-900">{value}</div></div>)}</div><div className="mt-4 text-xs font-semibold text-slate-700">相对正式参数</div><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-500">{snapshot.baselineDifferences.map((item) => <li key={item}>— {item}</li>)}</ul><ResultList title="具体风险" items={snapshot.risks} /><ResultList title="待验证指标" items={snapshot.validationIndicators} /><p className="mt-4 text-[10px] leading-5 text-amber-800">{snapshot.disclaimer}</p></section>;
}

function ResultList({ title, items }: { title: string; items: string[] }) { return <div className="mt-4"><h3 className="text-xs font-semibold text-slate-700">{title}</h3><ul className="mt-2 max-h-36 space-y-1 overflow-auto text-xs leading-5 text-slate-500">{items.map((item) => <li key={item}>— {item}</li>)}</ul></div>; }

function SimulationEvents({ run }: { run: ExperimentSimulationRun }) { return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="flex justify-between"><h2 className="font-semibold text-slate-950">仿真事件记录</h2><span className="font-mono text-[10px] text-slate-400">{run.events.length} EVENTS</span></div><div className="mt-4 space-y-3">{[...run.events].reverse().slice(0, 8).map((event) => <div className="border-l-2 border-emerald-300 pl-3" key={event.eventId}><div className="flex items-center justify-between gap-3"><div className="text-xs font-medium text-slate-800">{event.title}</div><time className="font-mono text-[9px] text-slate-400">{formatEventTime(event.createdAt)}</time></div><div className="mt-1 text-[9px] text-slate-400">环节：{event.stageId ?? "全局"}</div><div className="mt-1 text-[10px] leading-5 text-slate-500">{event.detail}</div></div>)}{run.events.length === 0 ? <div className="text-xs text-slate-400">等待正式仿真运行创建。</div> : null}</div></section>; }

function formatEventTime(value: string) { const date = new Date(value); return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(date); }
