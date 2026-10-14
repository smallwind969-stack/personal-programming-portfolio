import Link from "next/link";

import type { AgentCommandSummary, AgentQueueStatus, AgentTaskCenter, ExperimentArchiveResponse, HumanActionCenter } from "@/lib/schemas";

const statusText: Record<string, string> = {
  waiting: "等待前置环节", running: "运行中", interrupted: "已中断", needsReview: "待人工确认",
  completed: "已完成", failed: "失败", stopped: "已停止", queued: "排队中", leased: "执行中",
  deadLetter: "需排查", cancelled: "已取消",
};
const statusTone: Record<string, string> = {
  running: "bg-blue-50 text-blue-700", leased: "bg-blue-50 text-blue-700",
  completed: "bg-emerald-50 text-emerald-700", needsReview: "bg-amber-50 text-amber-800",
  queued: "bg-amber-50 text-amber-800", failed: "bg-red-50 text-red-700", deadLetter: "bg-red-50 text-red-700",
  interrupted: "bg-orange-50 text-orange-700", stopped: "bg-slate-100 text-slate-600",
  waiting: "bg-slate-100 text-slate-600", cancelled: "bg-slate-100 text-slate-600",
};
const targetText: Record<string, string> = { agentRun: "数据分析", simulationRun: "仿真模拟", optimizationRun: "工艺优化" };
const actionText: Record<string, string> = {
  advance: "继续运行", stop: "停止", retry: "重新运行", create: "创建任务",
  simulationCreate: "创建仿真", simulationAdvance: "推进仿真", simulationStop: "停止仿真", simulationRetry: "重试仿真",
  optimizationCreate: "创建优化", optimizationAdvance: "推进优化", optimizationStop: "停止优化", optimizationRetry: "重试优化",
};

