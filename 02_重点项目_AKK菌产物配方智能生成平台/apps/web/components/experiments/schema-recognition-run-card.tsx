"use client";

import { useEffect, useState } from "react";
import { createSchemaRecognitionRun } from "@/lib/api";
import type { SchemaRecognitionRun } from "@/lib/schemas";

const modeLabel = { llm_assisted: "本地模型辅助", rule_fallback: "规则安全回退", rule_only: "确定性规则" } as const;

export function SchemaRecognitionRunCard({ experimentId, agentRunId = "workspace" }: { experimentId: string; agentRunId?: string }) {
  const [run, setRun] = useState<SchemaRecognitionRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const commandId = `schema-node-${agentRunId}`;
    createSchemaRecognitionRun(experimentId, commandId).then(setRun).catch((cause) => setError(cause instanceof Error ? cause.message : "字段识别运行失败"));
  }, [agentRunId, experimentId]);
  if (error) return <section className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">{error}</section>;
  if (!run) return <section className="rounded-2xl border border-[#dce4de] bg-white p-5 text-sm text-slate-500">正在识别字段并验证结构化结果……</section>;
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs font-medium text-[#2f7054]">字段识别结果</div><h2 className="mt-1 text-lg font-semibold text-slate-950">{modeLabel[run.mode]}</h2><p className="mt-1 text-xs text-slate-500">{run.provider} · {run.model}</p></div><div className="grid grid-cols-3 gap-4 text-right text-xs"><Metric label="候选" value={run.candidateCount}/><Metric label="待确认" value={run.reviewCount}/><Metric label="冲突" value={run.conflictCount}/></div></div>
    {run.fallbackReason ? <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">本地模型未参与本次结果，已安全回退：{run.fallbackReason}</div> : null}
    <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead className="border-b border-slate-200 text-slate-500"><tr><th className="py-2">原字段</th><th>标准字段</th><th>类型 / 单位</th><th>来源</th><th>置信度</th><th>确认状态</th></tr></thead><tbody>{run.candidates.map((item) => <tr className="border-b border-slate-100" key={`${item.assetId}-${item.originalColumn}`}><td className="py-3 font-medium text-slate-800">{item.originalColumn}</td><td>{item.standardField}</td><td>{item.dataType} · {item.targetUnit ?? "无单位"}</td><td>{item.source}</td><td>{(item.confidence * 100).toFixed(1)}%</td><td className={item.requiresHumanReview ? "text-amber-700" : "text-emerald-700"}>{item.requiresHumanReview ? `待确认：${item.reviewReasons.join("、")}` : "策略校验通过"}</td></tr>)}</tbody></table></div>
    <div className="mt-4 rounded-lg bg-[#f2f6f3] px-3 py-2 text-xs leading-5 text-slate-600">这些结果只是字段映射候选，不会自动写入正式映射。请在字段映射确认环节人工复核后再用于清洗、对齐和建模。</div>
  </section>;
}

function Metric({ label, value }: { label: string; value: number }) { return <div><div className="text-slate-400">{label}</div><div className="mt-1 font-mono text-base font-semibold text-slate-900">{value}</div></div>; }
