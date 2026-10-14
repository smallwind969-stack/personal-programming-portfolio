"use client";

import { useEffect, useState } from "react";
import { createResultInterpretationRun } from "@/lib/api";
import type { ResultInterpretationRun } from "@/lib/schemas";

const metricLabel = { mae: "MAE", rmse: "RMSE", r2: "R²" } as const;

export function ResultInterpretationRunCard({ experimentId, agentRunId = "workspace" }: { experimentId: string; agentRunId?: string }) {
  const [run, setRun] = useState<ResultInterpretationRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    createResultInterpretationRun(experimentId, `result-interpretation-${agentRunId}`).then(setRun).catch((cause) => setError(cause instanceof Error ? cause.message : "无法读取结果解释"));
  }, [agentRunId, experimentId]);
  if (error) return <section className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">{error}</section>;
  if (!run) return <section className="rounded-2xl border border-[#dce4de] bg-white p-5 text-sm text-slate-500">正在读取权威指标与解释快照……</section>;
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><div className="text-xs font-medium text-[#2f7054]">实验结果研判</div><h2 className="mt-1 text-lg font-semibold text-slate-950">{run.mode === "llm_assisted" ? "证据化语义解释" : "确定性解释回退"}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{run.overallSummary}</p></div><span className="rounded-md bg-slate-100 px-2 py-1 font-mono text-xs text-slate-600">{run.provider} · {run.model}</span></div>
    {run.fallbackReason ? <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">本地模型未参与本次解释：{run.fallbackReason}</div> : null}
    <div className="mt-5 grid gap-3 md:grid-cols-3">{run.metricInterpretations.map((item) => <div className="rounded-xl bg-[#f3f7f4] p-4" key={item.metricKey}><div className="text-xs text-slate-500">权威指标 · {metricLabel[item.metricKey]}</div><div className="mt-1 font-mono text-2xl font-semibold text-slate-950">{item.value.toFixed(3)}</div><p className="mt-3 text-xs leading-5 text-slate-600">{item.interpretation}</p><div className="mt-2 font-mono text-[10px] text-slate-400">{item.evidenceRefs.join(" · ")}</div></div>)}</div>
    <div className="mt-5 grid gap-4 lg:grid-cols-2"><List title="已有风险解释" items={run.riskExplanations.map((item) => `${item.originalRisk}｜${item.explanation}`)} /><List title="仍待人工判断" items={run.unresolvedQuestions} /></div>
    <div className="mt-5"><h3 className="text-sm font-semibold text-slate-900">下一轮研发实验建议</h3><div className="mt-3 grid gap-3 md:grid-cols-2">{run.nextExperimentSuggestions.map((item) => <article className="rounded-xl border border-slate-200 p-4" key={item.title}><div className="flex items-center justify-between gap-2"><h4 className="text-sm font-semibold text-slate-900">{item.title}</h4><span className="text-[10px] text-amber-700">需人工复核</span></div><p className="mt-2 text-xs leading-5 text-slate-600">{item.purpose}</p><ul className="mt-3 space-y-1 text-xs text-slate-500">{item.validationItems.map((value) => <li key={value}>· {value}</li>)}</ul></article>)}</div></div>
    <div className="mt-5 rounded-lg bg-[#f2f6f3] px-3 py-2 text-xs leading-5 text-slate-600">解释文本不会改变 MAE、RMSE、R²、模型版本或仿真准入状态；所有建议仅作为研发实验建议。</div>
  </section>;
}

function List({ title, items }: { title: string; items: string[] }) { return <div className="rounded-xl border border-slate-200 p-4"><h3 className="text-xs font-semibold text-slate-700">{title}</h3><ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">{items.length ? items.map((item) => <li key={item}>· {item}</li>) : <li>暂无</li>}</ul></div>; }
