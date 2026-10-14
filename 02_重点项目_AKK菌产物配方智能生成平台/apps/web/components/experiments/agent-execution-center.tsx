"use client";

import { useEffect, useMemo, useState } from "react";

import {
  applyExperimentAgentGuidance,
  enqueueExperimentAgentCommand,
  getAgentCommand,
  getAgentQueueStatus,
  getAgentCatalog,
  getLatestExperimentAgentRun,
  cancelAgentCommand,
  replayAgentCommand,
  previewExperimentAgentGuidance,
  restartExperimentAgentRun,
  reviewExperimentAgentRun,
  stopExperimentAgentRun,
  getAgentRuntimeStatus,
} from "@/lib/api";
import type { AgentCatalogSnapshot, AgentCommandTask, AgentGuidancePreview, AgentQueueStatus, AgentRunNode, AgentRuntimeStatus, ExperimentAgentRun } from "@/lib/schemas";
import { SchemaRecognitionRunCard } from "@/components/experiments/schema-recognition-run-card";
import { ResultInterpretationRunCard } from "@/components/experiments/result-interpretation-run-card";

const statusText = {
  waiting: "等待上游",
  running: "运行中",
  interrupted: "人工暂停",
  completed: "已完成",
  needsReview: "待人工确认",
  failed: "执行异常",
  stopped: "已终止",
} as const;

const statusStyle = {
  waiting: "bg-slate-100 text-slate-600 ring-slate-200",
  running: "bg-blue-50 text-blue-700 ring-blue-200",
  interrupted: "bg-violet-50 text-violet-700 ring-violet-200",
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  needsReview: "bg-amber-50 text-amber-800 ring-amber-200",
  failed: "bg-rose-50 text-rose-700 ring-rose-200",
  stopped: "bg-stone-100 text-stone-700 ring-stone-200",
} as const;

