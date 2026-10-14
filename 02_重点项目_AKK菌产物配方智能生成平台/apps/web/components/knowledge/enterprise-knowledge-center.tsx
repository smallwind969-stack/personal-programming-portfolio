"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { registerEnterpriseKnowledgeUsage } from "@/lib/api";
import type { EnterpriseKnowledgeEntry, EnterpriseKnowledgeUsage } from "@/lib/schemas";

const labels = { verifiedFact: "核验事实", applicabilityBoundary: "适用边界", validationPlan: "验证计划" } as const;
const tones = { verifiedFact: "bg-emerald-50 text-emerald-800", applicabilityBoundary: "bg-amber-50 text-amber-900", validationPlan: "bg-violet-50 text-violet-800" } as const;

export function EnterpriseKnowledgeCenter({ entries }: { entries: EnterpriseKnowledgeEntry[] }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [selected, setSelected] = useState<string[]>([]);
  const [targetExperiment, setTargetExperiment] = useState("");
  const [targetVersion, setTargetVersion] = useState("");
  const [operator, setOperator] = useState("");
  const [note, setNote] = useState("");
  const [purpose, setPurpose] = useState<EnterpriseKnowledgeUsage["purpose"]>("modeling");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const visible = useMemo(() => entries.filter((item) => (category === "all" || item.category === category) && `${item.title} ${item.content} ${item.experimentName}`.toLowerCase().includes(query.toLowerCase())), [entries, query, category]);
  const experimentCount = new Set(entries.map((item) => item.experimentId)).size;
  async function registerUsage() {
    if (!targetExperiment.trim() || !targetVersion.trim() || !operator.trim() || note.trim().length < 2 || !selected.length) return;
    setBusy(true); setMessage("");
    try {
      const usage = await registerEnterpriseKnowledgeUsage(targetExperiment.trim(), { knowledgeIds: selected, purpose, targetVersion: targetVersion.trim(), operator: operator.trim(), note: note.trim() });
      setMessage(`已登记 ${usage.knowledgeIds.length} 条规律引用，目标实验：${usage.experimentId}`);
      setSelected([]);
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "引用登记失败"); }
    finally { setBusy(false); }
  }
  return <main className="min-h-screen bg-[#eef2ee] p-4 text-slate-900 sm:p-7"><div className="mx-auto max-w-7xl space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-medium text-[#397b5d]">可追溯研发资产</p><h1 className="mt-1 text-3xl font-semibold tracking-[-0.035em]">企业规律</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">只展示经人工审核并明确批准的内容；预测结果不会直接进入正式规律。</p></div><Link className="rounded-lg bg-[#174333] px-4 py-2 text-sm text-white" href="/">返回实验归档</Link></header>
    <section className="grid gap-3 md:grid-cols-5">{[["审核报告", "锁定责任与理由"], ["条目筛选", "逐条决定沉淀范围"], ["证据锁定", "保留版本与来源"], ["规律入库", `${entries.length} 条正式条目`], ["后续引用", "供检索与建模研判"]].map(([title, detail], index) => <div className="relative rounded-xl border border-[#dce4de] bg-white p-4" key={title}><span className="text-[10px] text-[#397b5d]">{String(index + 1).padStart(2, "0")}</span><b className="mt-2 block text-sm">{title}</b><p className="mt-1 text-xs text-slate-500">{detail}</p>{index < 4 ? <span className="absolute -right-2 top-1/2 z-10 hidden text-slate-300 md:block">→</span> : null}</div>)}</section>
    <section className="grid gap-3 sm:grid-cols-3"><Metric label="正式条目" value={entries.length}/><Metric label="来源实验" value={experimentCount}/><Metric label="预测直接入库" value="0"/></section>
    <section className="rounded-2xl border border-[#cbd8d0] bg-[#f7f9f7] p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="font-semibold">登记到下一轮研发</h2><p className="mt-1 text-xs leading-5 text-slate-500">选择已核验条目，记录它将被哪一个实验、哪一版数据或方案使用。</p></div><span className="text-xs text-slate-500">已选择 {selected.length} 条</span></div><div className="mt-4 grid gap-3 md:grid-cols-4"><input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onChange={(event) => setTargetExperiment(event.target.value)} placeholder="目标实验编号" value={targetExperiment}/><input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onChange={(event) => setTargetVersion(event.target.value)} placeholder="目标版本（如 dataset-v4）" value={targetVersion}/><input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onChange={(event) => setOperator(event.target.value)} placeholder="登记人" value={operator}/><select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onChange={(event) => setPurpose(event.target.value as EnterpriseKnowledgeUsage["purpose"])} value={purpose}><option value="modeling">数学建模</option><option value="simulation">仿真模拟</option><option value="optimization">工艺优化</option><option value="reporting">报告引用</option></select></div><div className="mt-3 flex gap-3"><input className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onChange={(event) => setNote(event.target.value)} placeholder="引用说明" value={note}/><button className="rounded-lg bg-[#174333] px-5 py-2 text-sm text-white disabled:opacity-40" disabled={busy || !selected.length || !targetExperiment.trim() || !targetVersion.trim() || !operator.trim() || note.trim().length < 2} onClick={() => void registerUsage()}>{busy ? "正在登记…" : "登记引用"}</button></div>{message ? <p className="mt-3 text-xs text-[#246247]">{message}</p> : null}</section>
    <section className="grid gap-4 lg:grid-cols-2">{visible.map((item) => <article className="rounded-2xl border border-[#dce4de] bg-white p-5" key={item.knowledgeId}><div className="flex flex-wrap items-center justify-between gap-2"><label className="flex items-center gap-2"><input checked={selected.includes(item.knowledgeId)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, item.knowledgeId] : current.filter((id) => id !== item.knowledgeId))} type="checkbox"/><span className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${tones[item.category]}`}>{labels[item.category]}</span></label><span className="text-[10px] text-slate-400">报告 v{item.sourceReportVersion}</span></div><h2 className="mt-4 text-lg font-semibold">{item.title}</h2><p className="mt-1 text-xs font-medium text-[#397b5d]">{item.experimentName}</p><p className="mt-3 text-sm leading-7 text-slate-600">{item.content}</p><div className="mt-4 flex flex-wrap gap-2">{item.evidenceRefs.map((ref) => <code className="rounded bg-slate-50 px-2 py-1 text-[9px] text-slate-500" key={ref}>{ref}</code>)}</div><div className="mt-5 border-t border-slate-100 pt-4 text-[10px] leading-5 text-slate-400"><p>审核：{item.reviewedBy} · {item.reviewReason}</p><p className="truncate font-mono" title={item.contentHash}>内容指纹：{item.contentHash}</p><Link className="mt-2 inline-block text-[#246247]" href={`/experiments/${encodeURIComponent(item.experimentId)}/reports`}>查看来源报告 →</Link></div></article>)}{!visible.length ? <div className="col-span-full rounded-2xl border border-dashed border-[#cbd8d0] bg-white p-12 text-center"><h2 className="font-semibold">暂无符合条件的企业规律</h2><p className="mt-2 text-sm text-slate-500">在实验报告中完成逐条审核后，可将批准内容沉淀到这里。</p></div> : null}</section>
  </div></main>;
}

function Metric({ label, value }: { label: string; value: string | number }) { return <div className="rounded-xl border border-[#dce4de] bg-white p-4"><p className="text-xs text-slate-500">{label}</p><strong className="mt-2 block text-2xl text-[#174333]">{value}</strong></div>; }
