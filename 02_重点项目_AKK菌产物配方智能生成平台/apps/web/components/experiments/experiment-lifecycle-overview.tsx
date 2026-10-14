import Link from "next/link";

import type { ExperimentLifecycleOverview, ExperimentLifecycleStage } from "@/lib/schemas";

const statusLabels = {
  waiting: "等待上游", running: "进行中", needsReview: "等待人工处理",
  completed: "已完成", failed: "需要处理", notRequired: "本轮不需要",
};
const statusClasses = {
  waiting: "border-slate-200 bg-slate-50 text-slate-600",
  running: "border-blue-200 bg-blue-50 text-blue-800",
  needsReview: "border-amber-200 bg-amber-50 text-amber-800",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  failed: "border-rose-200 bg-rose-50 text-rose-800",
  notRequired: "border-slate-200 bg-white text-slate-500",
};

export function ExperimentLifecycleOverviewCard({ lifecycle }: { lifecycle: ExperimentLifecycleOverview }) {
  return <section className="mt-6 rounded-xl border border-[#dce4de] bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-medium text-[#2f7054]">研发验证闭环</p><h2 className="mt-1 text-lg font-semibold text-slate-900">当前：{lifecycle.currentStageLabel}</h2><p className="mt-2 text-xs leading-5 text-slate-500">实验数据→模型复核→仿真映射→工艺优化→现实验证→反馈重训练，所有节点均来自真实状态与版本血缘。</p></div><div className="min-w-36"><div className="flex justify-between text-xs text-slate-500"><span>闭环进度</span><b className="font-mono text-[#174333]">{lifecycle.progressPercent}%</b></div><div className="mt-2 h-1.5 overflow-hidden rounded bg-slate-100"><div className="h-full bg-[#397b5d]" style={{ width: `${lifecycle.progressPercent}%` }}/></div></div></div>
    <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{lifecycle.stages.map((stage, index) => <LifecycleStageCard key={stage.stageKey} stage={stage} index={index} current={stage.stageKey === lifecycle.currentStageKey}/>)}</div>
    <p className="mt-4 text-[10px] leading-5 text-slate-400">{lifecycle.disclaimer}</p>
  </section>;
}

function LifecycleStageCard({ stage, index, current }: { stage: ExperimentLifecycleStage; index: number; current: boolean }) {
  const body = <><div className="flex items-center justify-between gap-3"><span className="font-mono text-[10px] text-slate-400">{String(index + 1).padStart(2, "0")}</span><span className={`rounded-full border px-2 py-0.5 text-[10px] ${statusClasses[stage.status]}`}>{statusLabels[stage.status]}</span></div><h3 className="mt-3 text-sm font-semibold text-slate-900">{stage.label}</h3><p className="mt-2 text-xs leading-5 text-slate-600">{stage.summary}</p><div className="mt-3 h-1 overflow-hidden rounded bg-slate-100"><div className={`h-full ${stage.status === "failed" ? "bg-rose-500" : stage.status === "needsReview" ? "bg-amber-500" : "bg-[#397b5d]"}`} style={{ width: `${stage.progressPercent}%` }}/></div>{stage.waitingReasons.length > 0 && <ul className="mt-3 space-y-1 text-[11px] leading-4 text-amber-800">{stage.waitingReasons.slice(0, 2).map((reason) => <li key={reason}>· {reason}</li>)}</ul>}{stage.evidenceRefs.length > 0 && <details className="mt-3"><summary className="cursor-pointer text-[10px] text-slate-500">证据版本 {stage.evidenceRefs.length} 项</summary><ul className="mt-2 space-y-1 break-all font-mono text-[9px] text-slate-400">{stage.evidenceRefs.map((item) => <li key={item}>{item}</li>)}</ul></details>}{stage.canEnter && <div className="mt-3 text-xs font-medium text-[#174333]">{stage.actionLabel} →</div>}</>;
  const classes = `rounded-xl border p-4 transition ${current ? "border-[#397b5d] bg-[#f3f8f5] ring-2 ring-[#397b5d]/10" : "border-slate-200 bg-white"}`;
  return stage.canEnter ? <Link className={classes} href={stage.route}>{body}</Link> : <article className={classes}>{body}</article>;
}
