"use client";

import Link from "next/link";
import { useState } from "react";

import { getLlmStatus } from "@/lib/api";
import type { AgentQueueStatus, AgentRuntimeStatus, LlmStatus } from "@/lib/schemas";

const failureLabels: Record<string, string> = {
  disabled: "模型能力未启用",
  authentication: "身份验证失败",
  endpoint_not_found: "接口地址不匹配",
  upstream: "上游模型服务异常",
  timeout: "连接超时",
  connection: "无法连接模型服务",
  http_error: "模型服务返回异常状态",
};

export function ModelCapabilityCenter({ initialStatus, queue, runtime }: { initialStatus: LlmStatus; queue: AgentQueueStatus; runtime: AgentRuntimeStatus }) {
  const [status, setStatus] = useState(initialStatus);
  const [checking, setChecking] = useState(false);
  async function probe() {
    setChecking(true);
    try { setStatus(await getLlmStatus()); } finally { setChecking(false); }
  }
  const onlineWorkers = queue.workers.filter((item) => item.status === "online").length;
  return <div className="mx-auto max-w-6xl space-y-5">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-medium text-[#2f7054]">系统设置</p><h1 className="mt-1 text-3xl font-semibold tracking-[-0.03em]">计算与模型能力</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">查看模型连接、业务用途和安全回退。密钥只由服务器环境变量管理，不会发送到浏览器。</p></div><Link className="rounded-lg border border-[#cbd8d0] bg-white px-4 py-2 text-sm text-[#174333]" href="/">返回实验归档</Link></div>

    <section className="rounded-2xl border border-[#dce4de] bg-white p-6"><div className="flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-3"><span className={`h-3 w-3 rounded-full ${status.available ? "bg-emerald-500" : "bg-amber-500"}`}/><div><h2 className="font-semibold">{status.available ? "模型服务连接正常" : failureLabels[status.failureCategory ?? ""] ?? "当前使用安全回退"}</h2><p className="mt-1 text-xs text-slate-500">{status.provider} · {status.model}</p></div></div><button className="rounded-lg bg-[#174333] px-4 py-2 text-sm text-white disabled:opacity-40" disabled={checking} onClick={() => void probe()}>{checking ? "检测中…" : "重新检测连接"}</button></div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Metric label="服务地址" value={status.baseUrl}/><Metric label="部署范围" value={status.endpointScope === "local" ? "本机 / 内网" : "远程兼容 API"}/><Metric label="密钥状态" value={status.apiKeyConfigured ? "服务端已配置" : "未配置"}/><Metric label="检测延迟" value={status.latencyMs === null ? "未检测" : `${status.latencyMs} ms`}/></div>
      {!status.available ? <p className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">模型不可用时，数据清洗、数学建模和版本门禁仍按确定性程序运行；需要语言理解的环节会明确标记为规则安全回退。</p> : null}
    </section>

    <section className="rounded-2xl border border-[#dce4de] bg-white p-6"><h2 className="font-semibold">模型应用范围</h2><p className="mt-1 text-xs text-slate-500">启用代表允许调用语言模型，不代表模型可以绕过确定性算法或人工审核。</p><div className="mt-4 grid gap-3 md:grid-cols-2">{status.usageRoutes.map((route) => <article className="rounded-xl border border-slate-200 p-4" key={route.routeKey}><div className="flex justify-between gap-3"><b className="text-sm">{route.label}</b><span className={`rounded-full px-2 py-1 text-[10px] ${route.enabled ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>{route.enabled ? "允许调用模型" : "使用规则回退"}</span></div><p className="mt-2 text-xs leading-5 text-slate-600">{route.role}</p><p className="mt-2 text-[11px] text-slate-400">回退：{route.fallback}</p></article>)}</div></section>

    <div className="grid gap-5 lg:grid-cols-2"><section className="rounded-2xl border border-[#dce4de] bg-white p-6"><h2 className="font-semibold">任务运行底座</h2><div className="mt-4 grid grid-cols-2 gap-3"><Metric label="运行框架" value={runtime.effectiveBackend}/><Metric label="在线 Worker" value={`${onlineWorkers} 个`}/><Metric label="队列后端" value={queue.backend}/><Metric label="失败 / 死信" value={`${queue.counts.failed} / ${queue.counts.deadLetter}`}/></div></section><section className="rounded-2xl border border-[#dce4de] bg-white p-6"><h2 className="font-semibold">不可绕过的安全边界</h2><ul className="mt-4 space-y-2 text-sm leading-6 text-slate-600">{status.securityBoundaries.map((item) => <li key={item}>· {item}</li>)}</ul></section></div>

    <section className="rounded-2xl border border-[#dce4de] bg-[#f7f9f7] p-6"><h2 className="font-semibold">服务器配置方式</h2><p className="mt-2 text-sm leading-6 text-slate-600">在服务器私有环境文件中配置 <code>LOCAL_LLM_PROVIDER</code>、<code>LOCAL_LLM_BASE_URL</code>、<code>LOCAL_LLM_MODEL</code> 和 <code>LOCAL_LLM_API_KEY</code>。页面只显示是否已配置，不显示密钥内容。</p></section>
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="min-w-0 rounded-xl bg-[#f3f6f3] p-4"><div className="text-[11px] text-slate-500">{label}</div><div className="mt-2 truncate text-sm font-medium text-slate-900" title={value}>{value}</div></div>; }
