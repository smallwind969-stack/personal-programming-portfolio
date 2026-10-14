"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import type { DataAnalysisProgress } from "@/lib/schemas";

const statusLabels = {
  waiting: "等待上游",
  running: "可以开始",
  needsReview: "待人工确认",
  completed: "已完成",
  blocked: "已阻塞",
} as const;

const statusClasses = {
  waiting: "bg-slate-100 text-slate-500",
  running: "bg-blue-100 text-blue-800",
  needsReview: "bg-amber-100 text-amber-900",
  completed: "bg-emerald-100 text-emerald-800",
  blocked: "bg-rose-100 text-rose-800",
} as const;

export function DataAnalysisProgressPanel({ progress }: { progress: DataAnalysisProgress }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const current = progress.steps.find((step) => step.current) ?? null;

  return <section className="rounded-2xl border border-[#cfdcd4] bg-white p-5" aria-label="数据分析推进清单">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><div className="text-xs font-semibold tracking-[0.14em] text-[#397b5d]">数据分析 · 六步闭环</div><h2 className="mt-1 text-xl font-semibold text-slate-950">实验推进清单</h2><p className="mt-2 text-xs text-slate-500">当前动作：{progress.currentAction}</p></div>
      <div className="flex items-center gap-3"><div className="text-right"><div className="font-mono text-2xl font-semibold text-[#24664a]">{progress.progressPercent}%</div><div className="text-[10px] text-slate-400">数据分析总体进度</div></div><button className="rounded-lg border border-[#cad8cf] px-3 py-2 text-xs text-[#174333] disabled:opacity-50" disabled={pending} onClick={() => startTransition(() => router.refresh())} type="button">{pending ? "刷新中…" : "刷新进度"}</button></div>
    </div>
    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[#397b5d] transition-all" style={{ width: `${progress.progressPercent}%` }} /></div>
    <ol className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{progress.steps.map((step) => <li className={`rounded-xl border p-4 ${step.current ? "border-[#397b5d] bg-[#f1f7f3] ring-2 ring-[#397b5d]/10" : "border-[#e0e7e2] bg-[#fafbfa]"}`} key={step.stepKey}><div className="flex items-center justify-between gap-2"><span className="font-mono text-[10px] text-slate-400">0{step.sequence}</span><span className={`rounded-full px-2 py-1 text-[10px] ${statusClasses[step.status]}`}>{statusLabels[step.status]}</span></div><h3 className="mt-3 text-sm font-semibold text-slate-900">{step.label}</h3><p className="mt-2 min-h-10 text-xs leading-5 text-slate-600">{step.summary}</p><div className="mt-2 text-[10px] text-slate-400">证据 {step.evidenceRefs.length} 项</div>{step.blockedReasons.length > 0 ? <ul className="mt-2 text-[10px] leading-5 text-amber-800">{step.blockedReasons.map((reason) => <li key={reason}>· {reason}</li>)}</ul> : null}<a className={`mt-3 inline-flex text-xs font-medium ${step.status === "waiting" ? "pointer-events-none text-slate-400" : "text-[#174333] hover:underline"}`} href={step.anchor}>{step.actionLabel} →</a></li>)}</ol>
    {current ? <p className="mt-4 rounded-lg bg-[#f4f7f4] px-3 py-2 text-xs text-slate-600">当前停在第 {current.sequence} 步“{current.label}”；系统不会自动替你提交人工确认。</p> : <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800">数据分析六步均已完成，可以进入仿真准入检查。</p>}
    <p className="mt-3 text-[10px] leading-5 text-slate-400">{progress.disclaimer}</p>
  </section>;
}
