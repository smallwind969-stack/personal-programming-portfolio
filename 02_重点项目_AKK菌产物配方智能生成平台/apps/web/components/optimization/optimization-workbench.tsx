"use client";

import { useState } from "react";
import { advanceOptimizationRun, createOptimizationRun, restartDemoOptimizationRun, reviewOptimizationRun, selectOptimizationCandidate, submitOptimizationRun } from "@/lib/api";
import { ExperimentOptimizationRun, OptimizationParameters, optimizationParametersSchema } from "@/lib/schemas";

const statusLabel: Record<string, string> = { waiting: "等待启动", draft: "方案编辑", running: "约束搜索复核中", needsReview: "等待人工审核", completed: "已完成", stopped: "已停止", failed: "失败" };
type Draft = Record<keyof OptimizationParameters, string>;

export function OptimizationWorkbench({ experimentId, initialRun, demoMode = false }: { experimentId: string; initialRun: ExperimentOptimizationRun; demoMode?: boolean }) {
  const [run, setRun] = useState(initialRun);
  const [draft, setDraft] = useState<Draft>(() => parameterDraft(initialRun.editedParameters));
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = run.editedParameters ? Object.entries(run.editedParameters).some(([key, value]) => draft[key as keyof Draft] !== String(value)) : true;
  const modelDriven = run.searchMode === "promoted_model_constrained";

  async function act(action: () => Promise<ExperimentOptimizationRun>) {
    setBusy(true); setError(null);
    try { setRun(await action()); } catch (value) { setError(value instanceof Error ? value.message : "操作失败"); }
    finally { setBusy(false); }
  }
  function choose(plan: ExperimentOptimizationRun["candidatePlans"][number]) {
    setDraft({ temperatureC: String(plan.parameters.temperatureC), ph: String(plan.parameters.ph), cultureHours: String(plan.parameters.cultureHours), stirringRpm: String(plan.parameters.stirringRpm) });
    void act(() => selectOptimizationCandidate(experimentId, run.runId, plan.planId, plan.parameters));
  }
  function save() {
    if (Object.values(draft).some((value) => !value.trim()) || !run.selectedPlanId) { setError("请先选择方案并完整填写参数"); return; }
    const parsed = optimizationParametersSchema.safeParse(Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, Number(value)])));
    if (!parsed.success) { setError("参数超出允许范围或精度不正确"); return; }
    void act(() => selectOptimizationCandidate(experimentId, run.runId, run.selectedPlanId!, parsed.data));
  }

  return <div className="space-y-5">
    <section className="rounded-2xl border border-[#dce4de] bg-white p-6">
      <div className="flex flex-wrap justify-between gap-4"><div><p className="text-xs text-[#2f7054]">阶段 03 · 工艺优化闭环</p><h1 className="mt-2 text-2xl font-semibold">工艺优化</h1><p className="mt-2 text-sm text-slate-600">{demoMode ? "三套规则方案 → 精确调参 → 风险复核 → 人工验收。所有数值仅用于流程演示。" : "三套模型约束方案 → 精确调参 → 可靠性复核 → 人工验收 → 现实数据回流。只有真实实验数据回流后才会重训模型。"}</p></div><div className="flex h-fit items-center gap-2"><b className="rounded-xl bg-[#173f32] px-4 py-3 text-sm text-white">{statusLabel[run.status]} · {run.progressPercent}%</b>{demoMode && <button disabled={busy} onClick={() => void act(() => restartDemoOptimizationRun(experimentId, run.runId))} className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 disabled:opacity-35">重新开始演示</button>}</div></div>
      <div className="mt-5 grid gap-3 md:grid-cols-4"><Tile label={demoMode ? "演示模型血缘" : "当前晋升模型"} value={run.baseModelVersion}/><Tile label={demoMode ? "演示仿真结果" : "正式仿真结果"} value={run.baseResultVersion}/><Tile label={demoMode ? "演示参数版本" : "正式工艺参数"} value={run.officialParameterVersion ?? "审核后生成"}/><Tile label={demoMode ? "演示结果版本" : "预测结果版本"} value={run.newResultVersion ?? "审核后生成"}/></div>
      {modelDriven ? <div className="mt-4 grid gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-950 sm:grid-cols-3"><Metric label="搜索模式" value="已晋升模型约束搜索"/><Metric label="可行组合" value={String(run.searchEvaluations)}/><Metric label="绑定版本" value={run.baseBindingVersions.join("、") || "待锁定"}/><p className="sm:col-span-3">父仿真：{run.baseSimulationRunId} · 模型权重保持只读，本步骤不会伪造重训结果。</p></div> : null}
      <div className={`mt-4 rounded-xl border p-4 text-sm ${run.requirementDriven ? "border-emerald-200 bg-emerald-50 text-emerald-950" : "border-slate-200 bg-slate-50 text-slate-600"}`}><b>{run.requirementDriven ? `产品需求驱动 · V${run.productRequirementVersion}` : "未引用已确认产品需求"}</b><p className="mt-1 text-xs">{run.requirementDriven ? `${run.productRequirementWorkingName} · ${run.productRequirementVersionId}` : "当前保持历史演示兼容；可先在产品创新中确认需求版本。"}</p>{run.productRequirementContentHash ? <p className="mt-1 break-all text-[10px] opacity-70">{run.productRequirementContentHash}</p> : null}</div>
      {!run.admissionAllowed && <p className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">尚未解锁，可预览方案；需先完成前序仿真与确认。{run.admissionReasons.join("；")}</p>}
      {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {run.status === "waiting" && <button disabled={!run.admissionAllowed || busy} onClick={() => void act(() => createOptimizationRun(experimentId))} className="mt-5 rounded-lg bg-[#174333] px-5 py-2.5 text-sm text-white disabled:opacity-35">启动工艺优化</button>}
    </section>

    <section className="grid gap-4 xl:grid-cols-3">{run.candidatePlans.map((plan) => <article key={plan.planId} className={`rounded-2xl border bg-white p-5 ${run.selectedPlanId === plan.planId ? "border-[#246448] ring-2 ring-[#246448]/10" : "border-[#dce4de]"}`}>
      <div className="flex justify-between"><h2 className="font-semibold">{plan.displayName}</h2><strong className="text-xl text-[#27694d]">{plan.scoreBreakdown.overall?.toFixed(1)}</strong></div>
      <p className="mt-2 text-sm leading-6 text-slate-600">{plan.summary}</p>
      <div className="mt-3 grid grid-cols-4 gap-1">{Object.entries(plan.scoreBreakdown).map(([key,value]) => <Metric key={key} label={key} value={value.toFixed(1)}/>)}</div>
      <ResponseSurface points={plan.responseSurface}/>
      <div className="mt-3 grid grid-cols-3 gap-2">{Object.entries(plan.baselineImprovements).map(([key,value]) => <Metric key={key} label={`较基线 ${key}`} value={`${value > 0 ? "+" : ""}${value}`}/>)}</div>
      <p className="mt-3 text-xs text-slate-500">{demoMode ? "规则演示稳定度" : "置信度"} {(plan.confidenceScore * 100).toFixed(1)}% · {plan.predictionIntervals[0]}</p>
      {plan.modelEvidence.map((evidence) => <div className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3" key={`${plan.planId}-${evidence.targetField}`}><div className="text-[10px] text-emerald-700">数学模型目标 · {evidence.targetField}</div><div className="mt-1 font-mono text-xl font-semibold">{evidence.prediction.toFixed(6)}</div><div className="mt-1 font-mono text-[9px] leading-5 text-slate-500">{evidence.modelVersion}<br/>{evidence.bindingVersion}</div><div className="mt-1 text-[10px] text-slate-500">经验区间 {evidence.intervalLower.toFixed(6)} – {evidence.intervalUpper.toFixed(6)}</div></div>)}
      <Details title="推导依据" items={plan.explanation}/><Details title="具体风险" items={plan.riskItems}/><Details title="验证指标" items={plan.validationItems}/>
      <button disabled={run.status !== "draft" || busy} onClick={() => choose(plan)} className="mt-4 w-full rounded-lg border border-[#174333] py-2 text-sm text-[#174333] disabled:opacity-35">选择此方案</button>
    </article>)}</section>

    {run.status !== "waiting" && <div className="grid gap-5 xl:grid-cols-2">
      <section className="rounded-2xl border border-[#dce4de] bg-white p-6"><h2 className="font-semibold">{demoMode ? "精确参数与演示提交" : "精确参数与正式提交"}</h2><p className="mt-1 text-xs text-slate-500">输入变化后必须先保存；超出训练范围的参数会被后端拒绝。</p><div className="mt-4 grid grid-cols-2 gap-3">{([['temperatureC','温度（℃）'],['ph','pH'],['cultureHours','培养时间（小时）'],['stirringRpm','搅拌速度（rpm）']] as const).map(([key,label]) => <label key={key} className="text-xs text-slate-600">{label}<input disabled={run.status !== "draft"} value={draft[key]} onChange={(event) => setDraft((current) => ({ ...current, [key]: event.target.value }))} className="mt-2 h-10 w-full rounded-lg border px-3 text-sm disabled:bg-slate-50"/></label>)}</div>{run.status === "draft" && <div className="mt-4 flex gap-3"><button disabled={busy} onClick={save} className="rounded-lg border border-[#174333] px-4 py-2 text-sm disabled:opacity-35">保存参数</button><button disabled={!run.editedParameters || dirty || busy} onClick={() => void act(() => submitOptimizationRun(experimentId, run.runId))} className="rounded-lg bg-[#174333] px-4 py-2 text-sm text-white disabled:opacity-35">{demoMode ? "提交演示方案并复核" : "正式提交并复核"}</button>{dirty && run.editedParameters && <span className="self-center text-xs text-amber-700">参数已修改，请先保存</span>}</div>}{run.submittedParameters && <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm">参数已冻结 · {modelDriven ? "模型与绑定血缘已锁定" : `数据版本 ${run.trainingDataVersion}`}</p>}</section>
      <section className="rounded-2xl border border-[#dce4de] bg-white p-6"><div className="flex justify-between"><h2 className="font-semibold">优化复核进程</h2>{run.status === "running" && <button disabled={busy} onClick={() => void act(() => advanceOptimizationRun(experimentId, run.runId))} className="rounded-lg bg-[#174333] px-3 py-2 text-xs text-white disabled:opacity-35">推进下一环节</button>}</div><div className="mt-4 space-y-2">{run.retrainingStages.map((stage,index) => <div key={stage.stageId} className="rounded-xl bg-slate-50 p-3 text-sm"><b>{index + 1}. {stage.stageName}</b><span className="ml-2 text-xs text-[#2f7054]">{statusLabel[stage.status]}</span><p className="mt-1 text-xs text-slate-500">{demoMode ? demoText(stage.detail) : stage.detail}</p>{stage.outputSummary.map((item) => <p key={item} className="mt-1 text-xs text-slate-600">· {demoMode ? demoText(item) : item}</p>)}</div>)}</div></section>
    </div>}

    {run.searchMetrics.length > 0 && <section className="rounded-2xl border border-[#dce4de] bg-white p-6"><h2 className="font-semibold">模型约束搜索证据</h2><div className="mt-4 grid gap-2 md:grid-cols-3">{run.searchMetrics.map((metric) => <div key={metric.strategyKey} className="rounded-xl bg-emerald-50 p-4"><p className="text-xs text-slate-500">{metric.strategyKey}</p><b className="mt-1 block text-sm">最优目标 {metric.bestObjective.toFixed(4)}</b><p className="mt-1 text-xs">预测 {metric.bestPrediction.toFixed(6)} · 可行 {metric.feasibleCount}/{metric.evaluatedCount}</p></div>)}</div></section>}
    {run.trainingMetrics.length > 0 && !modelDriven && <section className="rounded-2xl border border-[#dce4de] bg-white p-6"><h2 className="font-semibold">规则演示迭代证据</h2><div className="mt-4 grid grid-cols-5 gap-2">{run.trainingMetrics.map((metric) => <div key={metric.round} className={`rounded-xl p-3 ${metric.retained ? "bg-emerald-50" : "bg-slate-50"}`}><p className="text-xs text-slate-500">第 {metric.round} 轮</p><b className="mt-1 block text-sm">验证 {metric.validationScore.toFixed(3)}</b><p className="text-xs">损失 {metric.trainingLoss.toFixed(4)} · {metric.retained ? "保留" : "淘汰"}</p></div>)}</div></section>}

    {run.status === "needsReview" && <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6"><h2 className="font-semibold">人工验收关口</h2><p className="mt-2 text-sm">{demoMode ? "审核前不会生成演示参数或演示结果版本；批准后仍不会写入正式模型和实验资产。" : "审核前不会生成正式工艺参数或预测结果版本；当前没有新增真实标签，因此不会生成新模型。"}</p><div className="mt-4 grid gap-3 md:grid-cols-[220px_1fr]"><input value={operator} onChange={(event) => setOperator(event.target.value)} className="h-10 rounded-lg border px-3"/><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="审核依据（至少2个字）" className="h-10 rounded-lg border px-3"/></div><div className="mt-4 flex gap-3"><button disabled={busy || reason.trim().length < 2} onClick={() => void act(() => reviewOptimizationRun(experimentId, run.runId, "approved", reason, operator))} className="rounded-lg bg-[#174333] px-4 py-2 text-sm text-white disabled:opacity-35">{demoMode ? "批准演示参数版本" : "批准工艺参数版本"}</button><button disabled={busy || reason.trim().length < 2} onClick={() => void act(() => reviewOptimizationRun(experimentId, run.runId, "rejected", reason, operator))} className="rounded-lg border px-4 py-2 text-sm disabled:opacity-35">驳回</button></div></section>}

    {run.resultSummary && <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6"><h2 className="font-semibold">{demoMode ? "演示结果版本已生成 · 规则稳定度" : "新结果版本已生成 · 置信度"} {(run.resultSummary.confidenceScore * 100).toFixed(1)}%</h2><div className="mt-4 grid gap-4 md:grid-cols-3"><Details title="预测结果" items={run.resultSummary.predictedOutcomes}/><Details title="具体风险" items={run.resultSummary.riskItems}/><Details title="必须验证" items={run.resultSummary.validationItems}/></div><p className="mt-4 text-xs text-slate-500">{run.resultSummary.disclaimer}</p></section>}

    <section className="grid gap-5 xl:grid-cols-2"><Audit title="运行事件" items={run.events.map((event) => demoMode ? demoText(`${new Date(event.createdAt).toLocaleString("zh-CN")} · ${event.title} · ${event.detail}`) : `${new Date(event.createdAt).toLocaleString("zh-CN")} · ${event.title} · ${event.detail}`)}/><Audit title="人工决策" items={run.humanDecisions.map((decision) => `${decision.operator} · ${decision.decision} · ${decision.reason} · 影响：${decision.impactScope.join("、")}`)}/></section>
  </div>;
}

function ResponseSurface({ points }: { points: ExperimentOptimizationRun["candidatePlans"][number]["responseSurface"] }) { const min = Math.min(...points.map((point) => point.predictedScore)); return <div className="mt-4"><p className="text-xs text-slate-500">温度—pH 响应面切片</p><div className="mt-2 flex h-20 items-end gap-2 overflow-hidden">{points.map((point) => <div key={`${point.temperatureC}-${point.ph}`} className="flex-1 rounded-t bg-[#2f7054]" style={{ height: `${Math.min(100, Math.max(18, (point.predictedScore - min + 8) * 5))}%` }} title={`${point.temperatureC}℃ / pH ${point.ph} / 预测 ${point.predictedValue ?? point.predictedScore}`}/>)}</div><div className="mt-1 flex justify-between text-[10px] text-slate-500"><span>{points[0].temperatureC}℃</span><span>{points.at(-1)?.temperatureC}℃</span></div></div>; }
function Tile({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 truncate text-sm font-medium">{value}</p></div>; }
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-slate-50 p-2"><span className="text-[10px] text-slate-500">{label}</span><p className="text-xs font-medium">{value}</p></div>; }
function Details({ title, items }: { title: string; items: string[] }) { return <details className="mt-3"><summary className="cursor-pointer text-xs font-medium text-slate-700">{title}（{items.length}）</summary><ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>{item}</li>)}</ul></details>; }
function Audit({ title, items }: { title: string; items: string[] }) { return <section className="rounded-2xl border border-[#dce4de] bg-white p-6"><h2 className="font-semibold">{title}</h2>{items.length ? <ol className="mt-4 space-y-2">{items.map((item,index) => <li key={`${index}-${item}`} className="rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">{item}</li>)}</ol> : <p className="mt-4 text-sm text-slate-400">暂无记录</p>}</section>; }
function demoText(value: string) { return value.replaceAll("正式仿真结果", "演示仿真结果").replaceAll("正式工艺参数与预测结果版本", "演示参数与结果版本").replaceAll("正式实验版本", "正式实验资产").replaceAll("正式优化任务", "演示优化任务").replaceAll("新训练数据版本", "隔离演示数据版本"); }
function parameterDraft(parameters: OptimizationParameters | null | undefined): Draft { return parameters ? { temperatureC: String(parameters.temperatureC), ph: String(parameters.ph), cultureHours: String(parameters.cultureHours), stirringRpm: String(parameters.stirringRpm) } : { temperatureC: "", ph: "", cultureHours: "", stirringRpm: "" }; }
