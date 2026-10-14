"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { createResearchReport, depositResearchReportKnowledge, reviewResearchReport } from "@/lib/api";
import type { ResearchReport } from "@/lib/schemas";

const kindMeta = {
  fact: { label: "已记录事实", tone: "border-emerald-200 bg-emerald-50 text-emerald-800" },
  prediction: { label: "预测结果", tone: "border-blue-200 bg-blue-50 text-blue-800" },
  recommendation: { label: "验证计划", tone: "border-violet-200 bg-violet-50 text-violet-800" },
  limitation: { label: "适用边界", tone: "border-amber-200 bg-amber-50 text-amber-900" },
} as const;

export function ResearchReportCenter({ experimentId, experimentName, initialReports }: { experimentId: string; experimentName: string; initialReports: ResearchReport[] }) {
  const [reports, setReports] = useState(initialReports);
  const [selectedId, setSelectedId] = useState(initialReports[0]?.reportId ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const selected = reports.find((item) => item.reportId === selectedId) ?? reports[0] ?? null;

  async function generate() {
    setBusy(true); setError("");
    try {
      const report = await createResearchReport(experimentId);
      setReports((current) => [report, ...current]); setSelectedId(report.reportId);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "报告生成失败"); }
    finally { setBusy(false); }
  }
  function replaceReport(report: ResearchReport) {
    setReports((current) => current.map((item) => item.reportId === report.reportId ? report : item));
  }

  return <main className="space-y-6">
    <section className="rounded-2xl border border-[#dce4de] bg-[#173e32] p-6 text-white"><div className="flex flex-wrap items-start justify-between gap-5"><div><p className="text-xs text-emerald-100/65">研发证据汇编</p><h1 className="mt-2 text-2xl font-semibold">实验报告</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-50/70">数据、数学模型、仿真与工艺结果按版本冻结；事实、预测、边界与验证计划分别标记。</p></div><button className="rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-[#174333] disabled:opacity-50" disabled={busy} onClick={() => void generate()}>{busy ? "正在汇编证据…" : reports.length ? "生成当前证据的新版本" : "生成第一版报告"}</button></div></section>
    <ClosedLoop report={selected}/>
    {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div> : null}
    <div className="grid gap-5 xl:grid-cols-[16rem_1fr]"><aside className="rounded-2xl border border-[#dce4de] bg-white p-4"><div className="flex items-center justify-between"><h2 className="font-semibold">报告版本</h2><span className="text-xs text-slate-400">{reports.length}</span></div><div className="mt-4 space-y-2">{reports.map((report) => <button className={`w-full rounded-xl border p-3 text-left ${selected?.reportId === report.reportId ? "border-[#7ca08d] bg-[#eef5f0]" : "border-slate-200 hover:bg-slate-50"}`} key={report.reportId} onClick={() => setSelectedId(report.reportId)}><div className="flex justify-between gap-2"><b className="text-sm">版本 {report.reportVersion}</b><span className={`rounded-full px-2 py-0.5 text-[9px] ${report.status === "reviewed" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-800"}`}>{report.status === "reviewed" ? "已审核" : "待审核"}</span></div><p className="mt-2 text-[10px] text-slate-400">{formatTime(report.generatedAt)}</p></button>)}</div>{!reports.length ? <p className="mt-4 text-sm leading-6 text-slate-500">尚无报告。系统只汇编已有证据，不补造缺失结果。</p> : null}</aside>
      <section className="min-w-0">{selected ? <ReportDocument experimentName={experimentName} report={selected} onChange={replaceReport} onError={setError}/> : <div className="rounded-2xl border border-dashed border-[#cbd8d0] bg-white p-12 text-center text-sm text-slate-500">生成报告后，这里将展示分层证据和待确认事项。</div>}</section></div>
  </main>;
}

function ClosedLoop({ report }: { report: ResearchReport | null }) {
  const source = report?.sourceVersions ?? {};
  const steps = [["数据沉淀", source.dataset], ["模型研判", source.model], ["仿真映射", source.simulation], ["工艺优化", source.optimization], ["人工审核", report?.reviewedAt], ["规律沉淀", report?.approvedKnowledgeStatementIds.length ? "已选择" : undefined]];
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div><h2 className="font-semibold">研发验证闭环</h2><p className="mt-1 text-xs text-slate-500">每一环读取上一环的版本证据；只有人工逐条审核后，内容才可沉淀为企业规律。</p></div><div className="mt-5 grid gap-2 md:grid-cols-6">{steps.map(([label, version], index) => <div className="relative" key={label}><div className={`rounded-xl border p-3 ${version && version !== "not_available" ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-slate-50"}`}><span className="text-[10px] text-slate-400">{String(index + 1).padStart(2, "0")}</span><b className="mt-2 block text-sm text-slate-800">{label}</b><p className="mt-1 truncate font-mono text-[9px] text-slate-400">{version && version !== "not_available" ? version : "等待证据"}</p></div>{index < steps.length - 1 ? <span className="absolute -right-2 top-1/2 z-10 hidden -translate-y-1/2 text-slate-300 md:block">→</span> : null}</div>)}</div></section>;
}

function ReportDocument({ experimentName, report, onChange, onError }: { experimentName: string; report: ResearchReport; onChange: (report: ResearchReport) => void; onError: (message: string) => void }) {
  const [operator, setOperator] = useState("");
  const [reason, setReason] = useState("");
  const [approved, setApproved] = useState<string[]>(report.approvedKnowledgeStatementIds);
  const [busy, setBusy] = useState<"review" | "deposit" | null>(null);
  const eligible = useMemo(() => report.sections.flatMap((section) => section.statements).filter((item) => item.kind !== "prediction"), [report]);
  async function review() {
    setBusy("review"); onError("");
    try { onChange(await reviewResearchReport(report.experimentId, report.reportId, { operator, reason, approvedStatementIds: approved })); }
    catch (cause) { onError(cause instanceof Error ? cause.message : "审核提交失败"); }
    finally { setBusy(null); }
  }
  async function deposit() {
    setBusy("deposit"); onError("");
    try { const entries = await depositResearchReportKnowledge(report.experimentId, report.reportId); onError(entries.length ? `已沉淀 ${entries.length} 条企业规律，可前往企业规律中心查看。` : "本报告未批准可沉淀条目。"); }
    catch (cause) { onError(cause instanceof Error ? cause.message : "规律沉淀失败"); }
    finally { setBusy(null); }
  }
  return <article className="rounded-2xl border border-[#dce4de] bg-white p-5 sm:p-7"><header className="border-b border-[#e7ece8] pb-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs text-[#397b5d]">{experimentName} · 版本 {report.reportVersion}</p><h2 className="mt-2 text-2xl font-semibold text-slate-950">{report.title}</h2><p className="mt-2 font-mono text-[10px] text-slate-400">输入指纹 {report.inputFingerprint}</p></div><a className="rounded-lg border border-[#cbd8d0] px-4 py-2 text-xs text-[#174333]" href={`/api/experiments/${encodeURIComponent(report.experimentId)}/research-reports/${encodeURIComponent(report.reportId)}/markdown`}>下载 Markdown</a></div></header>
    <div className="mt-6 space-y-7">{report.sections.map((section) => <section key={section.sectionKey}><h3 className="text-lg font-semibold text-slate-900">{section.title}</h3><div className="mt-3 space-y-3">{section.statements.map((item) => { const meta = kindMeta[item.kind]; const selectable = report.status === "draft" && item.kind !== "prediction"; return <div className="rounded-xl border border-[#e2e8e4] p-4" key={item.statementId}><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full border px-2.5 py-1 text-[10px] font-medium ${meta.tone}`}>{meta.label}</span><b className="text-sm text-slate-900">{item.title}</b>{item.kind === "prediction" ? <span className="ml-auto text-[10px] text-blue-600">仅供研判，不可入库</span> : selectable ? <label className="ml-auto flex items-center gap-2 text-xs text-slate-600"><input checked={approved.includes(item.statementId)} onChange={(event) => setApproved((current) => event.target.checked ? [...current, item.statementId] : current.filter((id) => id !== item.statementId))} type="checkbox"/>批准沉淀</label> : report.approvedKnowledgeStatementIds.includes(item.statementId) ? <span className="ml-auto text-[10px] text-emerald-700">已批准</span> : null}</div><p className="mt-3 text-sm leading-7 text-slate-700">{item.text}</p><div className="mt-3 flex flex-wrap gap-2">{item.evidenceRefs.map((ref) => <code className="rounded bg-slate-50 px-2 py-1 text-[9px] text-slate-500" key={ref}>{ref}</code>)}</div></div>; })}</div></section>)}</div>
    {report.unresolvedItems.length ? <section className="mt-7 rounded-xl border border-amber-200 bg-amber-50 p-5"><h3 className="font-semibold text-amber-950">待补充或人工确认</h3><ul className="mt-3 space-y-2 text-sm text-amber-900">{report.unresolvedItems.map((item) => <li key={item}>· {item}</li>)}</ul></section> : null}
    {report.status === "draft" ? <section className="mt-7 rounded-xl border border-[#cbd8d0] bg-[#f7f9f7] p-5"><h3 className="font-semibold text-slate-900">审核与沉淀范围</h3><p className="mt-1 text-xs leading-5 text-slate-500">审核不等于验证预测。仅将上方明确勾选的事实、边界和验证计划纳入可沉淀范围。</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onChange={(event) => setOperator(event.target.value)} placeholder="审核人" value={operator}/><input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" onChange={(event) => setReason(event.target.value)} placeholder="审核理由" value={reason}/></div><div className="mt-4 flex items-center justify-between gap-3"><span className="text-xs text-slate-500">已选择 {approved.length} / {eligible.length} 条</span><button className="rounded-lg bg-[#174333] px-5 py-2 text-sm text-white disabled:opacity-40" disabled={busy !== null || !operator.trim() || reason.trim().length < 2} onClick={() => void review()}>{busy === "review" ? "正在锁定审核记录…" : "确认审核"}</button></div></section> : <section className="mt-7 rounded-xl border border-emerald-200 bg-emerald-50 p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><h3 className="font-semibold text-emerald-950">审核记录已锁定</h3><p className="mt-1 text-xs text-emerald-800">{report.reviewedBy} · {report.reviewReason} · 批准 {report.approvedKnowledgeStatementIds.length} 条</p></div><div className="flex gap-2"><Link className="rounded-lg border border-emerald-300 px-4 py-2 text-xs text-emerald-900" href="/knowledge-assets">企业规律中心</Link><button className="rounded-lg bg-[#174333] px-4 py-2 text-xs text-white disabled:opacity-40" disabled={busy !== null} onClick={() => void deposit()}>{busy === "deposit" ? "正在沉淀…" : "沉淀到企业规律"}</button></div></div></section>}
    <footer className="mt-7 border-t border-[#e7ece8] pt-5 text-xs leading-6 text-slate-500">{report.disclaimer}</footer>
  </article>;
}

function formatTime(value: string) { return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value)); }
