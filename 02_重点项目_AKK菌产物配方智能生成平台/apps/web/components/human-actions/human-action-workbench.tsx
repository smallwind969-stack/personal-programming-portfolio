"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { HumanActionCenter } from "@/lib/schemas";

const stageLabels: Record<string, string> = {
  dataAnalysis: "数据分析", modelEvaluation: "模型可靠性", supplementaryDesign: "补充实验设计",
  supplementaryExecution: "补充实验执行", measurementFeedback: "真实测量反馈", feedbackRetraining: "反馈重训练",
};
const actionLabels: Record<string, string> = {
  reviewReliability: "可靠性复核", generateDesign: "生成补充方案", reviewDesign: "补充方案审批",
  createExecution: "创建执行批次", continueExecution: "继续实验执行", createMeasurement: "创建测量任务",
  enterMeasurements: "录入真实测量", reviewMeasurements: "真实测量复核", createRetraining: "创建反馈重训练",
  reviewRetraining: "候选模型晋升复核",
};
const priorityLabels = { high: "高优先级", medium: "中优先级", normal: "常规" } as const;

export function HumanActionWorkbench({ initialCenter }: { initialCenter: HumanActionCenter }) {
  const [priority, setPriority] = useState("all");
  const [stage, setStage] = useState("all");
  const [experiment, setExperiment] = useState("all");
  const [query, setQuery] = useState("");
  const experiments = useMemo(() => Array.from(new Map(initialCenter.items.map((item) => [item.experimentId, item.experimentName]))), [initialCenter.items]);
  const visible = useMemo(() => initialCenter.items.filter((item) => {
    const keyword = query.trim().toLocaleLowerCase("zh-CN");
    return (priority === "all" || item.priority === priority)
      && (stage === "all" || item.stageKey === stage)
      && (experiment === "all" || item.experimentId === experiment)
      && (!keyword || `${item.title} ${item.detail} ${item.experimentName}`.toLocaleLowerCase("zh-CN").includes(keyword));
  }), [experiment, initialCenter.items, priority, query, stage]);
  const high = visible.filter((item) => item.priority === "high").length;

  return <main className="mx-auto max-w-7xl space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-medium text-[#397b5d]">研发负责人工作台</p><h1 className="mt-1 text-3xl font-semibold tracking-[-0.035em] text-slate-950">人工操作中心</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">集中查看需要人工判断的门禁、补充实验和反馈重训练事项。点击事项后，在对应实验工作台完成确认。</p></div><div className="flex gap-2"><Link className="rounded-lg border border-[#cbd8d0] bg-white px-4 py-2 text-sm text-[#174333]" href="/runs">运行记录</Link><Link className="rounded-lg bg-[#174333] px-4 py-2 text-sm text-white" href="/">实验归档</Link></div></header>

    <section className="grid gap-3 sm:grid-cols-3"><Metric label="当前待处理" value={initialCenter.totalCount} detail={`涉及 ${initialCenter.experimentCount} 项实验`} /><Metric label="筛选后事项" value={visible.length} detail="随筛选条件实时更新" /><Metric label="高优先级" value={high} detail="可靠性、测量或模型晋升门禁" /></section>

    <section className="rounded-2xl border border-[#dce4de] bg-white p-4"><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[1.4fr_1fr_1fr_1fr_auto]">
      <label><span className="sr-only">搜索事项</span><input className="h-11 w-full rounded-lg border border-[#dce4de] px-3 text-sm outline-none focus:border-[#397b5d]" onChange={(event) => setQuery(event.target.value)} placeholder="搜索实验、事项或说明……" value={query}/></label>
      <Select label="优先级" onChange={setPriority} value={priority}><option value="all">全部优先级</option><option value="high">高优先级</option><option value="medium">中优先级</option><option value="normal">常规</option></Select>
      <Select label="研发环节" onChange={setStage} value={stage}><option value="all">全部研发环节</option>{Object.entries(stageLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select>
      <Select label="实验" onChange={setExperiment} value={experiment}><option value="all">全部实验</option>{experiments.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</Select>
      <button className="h-11 rounded-lg border border-[#dce4de] px-4 text-sm text-slate-600" onClick={() => { setPriority("all"); setStage("all"); setExperiment("all"); setQuery(""); }} type="button">清除筛选</button>
    </div></section>

    <section className="grid gap-4 lg:grid-cols-2">{visible.length ? visible.map((item) => <article className="rounded-2xl border border-[#dce4de] bg-white p-5" key={item.actionId}><div className="flex flex-wrap items-center justify-between gap-2"><div className="flex gap-2"><span className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${item.priority === "high" ? "bg-rose-50 text-rose-700" : item.priority === "medium" ? "bg-amber-50 text-amber-800" : "bg-slate-100 text-slate-600"}`}>{priorityLabels[item.priority]}</span><span className="rounded-full bg-[#edf5f0] px-2.5 py-1 text-[10px] text-[#246247]">{stageLabels[item.stageKey]}</span></div><span className="text-[10px] text-slate-400">{actionLabels[item.actionType]}</span></div><h2 className="mt-4 text-lg font-semibold text-slate-900">{item.title}</h2><p className="mt-1 text-xs font-medium text-[#397b5d]">{item.experimentName}</p><p className="mt-3 text-sm leading-6 text-slate-600">{item.detail}</p>{item.blockedReasons.length ? <div className="mt-3 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-900">{item.blockedReasons.map((reason) => <p key={reason}>等待：{reason}</p>)}</div> : null}<div className="mt-5 flex items-center justify-between border-t border-[#edf0ee] pt-4"><code className="max-w-[65%] truncate text-[10px] text-slate-400" title={item.sourceRef}>{item.sourceRef}</code><Link className="rounded-lg bg-[#174333] px-4 py-2 text-xs font-medium text-white" href={item.route}>前往处理 →</Link></div></article>) : <div className="col-span-full rounded-2xl border border-[#dce4de] bg-white p-12 text-center"><h2 className="font-semibold text-slate-800">当前筛选下没有待处理事项</h2><p className="mt-2 text-sm text-slate-500">可以清除筛选，或返回实验归档继续推进工作流。</p></div>}</section>
    <p className="text-center text-[11px] text-slate-400">{initialCenter.disclaimer}</p>
  </main>;
}

function Metric({ detail, label, value }: { detail: string; label: string; value: number }) { return <article className="rounded-2xl border border-[#dce4de] bg-white p-5"><p className="text-xs text-slate-500">{label}</p><p className="mt-3 font-mono text-3xl font-semibold text-slate-950">{value}</p><p className="mt-2 text-xs text-slate-500">{detail}</p></article>; }
function Select({ children, label, onChange, value }: { children: React.ReactNode; label: string; onChange: (value: string) => void; value: string }) { return <label><span className="sr-only">{label}</span><select className="h-11 w-full rounded-lg border border-[#dce4de] bg-white px-3 text-sm text-slate-700 outline-none focus:border-[#397b5d]" onChange={(event) => onChange(event.target.value)} value={value}>{children}</select></label>; }
