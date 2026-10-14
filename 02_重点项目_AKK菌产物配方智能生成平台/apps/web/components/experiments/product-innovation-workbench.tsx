"use client";

import { useState } from "react";
import { confirmProductRequirement, createProductInnovationRun } from "@/lib/api";
import type { ProductInnovationRun, ProductRequirementVersion } from "@/lib/schemas";

export function ProductInnovationWorkbench({ experimentId, initialRun = null, initialConfirmed = null, initialBrief = "", initialIndustry = "" }: { experimentId: string; initialRun?: ProductInnovationRun | null; initialConfirmed?: ProductRequirementVersion | null; initialBrief?: string; initialIndustry?: string }) {
  const [brief, setBrief] = useState(initialBrief);
  const [industry, setIndustry] = useState(initialIndustry);
  const [market, setMarket] = useState("");
  const [users, setUsers] = useState("");
  const [constraints, setConstraints] = useState("仅作为研发实验建议\n不得直接下发设备控制指令");
  const [run, setRun] = useState<ProductInnovationRun | null>(initialRun);
  const [confirmed, setConfirmed] = useState<ProductRequirementVersion | null>(initialConfirmed);
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (brief.trim().length < 5) return;
    setBusy(true); setError(null);
    try {
      setConfirmed(null);
      setRun(await createProductInnovationRun(experimentId, `innovation-ui-${Date.now()}`, {
        brief: brief.trim(), industry: industry.trim() || null, targetMarket: market.trim() || null,
        targetUsers: users.split(/[，,]/).map((value) => value.trim()).filter(Boolean), locale: "zh-CN",
        constraints: constraints.split(/\r?\n/).map((value) => value.trim()).filter(Boolean),
      }));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "产品需求研判失败"); }
    finally { setBusy(false); }
  }

  async function confirm() {
    if (!run) return;
    setBusy(true); setError(null);
    try { setConfirmed(await confirmProductRequirement(experimentId, run.runId, `confirm-ui-${Date.now()}`, operator.trim(), reason.trim())); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "确认失败"); }
    finally { setBusy(false); }
  }

  return <div className="space-y-4">
    <section className="rounded-2xl border border-[#dce4de] bg-[#173e32] p-6 text-white"><div className="text-xs text-emerald-100/70">产品需求研判</div><h1 className="mt-2 text-2xl font-semibold">把产品构想转换成可验证研发需求</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-50/70">自动梳理目标、约束、原材料功能角色和验证计划，不生成最终配方比例或生产参数。</p></section>
    <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="mb-4 rounded-xl bg-[#f2f6f3] p-4 text-xs leading-5 text-slate-600"><b className="text-slate-800">需求描述引导</b><p className="mt-1">写清楚产品形态、目标用户、希望提高或降低的指标、成本边界和不能接受的风险。系统只会形成待验证需求，不会直接生成生产指令。</p></div><div className="grid gap-4 md:grid-cols-3"><Field label="所属行业" value={industry} onChange={setIndustry} placeholder="功能食品、生物制造等"/><Field label="目标市场" value={market} onChange={setMarket} placeholder="例如：中国华东地区"/><Field label="目标用户" value={users} onChange={setUsers} placeholder="多个标签用逗号分隔"/></div><Area label="产品构想" value={brief} onChange={setBrief} placeholder="描述希望解决的问题、产品形态、目标体验和已有约束"/><Area label="补充约束（每行一条）" value={constraints} onChange={setConstraints} placeholder={"成本需要可控\n需要冷链稳定"}/><button className="mt-4 rounded-lg bg-[#174333] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40" disabled={brief.trim().length < 5 || busy} onClick={submit} type="button">{busy ? "正在分析需求…" : confirmed ? "基于新描述生成下一版需求" : "开始需求研判"}</button>{error ? <div className="mt-3 text-sm text-rose-700">{error}</div> : null}</section>
    {run ? <><InnovationResult run={run} confirmed={Boolean(confirmed)}/><section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="font-semibold">人工确认产品需求</h2><p className="mt-1 text-xs leading-5 text-slate-500">确认后生成只读需求版本，工艺优化只引用已确认版本。</p></div>{confirmed ? <span className="rounded bg-emerald-50 px-3 py-1 text-xs text-emerald-800">已固化 V{confirmed.version}</span> : null}</div>{confirmed ? <div className="mt-4 rounded-xl bg-[#f2f6f3] p-4 text-sm"><b>{confirmed.snapshot.workingName}</b><p className="mt-1 text-xs text-slate-600">{confirmed.requirementVersionId} · 来源 {confirmed.sourceRunId}</p><p className="mt-1 break-all text-[11px] text-slate-500">{confirmed.contentHash}</p><a className="mt-3 inline-flex rounded-lg bg-[#174333] px-4 py-2 text-xs text-white" href={`/experiments/${experimentId}/optimization`}>进入工艺优化并重新开始演示</a></div> : <div className="mt-4 grid gap-3 md:grid-cols-[220px_1fr_auto]"><input className="h-10 rounded-lg border px-3 text-sm" value={operator} onChange={(event) => setOperator(event.target.value)} placeholder="确认人"/><input className="h-10 rounded-lg border px-3 text-sm" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="确认依据（至少 2 个字）"/><button type="button" className="rounded-lg bg-[#174333] px-5 text-sm text-white disabled:opacity-40" disabled={busy || !operator.trim() || reason.trim().length < 2} onClick={confirm}>确认并固化版本</button></div>}<p className="mt-3 text-[11px] text-slate-500">固化内容仅为研发实验建议，不会生成最终配方或下发设备控制指令。</p></section></> : null}
  </div>;
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="text-xs font-medium text-slate-600">{label}<input className="mt-2 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm" onChange={(event) => onChange(event.target.value)} placeholder={placeholder} value={value}/></label>; }
function Area({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="mt-4 block text-xs font-medium text-slate-600">{label}<textarea className="mt-2 min-h-24 w-full rounded-xl border border-slate-200 p-3 text-sm leading-6" maxLength={5000} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} value={value}/></label>; }
function InnovationResult({ run, confirmed }: { run: ProductInnovationRun; confirmed: boolean }) { return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="flex justify-between gap-3"><div><div className="text-xs text-[#2f7054]">{run.mode === "llm_assisted" ? "本地模型辅助" : "规则安全回退"}</div><h2 className="mt-1 text-xl font-semibold">{run.workingName}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{run.problemStatement}</p></div><span className={`h-fit rounded px-2 py-1 text-xs ${confirmed ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>{confirmed ? "已人工确认" : "待人工确认"}</span></div><div className="mt-5 grid gap-4 lg:grid-cols-2"><Cards title="价值主张" items={run.valuePropositions}/><Cards title="目标用户与场景" items={[...run.targetUserTags, ...run.usageScenarios]}/><Cards title="原材料功能角色（无比例）" items={run.materialRoles.map((item) => `${item.role}：${item.purpose}`)}/><Cards title="目标性能指标" items={run.targetMetrics.map((item) => `${item.metricName} · ${item.direction} · ${item.targetDescription}`)}/><Cards title="成本与工艺假设" items={[...run.costAssumptions, ...run.processConstraints]}/><Cards title="风险与未决问题" items={[...run.risks, ...run.unresolvedQuestions]}/><Cards title="法规与研发边界" items={run.regulatoryConstraints}/><Cards title="概念验证计划" items={run.validationPlan.map((item) => `${item.title}：${item.validationItems.join("、")}`)}/></div></section>; }
function Cards({ title, items }: { title: string; items: string[] }) { return <div className="rounded-xl border border-slate-200 p-4"><h3 className="text-xs font-semibold text-slate-700">{title}</h3><ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>· {item}</li>)}</ul></div>; }
