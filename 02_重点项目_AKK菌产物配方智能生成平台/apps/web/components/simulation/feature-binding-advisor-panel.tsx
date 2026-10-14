"use client";

import { useMemo, useState } from "react";

import {
  confirmSimulationModelBinding,
  enqueueFeatureBindingSuggestion,
  getAgentCommand,
  getFeatureBindingSuggestionRun,
} from "@/lib/api";
import type {
  AgentCommandTask,
  FeatureBindingSuggestionCandidate,
  FeatureBindingSuggestionRun,
  FeatureBindingVersion,
  DeviceAdapterPack,
  PromotedModelRecord,
  ExperimentWorkspaceOverview,
} from "@/lib/schemas";

const parameterOptions = [
  ["temperatureC", "温度"], ["ph", "pH"], ["stirringRpm", "搅拌速度"],
  ["cultureHours", "培养时长"], ["pressureMpa", "压力"],
  ["anaerobicScore", "厌氧水平"], ["carbonConcentration", "碳源浓度"],
] as const;

const taskLabels: Record<AgentCommandTask["status"], string> = {
  queued: "等待计算", leased: "映射分析中", completed: "建议已生成", failed: "本次执行失败",
  deadLetter: "需要人工处理", cancelled: "已取消",
};

export function FeatureBindingAdvisorPanel({
  experimentId,
  promotedModels,
  adapterPacks,
  activeBindingVersions,
  parameterDefinitions,
}: {
  experimentId: string;
  promotedModels: PromotedModelRecord[];
  adapterPacks: DeviceAdapterPack[];
  activeBindingVersions: string[];
  parameterDefinitions: ExperimentWorkspaceOverview["productionContext"]["parameterDefinitions"];
}) {
  const [modelVersion, setModelVersion] = useState(promotedModels[0]?.modelVersion ?? "");
  const [task, setTask] = useState<AgentCommandTask | null>(null);
  const [adapterPackId, setAdapterPackId] = useState("");
  const [run, setRun] = useState<FeatureBindingSuggestionRun | null>(null);
  const [drafts, setDrafts] = useState<FeatureBindingSuggestionCandidate[]>([]);
  const [operator, setOperator] = useState("");
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState<FeatureBindingVersion | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedModel = promotedModels.find((item) => item.modelVersion === modelVersion);
  const selectedAdapter = adapterPacks.find((item) => item.packId === adapterPackId);
  const allMapped = drafts.length > 0 && drafts.every((item) => item.simulationParameter);
  const evidenceCount = useMemo(() => drafts.reduce((sum, item) => sum + item.evidence.length, 0), [drafts]);
  const bindingParameterOptions = useMemo(() => {
    const builtIn = parameterOptions.map(([value, label]) => ({ value, label }));
    const custom = parameterDefinitions.filter((item) => !builtIn.some((option) => option.value === item.key)).map((item) => ({ value: item.key, label: item.label }));
    return [...builtIn, ...custom];
  }, [parameterDefinitions]);

  async function generateSuggestions() {
    if (!modelVersion) return;
    setBusy(true); setError(null); setConfirmed(null); setRun(null); setDrafts([]);
    try {
      let current = await enqueueFeatureBindingSuggestion(
        experimentId, modelVersion,
        selectedAdapter ? {
          enterpriseKey: selectedAdapter.enterpriseKey,
          deviceType: selectedAdapter.deviceType,
          packVersion: selectedAdapter.packVersion,
        } : undefined,
      );
      setTask(current);
      for (let attempt = 0; attempt < 75 && ["queued", "leased"].includes(current.status); attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 800));
        current = await getAgentCommand(current.taskId);
        setTask(current);
      }
      if (current.status !== "completed" || !current.resultRunId) {
        throw new Error(current.errorMessage || "本次分析未生成可确认的绑定建议");
      }
      const suggestion = await getFeatureBindingSuggestionRun(experimentId, current.resultRunId);
      setRun(suggestion);
      setDrafts(suggestion.candidates.map((item) => ({ ...item })));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "绑定建议生成失败");
    } finally {
      setBusy(false);
    }
  }

  function updateCandidate(index: number, patch: Partial<FeatureBindingSuggestionCandidate>) {
    setDrafts((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  async function confirmBindings() {
    if (!run || !allMapped) return;
    setBusy(true); setError(null);
    try {
      const result = await confirmSimulationModelBinding(experimentId, {
        bindingVersion: `binding-${Date.now()}`,
        modelVersion: run.modelVersion,
        featureNames: drafts.map((item) => item.modelFeature),
        entries: drafts.map((item) => ({
          modelFeature: item.modelFeature, standardField: item.standardField,
          simulationParameter: item.simulationParameter as string,
          sourceUnit: item.sourceUnit ?? null, targetUnit: item.targetUnit ?? null,
          scale: item.scale, offset: item.offset,
        })),
        confirmedBy: operator.trim(), confirmationReason: reason.trim(),
        suggestionRunId: run.runId, adapterPack: run.adapterPack,
      });
      setConfirmed(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "正式绑定保存失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-[#dce4de] bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <div className="text-xs font-medium text-[#2f7054]">模型接入仿真前的人工闸门</div>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">设备适配与特征绑定</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">系统只提出映射建议，不会修改正式模型，也不会向真实设备发送控制指令。确认后的版本才可被仿真模型调用。</p>
        </div>
        <div className="rounded-xl bg-[#173e32] px-4 py-3 text-right text-white">
          <div className="text-[10px] text-emerald-100/60">正式状态</div>
          <div className="mt-1 text-sm font-semibold">{confirmed ? `已确认 ${confirmed.bindingVersion}` : activeBindingVersions.length ? `已确认 ${activeBindingVersions.join("、")}` : "等待人工确认"}</div>
        </div>
      </div>

      {promotedModels.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-amber-300 bg-amber-50 p-5 text-sm leading-6 text-amber-900"><p>当前实验还没有通过人工晋升的数学模型。请先在数据分析阶段完成模型评估与晋升，再进行设备参数绑定。</p>{parameterDefinitions.length ? <div className="mt-3 rounded-lg bg-white/70 p-3"><p className="text-xs font-semibold">本实验等待绑定的参数</p><div className="mt-2 flex flex-wrap gap-2">{parameterDefinitions.map((item) => <span className="rounded bg-white px-2 py-1 text-[10px]" key={item.key}>{item.label}{item.unit ? `（${item.unit}）` : ""}</span>)}</div><p className="mt-2 text-[10px]">模型晋升后，建议映射会自动加入这些参数供人工确认。</p></div> : null}</div>
      ) : (
        <>
          <div className="mt-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
            <label className="text-xs font-medium text-slate-600">选择已晋升模型
              <select className="mt-2 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-[#397b5d]" value={modelVersion} onChange={(event) => { setModelVersion(event.target.value); setRun(null); setDrafts([]); setTask(null); setConfirmed(null); }}>
                {promotedModels.map((model) => <option key={model.modelVersion} value={model.modelVersion}>{model.targetField} · {model.modelType} · {model.modelVersion}</option>)}
              </select>
            </label>
            <label className="text-xs font-medium text-slate-600">选择企业设备适配包（可选）
              <select className="mt-2 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-[#397b5d]" value={adapterPackId} onChange={(event) => { setAdapterPackId(event.target.value); setRun(null); setDrafts([]); setTask(null); setConfirmed(null); }}>
                <option value="">不使用适配包，仅运行通用规则</option>
                {adapterPacks.map((pack) => <option key={pack.packId} value={pack.packId}>{pack.enterpriseKey} · {pack.deviceType} · V{pack.packVersion}</option>)}
              </select>
            </label>
            <button className="self-end rounded-lg bg-[#174333] px-5 py-3 text-sm font-medium text-white disabled:opacity-40" type="button" disabled={busy || !modelVersion} onClick={() => void generateSuggestions()}>{busy ? "正在分析映射…" : run ? "重新生成建议" : "生成绑定建议"}</button>
          </div>
          {selectedModel ? <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-slate-500"><span>目标：{selectedModel.targetField}</span><span>特征：{selectedModel.featureNames.length} 项</span><span>数据快照：{selectedModel.datasetSnapshotId}</span><span>批准人：{selectedModel.approvedBy}</span></div> : null}
          {selectedAdapter ? <div className="mt-3 rounded-lg border border-[#dce4de] bg-[#f4f7f4] px-3 py-2 text-[11px] text-slate-600">将使用适配包 <b>{selectedAdapter.packId}</b> · {selectedAdapter.entries.length} 条映射 · 哈希 {selectedAdapter.contentHash.slice(0, 20)}…</div> : null}
        </>
      )}

      {task ? <div className="mt-5 grid gap-3 rounded-xl border border-[#dce4de] bg-[#f4f7f4] p-4 sm:grid-cols-4"><Metric label="任务状态" value={taskLabels[task.status]} /><Metric label="执行次数" value={`${task.attempts}/${task.maxAttempts}`} /><Metric label="运行节点" value={task.leaseOwner || "等待 Worker"} /><Metric label="所需能力" value={task.requiredCapabilities.join(" + ")} /></div> : null}
      {error ? <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div> : null}

      {run ? (
        <div className="mt-6">
          <div className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 pb-3">
            <div><h3 className="font-semibold text-slate-900">建议证据链</h3><p className="mt-1 text-xs text-slate-500">{run.mode === "llm_assisted" ? "规则与语义模型联合判断" : run.mode === "rule_fallback" ? "语义服务不可用，已安全回退到确定性规则" : "确定性规则判断"}</p></div>
            <div className="flex gap-4 text-right"><Metric label="待复核" value={String(run.reviewCount)} /><Metric label="冲突" value={String(run.conflictCount)} /><Metric label="证据" value={String(evidenceCount)} /></div>
          </div>
          {run.adapterPack ? <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] leading-5 text-emerald-900">建议来源已锁定：{run.adapterPack.enterpriseKey} / {run.adapterPack.deviceType} / V{run.adapterPack.packVersion}<br/><span className="font-mono">{run.adapterPack.contentHash}</span></div> : null}
          <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[860px] text-left text-xs"><thead className="text-slate-400"><tr><th className="py-2 pr-3 font-medium">模型特征</th><th className="px-3 font-medium">标准字段</th><th className="px-3 font-medium">仿真参数</th><th className="px-3 font-medium">换算</th><th className="px-3 font-medium">置信度</th><th className="pl-3 font-medium">判断依据</th></tr></thead><tbody>{drafts.map((item, index) => <tr className="border-t border-slate-100 align-top" key={item.modelFeature}><td className="py-3 pr-3 font-mono font-semibold text-slate-800">{item.modelFeature}</td><td className="px-3 py-3"><input className="h-9 w-36 rounded border border-slate-200 px-2" value={item.standardField} onChange={(event) => updateCandidate(index, { standardField: event.target.value })}/></td><td className="px-3 py-3"><select className={`h-9 w-36 rounded border px-2 ${item.simulationParameter ? "border-slate-200" : "border-amber-300 bg-amber-50"}`} value={item.simulationParameter ?? ""} onChange={(event) => updateCandidate(index, { simulationParameter: event.target.value || null })}><option value="">请选择</option>{bindingParameterOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></td><td className="px-3 py-3"><div className="flex items-center gap-1"><input aria-label={`${item.modelFeature} 比例`} className="h-9 w-16 rounded border border-slate-200 px-2 font-mono" type="number" step="any" value={item.scale} onChange={(event) => updateCandidate(index, { scale: event.target.valueAsNumber })}/><span className="text-slate-400">× +</span><input aria-label={`${item.modelFeature} 偏移`} className="h-9 w-16 rounded border border-slate-200 px-2 font-mono" type="number" step="any" value={item.offset} onChange={(event) => updateCandidate(index, { offset: event.target.valueAsNumber })}/></div></td><td className="px-3 py-3"><span className={item.requiresHumanReview ? "text-amber-700" : "text-emerald-700"}>{(item.confidence * 100).toFixed(0)}%</span><div className="mt-1 text-[10px] text-slate-400">{item.source}</div></td><td className="py-3 pl-3 text-[11px] leading-5 text-slate-500">{item.evidence.join("；")} {item.reviewReasons.length ? <div className="text-amber-700">需确认：{item.reviewReasons.join("、")}</div> : null}</td></tr>)}</tbody></table></div>

          <div className="mt-5 grid gap-3 rounded-xl bg-[#f4f7f4] p-4 md:grid-cols-[180px_minmax(0,1fr)_auto]">
            <input className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm" value={operator} onChange={(event) => setOperator(event.target.value)} placeholder="确认人" />
            <input className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="确认依据，例如：已核对设备说明书与单位换算" />
            <button className="rounded-lg bg-slate-900 px-5 text-sm font-medium text-white disabled:opacity-35" type="button" disabled={busy || !allMapped || !operator.trim() || reason.trim().length < 2 || Boolean(confirmed)} onClick={() => void confirmBindings()}>{confirmed ? "正式绑定已保存" : "人工确认并生成正式版本"}</button>
          </div>
          {!allMapped ? <p className="mt-2 text-xs text-amber-700">仍有特征未选择仿真参数，不能生成正式绑定。</p> : null}
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><div className="text-[10px] text-slate-400">{label}</div><div className="mt-1 max-w-40 truncate text-xs font-semibold text-slate-800" title={value}>{value}</div></div>;
}
