"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { ModelAssetSummary } from "@/lib/schemas";

export function ModelAssetCenter({ assets }: { assets: ModelAssetSummary[] }) {
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("all");
  const visible = useMemo(() => assets.filter((asset) => {
    const keyword = query.trim().toLocaleLowerCase("zh-CN");
    return (scope === "all" || (scope === "latest" ? asset.latest : !asset.latest))
      && (!keyword || `${asset.experimentName} ${asset.modelVersion} ${asset.targetField} ${asset.modelType}`.toLocaleLowerCase("zh-CN").includes(keyword));
  }), [assets, query, scope]);
  const verified = assets.filter((asset) => asset.artifactVerified).length;
  const ready = assets.filter((asset) => asset.evaluationStatus === "confirmed" && asset.bindingVersion).length;

  return <main className="mx-auto max-w-7xl space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-medium text-[#397b5d]">可追溯研发资产</p><h1 className="mt-1 text-3xl font-semibold tracking-[-0.035em] text-slate-950">模型资产</h1><p className="mt-2 text-sm text-slate-500">查看训练数据、算法指标、适用边界、人工准入和仿真依赖。</p></div><div className="flex gap-2"><Link className="rounded-lg border border-[#cbd8d0] bg-white px-4 py-2 text-sm text-[#174333]" href="/model-assets/adapters">设备适配包</Link><Link className="rounded-lg bg-[#174333] px-4 py-2 text-sm text-white" href="/">实验归档</Link></div></header>
    <section className="grid gap-3 sm:grid-cols-3"><Metric label="已晋升模型版本" value={assets.length} detail={`${assets.filter((item) => item.latest).length} 个当前版本`} /><Metric label="制品校验通过" value={verified} detail="基于内容指纹现场校验" /><Metric label="具备仿真依赖" value={ready} detail="评估已确认且特征绑定完整" /></section>
    <section className="flex flex-wrap gap-3 rounded-2xl border border-[#dce4de] bg-white p-4"><input className="h-11 min-w-[260px] flex-1 rounded-lg border border-[#dce4de] px-3 text-sm outline-none focus:border-[#397b5d]" onChange={(event) => setQuery(event.target.value)} placeholder="搜索实验、模型版本、目标字段……" value={query}/><select className="h-11 rounded-lg border border-[#dce4de] bg-white px-3 text-sm text-slate-700" onChange={(event) => setScope(event.target.value)} value={scope}><option value="all">全部版本</option><option value="latest">仅当前版本</option><option value="history">历史版本</option></select></section>
    <section className="overflow-hidden rounded-2xl border border-[#dce4de] bg-white"><div className="overflow-x-auto"><table className="w-full min-w-[950px] text-left text-sm"><thead className="bg-[#f6f8f6] text-xs text-slate-500"><tr><th className="px-5 py-3">实验 / 模型</th><th className="px-4 py-3">预测目标</th><th className="px-4 py-3">关键指标</th><th className="px-4 py-3">证据状态</th><th className="px-4 py-3">仿真使用</th><th className="px-5 py-3 text-right">详情</th></tr></thead><tbody className="divide-y divide-[#e8ede9]">{visible.length ? visible.map((asset) => <tr className="hover:bg-[#f9faf9]" key={`${asset.experimentId}:${asset.modelVersion}`}><td className="px-5 py-4"><div className="flex items-center gap-2"><span className="font-semibold text-slate-900">{asset.experimentName}</span>{asset.latest ? <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-700">当前版本</span> : null}</div><p className="mt-1 font-mono text-xs text-slate-400">{asset.modelVersion} · {asset.modelType}</p></td><td className="px-4 py-4"><p className="font-medium text-slate-800">{asset.targetField}</p><p className="mt-1 text-xs text-slate-400">{asset.featureCount} 个特征</p></td><td className="px-4 py-4"><MetricPairs metrics={asset.metrics}/></td><td className="px-4 py-4"><div className="space-y-1 text-xs"><Evidence ok={asset.artifactVerified} text="制品指纹"/><Evidence ok={asset.evaluationStatus === "confirmed"} text="可靠性评估"/><Evidence ok={Boolean(asset.bindingVersion)} text="特征绑定"/></div></td><td className="px-4 py-4"><span className="font-mono text-lg font-semibold text-[#246247]">{asset.simulationUsageCount}</span><p className="text-[10px] text-slate-400">次运行引用</p></td><td className="px-5 py-4 text-right"><Link className="font-medium text-[#174333] hover:underline" href={`/model-assets/${encodeURIComponent(asset.experimentId)}/${encodeURIComponent(asset.modelVersion)}`}>查看证据链 →</Link></td></tr>) : <tr><td className="px-5 py-12 text-center text-slate-500" colSpan={6}>{assets.length ? "没有符合筛选条件的模型。" : "当前尚无经人工晋升的模型资产。请先在数据分析工作台完成训练、评估和晋升。"}</td></tr>}</tbody></table></div></section>
    <p className="text-center text-[11px] text-slate-400">模型资产页面只展示已持久化证据，不自动晋升模型，也不直接控制真实设备。</p>
  </main>;
}

function Metric({ detail, label, value }: { detail: string; label: string; value: number }) { return <article className="rounded-2xl border border-[#dce4de] bg-white p-5"><p className="text-xs text-slate-500">{label}</p><p className="mt-3 font-mono text-3xl font-semibold text-slate-950">{value}</p><p className="mt-2 text-xs text-slate-500">{detail}</p></article>; }
function Evidence({ ok, text }: { ok: boolean; text: string }) { return <p className={ok ? "text-emerald-700" : "text-amber-700"}>{ok ? "●" : "○"} {text}</p>; }
function MetricPairs({ metrics }: { metrics: Record<string, number> }) { const entries = Object.entries(metrics).slice(0, 2); return <div className="space-y-1">{entries.map(([key, value]) => <p className="font-mono text-xs text-slate-600" key={key}>{key}: {Number(value).toFixed(3)}</p>)}</div>; }