export function AgentExecutionCenter({ experimentId, initialRun }: { experimentId: string; initialRun: ExperimentAgentRun }) {
  const [run, setRun] = useState(initialRun);
  const [selectedNodeId, setSelectedNodeId] = useState(initialRun.currentNodeId ?? initialRun.nodes[0].nodeId);
  const [prompt, setPrompt] = useState("");
  const [guidance, setGuidance] = useState<AgentGuidancePreview | null>(null);
  const [reviewReason, setReviewReason] = useState("");
  const [reviewOperator, setReviewOperator] = useState("研发负责人");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<AgentRuntimeStatus | null>(null);
  const [queueStatus, setQueueStatus] = useState<AgentQueueStatus | null>(null);
  const [queuedTask, setQueuedTask] = useState<AgentCommandTask | null>(null);
  const [agentCatalog, setAgentCatalog] = useState<AgentCatalogSnapshot | null>(null);

  useEffect(() => {
    getAgentRuntimeStatus().then(setRuntimeStatus).catch(() => setRuntimeStatus(null));
    getAgentQueueStatus().then(setQueueStatus).catch(() => setQueueStatus(null));
    getAgentCatalog().then(setAgentCatalog).catch(() => setAgentCatalog(null));
  }, []);

  useEffect(() => {
    if (!queuedTask || ["completed", "deadLetter", "failed", "cancelled"].includes(queuedTask.status)) return;
    let active = true;
    const timer = window.setInterval(async () => {
      try {
        const next = await getAgentCommand(queuedTask.taskId);
        if (!active) return;
        setQueuedTask(next);
        if (next.status === "completed") {
          const latest = await getLatestExperimentAgentRun(experimentId);
          if (active) { setRun(latest); setSelectedNodeId(latest.currentNodeId ?? selectedNodeId); setBusyAction(null); }
        } else if (next.status === "deadLetter" || next.status === "failed" || next.status === "cancelled") {
          setError(`后台任务未完成：${next.errorCategory ?? "unknown"} · ${next.errorMessage ?? "请查看队列日志"}`);
          setBusyAction(null);
        }
      } catch (cause) {
        if (active) { setError(cause instanceof Error ? cause.message : "无法读取后台任务状态"); setBusyAction(null); }
      }
    }, 1000);
    return () => { active = false; window.clearInterval(timer); };
  }, [queuedTask?.taskId, queuedTask?.status, experimentId, selectedNodeId]);

  const selectedNode = useMemo(
    () => run.nodes.find((node) => node.nodeId === selectedNodeId) ?? run.nodes[0],
    [run.nodes, selectedNodeId],
  );

  async function perform(action: string, operation: () => Promise<ExperimentAgentRun>) {
    setBusyAction(action);
    setError(null);
    try {
      const next = await operation();
      setRun(next);
      if (next.currentNodeId) setSelectedNodeId(next.currentNodeId);
      return next;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "操作失败，请检查 API 服务。");
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function previewGuidance() {
    if (prompt.trim().length < 2) return;
    setBusyAction("preview");
    setError(null);
    try {
      setGuidance(await previewExperimentAgentGuidance(experimentId, run.runId, prompt.trim()));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法生成引导影响预览。");
    } finally {
      setBusyAction(null);
    }
  }

  async function applyGuidance() {
    if (!guidance) return;
    const next = await perform("apply", () => applyExperimentAgentGuidance(experimentId, run.runId, guidance.guidanceId));
    if (next) {
      setGuidance(null);
      setPrompt("");
    }
  }

  async function restartWithGuidance() {
    if (!guidance) return;
    setBusyAction("guidedRestart");
    setError(null);
    try {
      const stopped = run.status === "stopped" ? run : await stopExperimentAgentRun(experimentId, run.runId);
      const next = await restartExperimentAgentRun(experimentId, stopped.runId, guidance.guidanceId);
      setRun(next);
      setSelectedNodeId(next.currentNodeId ?? next.nodes[0].nodeId);
      setGuidance(null);
      setPrompt("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法带引导创建新版本。");
    } finally {
      setBusyAction(null);
    }
  }

  async function submitReview(decision: "approved" | "rejected") {
    if (reviewReason.trim().length < 2 || reviewOperator.trim().length < 1) return;
    await perform("review", () => reviewExperimentAgentRun(experimentId, run.runId, {
      decision,
      reason: reviewReason.trim(),
      operator: reviewOperator.trim(),
      impactScope: ["model-version", "simulation-admission"],
    }));
  }

  async function enqueueAdvance() {
    setBusyAction("advance"); setError(null);
    try { setQueuedTask(await enqueueExperimentAgentCommand(experimentId, run.runId, "advance", run.runtimeRevision)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "任务入队失败"); setBusyAction(null); }
  }

  async function enqueueStop() {
    setBusyAction("stop"); setError(null);
    try { setQueuedTask(await enqueueExperimentAgentCommand(experimentId, run.runId, "stop", run.runtimeRevision)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "终止任务入队失败"); setBusyAction(null); }
  }

  const canAdvance = run.status === "running";
  const canStop = run.status === "running" || run.status === "needsReview";
  const canRestart = run.status === "stopped";

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-[#dce4de] bg-[#173e32] px-6 py-6 text-white">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <div className="text-xs text-emerald-100/70">阶段 01 · 数据分析执行中心</div>
            <h1 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">从原始数据到仿真准入模型</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-50/70">七个计算环节按状态图协同推进。这里展示输入、算法、公式、指标、异常回退与人工门禁等可审计轨迹。</p>
          </div>
          <div className="grid grid-cols-3 gap-5 text-right">
            <Metric label="运行版本" value={`v${run.version}`} />
            <Metric label="编排运行时" value={run.runtimeBackend === "deterministic" ? "确定性状态图" : run.runtimeBackend} />
            <Metric label="LangGraph" value={runtimeStatus?.backends.find((item) => item.backend === "langgraph")?.enabled ? "已启用" : runtimeStatus?.backends.find((item) => item.backend === "langgraph")?.installed ? "已安装·未启用" : "未安装"} />
            <Metric label="运行检查点" value={runtimeStatus?.persistent ? `SQLite · 可恢复 ${runtimeStatus.recoverableRuns}` : "仅进程内存"} />
            <Metric label="任务队列" value={queueStatus ? `${queueStatus.backend}/${queueStatus.dispatchBackend} · 待执行 ${queueStatus.counts.queued ?? 0} · 可用槽位 ${queueStatus.workers.filter((worker) => worker.status === "online").reduce((sum, worker) => sum + worker.availableSlots, 0)}` : "读取中"} />
            <Metric label="本地模型" value={runtimeStatus?.localModel.configured ? `${runtimeStatus.localModel.provider} · ${runtimeStatus.localModel.model}` : "未配置"} />
            <Metric label="计算模块" value={agentCatalog ? `${agentCatalog.agentCount} 个模块 · ${agentCatalog.workflowCount} 套流程` : "读取中"} />
            <Metric label="总进度" value={`${run.progressPercent}%`} />
            <Metric label="当前状态" value={statusText[run.status]} />
          </div>
        </div>
        <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-[#79d0a5] transition-all" style={{ width: `${run.progressPercent}%` }} /></div>
      </section>

      {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-4">
          <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="font-semibold text-slate-950">执行状态图</h2><p className="mt-1 text-xs text-slate-500">点击任一环节，查看该节点的算法进程与证据。</p></div>
              <button className="rounded-lg bg-[#174333] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40" disabled={!canAdvance || busyAction !== null} onClick={enqueueAdvance} type="button">
                {busyAction === "advance" ? "后台任务处理中…" : "提交下一环节任务"}
              </button>
            </div>
            <div className="mt-5 grid gap-2 md:grid-cols-7">
              {run.nodes.map((node, index) => <NodeButton key={node.nodeId} node={node} index={index} selected={node.nodeId === selectedNode.nodeId} onSelect={() => setSelectedNodeId(node.nodeId)} />)}
            </div>
          </section>

          <NodeInspector node={selectedNode} />

          {selectedNode.nodeId === "schema-recognition" ? <SchemaRecognitionRunCard experimentId={experimentId} agentRunId={run.runId} /> : null}
          {selectedNode.nodeId === "model-evaluation" && selectedNode.status === "completed" ? <ResultInterpretationRunCard experimentId={experimentId} agentRunId={run.runId} /> : null}

          {run.status === "needsReview" ? (
            <HumanReviewPanel
              busy={busyAction !== null}
              operator={reviewOperator}
              reason={reviewReason}
              onOperatorChange={setReviewOperator}
              onReasonChange={setReviewReason}
              onSubmit={submitReview}
            />
          ) : null}

          <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
            <div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-950">可审计执行事件</h2><p className="mt-1 text-xs text-slate-500">所有状态变化和人工指令都会写入当前运行版本。</p></div><span className="font-mono text-xs text-slate-400">{run.events.length} EVENTS</span></div>
            <ol className="mt-5 space-y-0">
              {[...run.events].reverse().map((event) => (
                <li className="grid grid-cols-[1rem_1fr] gap-3" key={event.eventId}>
                  <div className="flex flex-col items-center"><span className="mt-1.5 h-2 w-2 rounded-full bg-[#397b5d]" /><span className="mt-1 h-full min-h-8 w-px bg-slate-200" /></div>
                  <div className="pb-4"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-medium text-slate-800">{event.title}</span><time className="font-mono text-[10px] text-slate-400">{formatTime(event.createdAt)}</time></div><p className="mt-1 text-xs leading-5 text-slate-500">{event.detail}</p></div>
                </li>
              ))}
            </ol>
          </section>

          {queuedTask ? <section className="rounded-2xl border border-blue-200 bg-blue-50 p-4"><div className="flex items-center justify-between gap-3"><div><div className="text-xs font-semibold text-blue-900">后台命令队列</div><p className="mt-1 font-mono text-[10px] text-blue-700">{queuedTask.taskId}</p></div><span className="rounded bg-white px-2 py-1 text-xs text-blue-800">{queuedTask.status} · 优先级 {queuedTask.priority} · 尝试 {queuedTask.attempts}/{queuedTask.maxAttempts}</span></div><p className="mt-3 text-xs text-blue-900/75">API 已返回，节点由 worker 持租约执行。租约心跳、重试和最终 revision 会持续写入任务记录。</p>{queuedTask.leaseOwner ? <p className="mt-2 text-[10px] text-blue-700">执行者：{queuedTask.leaseOwner} · 租约至 {queuedTask.leaseExpiresAt}</p> : null}<div className="mt-3 flex gap-2">{["queued", "leased"].includes(queuedTask.status) ? <button className="rounded border border-blue-300 bg-white px-3 py-1.5 text-xs text-blue-800" type="button" onClick={async () => { const next = await cancelAgentCommand(queuedTask.taskId, "用户从运行中心取消"); setQueuedTask(next); setBusyAction(null); }}>取消任务</button> : null}{queuedTask.status === "deadLetter" ? <button className="rounded bg-blue-800 px-3 py-1.5 text-xs text-white" type="button" onClick={async () => { const next = await replayAgentCommand(queuedTask.taskId); setQueuedTask(next); setBusyAction("advance"); }}>重放死信</button> : null}</div></section> : null}
        </div>

        <aside className="space-y-4">
          {agentCatalog ? <AgentManifestCard catalog={agentCatalog} agentKey={selectedNode.agentKey} /> : null}
          <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
            <div className="text-xs font-medium text-[#2f7054]">人工控制</div><h2 className="mt-1 font-semibold text-slate-950">运行控制与版本保留</h2>
            <p className="mt-3 text-xs leading-5 text-slate-500">终止不会删除本次记录；重新开始会创建新版本，并保留父运行编号。</p>
            <div className="mt-4 grid gap-2">
              <button className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700 disabled:opacity-40" disabled={!canStop || busyAction !== null} onClick={enqueueStop} type="button">提交终止任务</button>
              <button className="rounded-lg border border-[#b8cfc2] px-3 py-2 text-sm font-medium text-[#174333] disabled:opacity-40" disabled={!canRestart || busyAction !== null} onClick={() => perform("restart", () => restartExperimentAgentRun(experimentId, run.runId))} type="button">重新开始并创建新版本</button>
            </div>
            <div className="mt-4 border-t border-slate-100 pt-4 font-mono text-[10px] leading-5 text-slate-400"><div>RUN {run.runId}</div>{run.parentRunId ? <div>PARENT {run.parentRunId}</div> : null}</div>
          </section>

          <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
            <div className="text-xs font-medium text-[#2f7054]">提示词引导</div><h2 className="mt-1 font-semibold text-slate-950">先预览影响，再确认应用</h2>
            <textarea className="mt-4 min-h-28 w-full resize-y rounded-lg border border-slate-200 p-3 text-sm leading-6 outline-none focus:border-[#397b5d]" onChange={(event) => setPrompt(event.target.value)} placeholder="例如：字段识别优先采用企业内部温度和 pH 命名规则" value={prompt} />
            <button className="mt-2 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-40" disabled={prompt.trim().length < 2 || busyAction !== null} onClick={previewGuidance} type="button">{busyAction === "preview" ? "正在解析…" : "生成结构化影响预览"}</button>
            {guidance ? <GuidancePreview guidance={guidance} busy={busyAction !== null} onApply={applyGuidance} onRestart={restartWithGuidance} /> : null}
          </section>

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">{run.disclaimer}</div>
        </aside>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) { return <div><div className="text-[10px] text-emerald-100/60">{label}</div><div className="mt-1 font-mono text-sm font-semibold">{value}</div></div>; }

function AgentManifestCard({ catalog, agentKey }: { catalog: AgentCatalogSnapshot; agentKey: string }) {
  const agent = catalog.agents.find((item) => item.agentKey === agentKey);
  if (!agent) return null;
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="flex items-start justify-between gap-3"><div><div className="text-xs font-medium text-[#2f7054]">运行能力信息</div><h2 className="mt-1 font-semibold text-slate-950">{agent.displayName}</h2></div><span className="rounded bg-[#edf5f0] px-2 py-1 font-mono text-[10px] text-[#2f7054]">v{agent.version}</span></div><p className="mt-3 text-xs leading-5 text-slate-600">{agent.description}</p><dl className="mt-4 space-y-3 text-xs"><div><dt className="text-slate-400">编排框架</dt><dd className="mt-1 text-slate-700">{agent.framework} · {agent.kind}</dd></div><div><dt className="text-slate-400">运行资源</dt><dd className="mt-1 flex flex-wrap gap-1">{agent.requiredWorkerCapabilities.map((item) => <span className="rounded bg-slate-100 px-2 py-1 text-slate-600" key={item}>{item}</span>)}</dd></div><div><dt className="text-slate-400">输入 → 输出</dt><dd className="mt-1 font-mono text-[10px] text-slate-600">{agent.inputSchema} → {agent.outputSchema}</dd></div><div><dt className="text-slate-400">能力</dt><dd className="mt-1 text-slate-600">{agent.capabilities.join("、")}</dd></div></dl></section>;
}

function NodeButton({ node, index, selected, onSelect }: { node: AgentRunNode; index: number; selected: boolean; onSelect: () => void }) {
  return <button className={`relative min-h-28 rounded-xl border p-3 text-left transition ${selected ? "border-[#397b5d] bg-[#f0f7f3] ring-1 ring-[#397b5d]" : "border-slate-200 bg-white hover:border-slate-300"}`} onClick={onSelect} type="button"><div className="font-mono text-[10px] text-slate-400">{String(index + 1).padStart(2, "0")}</div><div className="mt-2 text-xs font-semibold leading-5 text-slate-800">{node.stageLabel}</div><span className={`mt-3 inline-flex rounded px-1.5 py-0.5 text-[9px] ring-1 ring-inset ${statusStyle[node.status]}`}>{statusText[node.status]}</span></button>;
}

function NodeInspector({ node }: { node: AgentRunNode }) {
  const groups = [["输入数据", node.inputSummary], ["方法、算法与公式", node.methodSummary], ["当前指标", node.metricSummary], ["节点输出", node.outputSummary.length ? node.outputSummary : ["等待该节点获得执行权"]]] as const;
  return <section className="rounded-2xl border border-[#dce4de] bg-white p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs text-slate-400">{node.agentName}</div><h2 className="mt-1 text-xl font-semibold text-slate-950">{node.stageLabel}算法进程</h2></div><span className={`rounded-md px-2 py-1 text-xs ring-1 ring-inset ${statusStyle[node.status]}`}>{statusText[node.status]} · {node.progressPercent}%</span></div><div className="mt-5 grid gap-3 md:grid-cols-2">{groups.map(([label, items]) => <div className="rounded-xl bg-[#f6f8f6] p-4" key={label}><h3 className="text-xs font-semibold text-slate-700">{label}</h3><ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">{items.map((item) => <li className="flex gap-2" key={item}><span className="text-[#397b5d]">—</span><span>{item}</span></li>)}</ul></div>)}</div></section>;
}

function GuidancePreview({ guidance, busy, onApply, onRestart }: { guidance: AgentGuidancePreview; busy: boolean; onApply: () => void; onRestart: () => void }) {
  return <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-4"><div className="text-xs font-semibold text-blue-900">影响预览</div><p className="mt-2 text-xs leading-5 text-blue-900/75">{guidance.intentSummary}</p><dl className="mt-3 space-y-2 text-xs"><div><dt className="text-blue-700">影响节点</dt><dd className="mt-1 text-slate-700">{guidance.affectedNodes.join("、")}</dd></div><div><dt className="text-blue-700">安全检查点</dt><dd className="mt-1 text-slate-700">{guidance.safeCheckpoint}</dd></div><div><dt className="text-blue-700">结果可比性</dt><dd className="mt-1 text-slate-700">{guidance.comparisonImpact}</dd></div></dl>{guidance.requiresRestart ? <><div className="mt-3 rounded bg-amber-100 px-3 py-2 text-xs text-amber-900">该变更影响模型/特征配置，确认后将终止当前运行，并把引导写入新的运行版本。</div><button className="mt-3 w-full rounded-lg bg-amber-700 px-3 py-2 text-xs font-medium text-white disabled:opacity-40" disabled={busy} onClick={onRestart} type="button">确认并创建引导版新运行</button></> : <button className="mt-3 w-full rounded-lg bg-blue-700 px-3 py-2 text-xs font-medium text-white disabled:opacity-40" disabled={busy} onClick={onApply} type="button">确认并在安全检查点应用</button>}</div>;
}

function HumanReviewPanel({ busy, operator, reason, onOperatorChange, onReasonChange, onSubmit }: { busy: boolean; operator: string; reason: string; onOperatorChange: (value: string) => void; onReasonChange: (value: string) => void; onSubmit: (decision: "approved" | "rejected") => void }) {
  const ready = operator.trim().length > 0 && reason.trim().length >= 2;
  return <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><div className="text-xs font-medium text-amber-800">人工确认检查点</div><h2 className="mt-1 text-lg font-semibold text-slate-950">记录决策、理由与影响范围</h2><p className="mt-2 text-xs leading-5 text-slate-600">这一步保留研发人员的最终判断。提交后，操作人和理由将写入当前运行的审计事件。</p><div className="mt-4 grid gap-3 sm:grid-cols-[14rem_1fr]"><label className="text-xs font-medium text-slate-600">操作人<input className="mt-2 h-10 w-full rounded-lg border border-amber-200 bg-white px-3 text-sm outline-none" onChange={(event) => onOperatorChange(event.target.value)} value={operator} /></label><label className="text-xs font-medium text-slate-600">决策理由<input className="mt-2 h-10 w-full rounded-lg border border-amber-200 bg-white px-3 text-sm outline-none" onChange={(event) => onReasonChange(event.target.value)} placeholder="说明字段映射、异常点和模型指标的复核结论" value={reason} /></label></div><div className="mt-4 flex flex-wrap gap-2"><button className="rounded-lg bg-[#174333] px-4 py-2 text-sm font-medium text-white disabled:opacity-40" disabled={!ready || busy} onClick={() => onSubmit("approved")} type="button">确认通过并开放模型版本</button><button className="rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 disabled:opacity-40" disabled={!ready || busy} onClick={() => onSubmit("rejected")} type="button">驳回并终止本次运行</button></div></section>;
}

function formatTime(value: string) { const date = new Date(value); return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(date); }