export function GlobalRunCenter({ archive, commands, humanActions, queue, taskCenters }: {
  archive: ExperimentArchiveResponse; commands: AgentCommandSummary[]; humanActions: HumanActionCenter;
  queue: AgentQueueStatus; taskCenters: AgentTaskCenter[];
}) {
  const experimentNames = new Map(archive.experiments.map((item) => [item.experimentId, item.name]));
  const onlineWorkers = queue.workers.filter((worker) => worker.status === "online");
  const activeCommands = (queue.counts.queued ?? 0) + (queue.counts.leased ?? 0);
  return <main className="mx-auto max-w-7xl space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-xs font-medium text-[#397b5d]">全局运行记录</p><h1 className="mt-1 text-3xl font-semibold tracking-[-0.035em] text-slate-950">流程运行中心</h1><p className="mt-2 text-sm text-slate-500">查看实验阶段、计算进度、执行队列和人工确认事项。</p></div>
      <div className="flex gap-2"><Link className="rounded-lg border border-[#cbd8d0] bg-white px-4 py-2 text-sm text-[#174333]" href="/human-actions">人工操作中心</Link><Link className="rounded-lg border border-[#cbd8d0] bg-white px-4 py-2 text-sm text-[#174333]" href="/">返回实验归档</Link></div>
    </header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="进行中的实验" value={`${archive.runningCount}`} detail={`共 ${archive.totalCount} 项实验`} />
      <Metric label="在线执行器" value={`${onlineWorkers.length}`} detail={`${onlineWorkers.reduce((sum, item) => sum + item.availableSlots, 0)} 个可用执行位`} />
      <Metric label="队列中的任务" value={`${activeCommands}`} detail={`${queue.counts.completed ?? 0} 项已完成`} />
      <Metric label="待人工确认" value={`${humanActions.totalCount}`} detail={`${humanActions.highPriorityCount} 项高优先级`} />
    </section>

    <section className="rounded-2xl border border-[#dce4de] bg-white">
      <div className="border-b border-[#e4eae6] px-5 py-4"><h2 className="font-semibold text-slate-900">实验与计算进程</h2><p className="mt-1 text-xs text-slate-500">进度来自各实验的真实流程状态，不在本页面重复修改。</p></div>
      <div className="divide-y divide-[#e8ede9]">{taskCenters.length ? taskCenters.map((center) => {
        const experiment = archive.experiments.find((item) => item.experimentId === center.experimentId);
        return <article className="p-5" key={center.experimentId}>
          <div className="flex flex-wrap items-center justify-between gap-3"><div><Link className="font-semibold text-slate-900 hover:text-[#174333]" href={`/experiments/${center.experimentId}`}>{experiment?.name ?? center.experimentId}</Link><p className="mt-1 text-xs text-slate-400">{center.experimentId} · 更新于 {formatTime(experiment?.updatedAt ?? center.generatedAt)}</p></div><div className="flex items-center gap-3"><Status status={center.overallStatus}/><span className="font-mono text-sm font-semibold text-[#246247]">{center.progressPercent}%</span></div></div>
          <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[#edf1ee]"><div className="h-full rounded-full bg-[#397b5d]" style={{ width: `${center.progressPercent}%` }}/></div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">{center.tasks.map((task) => <Link className="rounded-xl border border-[#e1e7e3] p-4 transition hover:border-[#8db39f] hover:bg-[#f8faf8]" href={task.route} key={task.taskId}><div className="flex items-center justify-between gap-2"><span className="text-sm font-medium">{task.agentName}</span><Status status={task.status}/></div><div className="mt-3 flex items-end justify-between"><span className="text-xs text-slate-500 line-clamp-2">{task.summary}</span><span className="ml-3 font-mono text-xs text-slate-600">{task.progressPercent}%</span></div>{task.blockedReasons.length ? <p className="mt-2 text-[11px] text-amber-700">等待：{task.blockedReasons[0]}</p> : null}</Link>)}</div>
        </article>;
      }) : <p className="p-8 text-center text-sm text-slate-500">暂无可读取的运行进程。</p>}</div>
    </section>

    <div className="grid gap-6 xl:grid-cols-[1.45fr_.55fr]">
      <section className="overflow-hidden rounded-2xl border border-[#dce4de] bg-white"><div className="border-b border-[#e4eae6] px-5 py-4"><h2 className="font-semibold">最近执行记录</h2><p className="mt-1 text-xs text-slate-500">仅显示审计摘要，不展示提示词、命令载荷和安全凭据。</p></div><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-[#f7f9f7] text-xs text-slate-500"><tr><th className="px-5 py-3">更新时间</th><th className="px-4 py-3">实验</th><th className="px-4 py-3">环节 / 动作</th><th className="px-4 py-3">状态</th><th className="px-4 py-3">执行</th></tr></thead><tbody className="divide-y divide-[#edf0ee]">{commands.length ? commands.map((command) => <tr key={command.taskId}><td className="whitespace-nowrap px-5 py-3 text-xs text-slate-500">{formatTime(command.updatedAt)}</td><td className="px-4 py-3"><Link className="font-medium text-slate-800 hover:text-[#174333]" href={`/experiments/${command.experimentId}`}>{experimentNames.get(command.experimentId) ?? command.experimentId}</Link></td><td className="px-4 py-3 text-slate-600">{targetText[command.targetKind] ?? command.targetKind} · {actionText[command.action] ?? command.action}</td><td className="px-4 py-3"><Status status={command.status}/>{command.errorCategory ? <div className="mt-1 text-[10px] text-red-600">{command.errorCategory}</div> : null}</td><td className="px-4 py-3 font-mono text-xs text-slate-500">{command.attempts}/{command.maxAttempts}</td></tr>) : <tr><td className="px-5 py-8 text-center text-slate-500" colSpan={5}>暂无持久化执行记录。</td></tr>}</tbody></table></div></section>

      <aside className="space-y-6"><section className="rounded-2xl border border-[#dce4de] bg-white p-5"><h2 className="font-semibold">执行底座</h2><div className="mt-4 space-y-3"><Line label="队列" value={queue.persistent ? "持久化" : "临时"}/><Line label="调度方式" value={queue.dispatchBackend === "polling" ? "轮询 Worker" : "分布式调度"}/><Line label="失败 / 待排查" value={`${queue.counts.failed ?? 0} / ${queue.counts.deadLetter ?? 0}`}/></div><div className="mt-4 space-y-2">{queue.workers.map((worker) => <div className="rounded-xl bg-[#f5f8f5] p-3" key={worker.workerId}><div className="flex items-center justify-between"><span className="text-xs font-medium">{worker.workerId}</span><span className={worker.status === "online" ? "text-xs text-emerald-700" : "text-xs text-slate-400"}>● {worker.status === "online" ? "在线" : "离线"}</span></div><p className="mt-2 text-[11px] text-slate-500">{worker.activeTasks} 项执行中 · {worker.availableSlots} 个空闲位</p></div>)}</div></section>
      <section className="rounded-2xl border border-[#dce4de] bg-[#f8faf8] p-5"><h2 className="font-semibold">人工控制边界</h2><p className="mt-2 text-sm leading-6 text-slate-600">待确认事项必须进入对应实验处理。运行中心只负责观察，不会自动批准模型、改写工艺参数或下发设备控制指令。</p></section></aside>
    </div>
  </main>;
}

function Metric({ detail, label, value }: { detail: string; label: string; value: string }) { return <article className="rounded-2xl border border-[#dce4de] bg-white p-5"><p className="text-xs text-slate-500">{label}</p><p className="mt-3 font-mono text-3xl font-semibold text-slate-950">{value}</p><p className="mt-2 text-xs text-slate-500">{detail}</p></article>; }
function Status({ status }: { status: string }) { return <span className={`whitespace-nowrap rounded-full px-2 py-1 text-[10px] font-medium ${statusTone[status] ?? "bg-slate-100 text-slate-600"}`}>{statusText[status] ?? status}</span>; }
function Line({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between text-sm"><span className="text-slate-500">{label}</span><span className="font-medium text-slate-800">{value}</span></div>; }
function formatTime(value: string) { return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value)); }
