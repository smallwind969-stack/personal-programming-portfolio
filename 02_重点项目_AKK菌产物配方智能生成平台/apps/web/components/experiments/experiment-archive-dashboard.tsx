"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { stageLabels, statusClasses, statusLabels } from "@/components/experiments/experiment-status";
import type {
  ExperimentArchiveItem,
  ExperimentArchiveResponse,
  ExperimentLifecycleSummary,
  ExperimentStageStatus,
  HumanActionCenter,
} from "@/lib/schemas";

type StatusFilter = "all" | ExperimentStageStatus;
type LifecycleFilter =
  | "all"
  | "dataAnalysis"
  | "modelEvaluation"
  | "supplementaryDesign"
  | "supplementaryExecution"
  | "measurementFeedback"
  | "feedbackRetraining";

const lifecycleFilterLabels: Record<Exclude<LifecycleFilter, "all">, string> = {
  dataAnalysis: "数据分析",
  modelEvaluation: "模型评估",
  supplementaryDesign: "补充实验设计",
  supplementaryExecution: "实验执行",
  measurementFeedback: "真实测量",
  feedbackRetraining: "反馈重训练",
};

export function ExperimentArchiveDashboard({
  archive,
  lifecycleSummaries = [],
  actionCenter,
}: {
  archive: ExperimentArchiveResponse;
  lifecycleSummaries?: ExperimentLifecycleSummary[];
  actionCenter?: HumanActionCenter;
}) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [lifecycleFilter, setLifecycleFilter] = useState<LifecycleFilter>("all");
  const [onlyPending, setOnlyPending] = useState(false);
  const lifecycleByExperiment = useMemo(
    () => new Map(lifecycleSummaries.map((item) => [item.experimentId, item])),
    [lifecycleSummaries],
  );

  const experiments = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("zh-CN");
    return archive.experiments.filter((experiment) => {
      const matchesQuery =
        !normalizedQuery ||
        [experiment.name, experiment.experimentId, experiment.batchCode ?? ""]
          .join(" ")
          .toLocaleLowerCase("zh-CN")
          .includes(normalizedQuery);
      const matchesStatus = statusFilter === "all" || experiment.status === statusFilter;
      const lifecycle = lifecycleByExperiment.get(experiment.experimentId);
      const matchesLifecycle =
        lifecycleFilter === "all" || lifecycle?.currentStageKey === lifecycleFilter;
      const pendingCount = actionCenter?.experimentActionCounts[experiment.experimentId] ?? 0;
      return matchesQuery && matchesStatus && matchesLifecycle && (!onlyPending || pendingCount > 0);
    });
  }, [actionCenter, archive.experiments, lifecycleByExperiment, lifecycleFilter, onlyPending, query, statusFilter]);

  return (
    <div className="overflow-hidden rounded-[1.25rem] border border-[#dce4de] bg-[#fbfcfb] shadow-[0_24px_70px_rgba(28,55,43,0.08)]">
      <div className="grid min-h-[calc(100vh-7.5rem)] lg:grid-cols-[13.5rem_1fr]">
        <ArchiveSidebar />
        <section className="min-w-0 px-5 pb-8 pt-7 sm:px-7 lg:px-9">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-[-0.03em] text-slate-950 sm:text-3xl">实验归档</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">管理当前终端的实验、阶段成果与模型可靠性</p>
            </div>
            <Link className="focus-ring inline-flex h-10 items-center rounded-lg bg-[#174333] px-4 text-sm font-medium text-white transition hover:bg-[#0f3528] active:translate-y-px" href="/experiments/new">
              <span aria-hidden className="mr-2 text-lg leading-none">+</span>新建实验
            </Link>
          </div>

          <ArchiveMetrics archive={archive} />
          {actionCenter ? <HumanActionQueue actionCenter={actionCenter} /> : null}

          <div className="mt-6 flex flex-col gap-3 xl:flex-row">
            <label className="flex-1">
              <span className="sr-only">搜索实验</span>
              <input className="focus-ring h-11 w-full rounded-lg border border-[#dce4de] bg-white px-4 text-sm outline-none placeholder:text-slate-400" onChange={(event) => setQuery(event.target.value)} placeholder="搜索实验名称、编号或批次……" type="search" value={query} />
            </label>
            <FilterSelect label="筛选状态" onChange={(value) => setStatusFilter(value as StatusFilter)} value={statusFilter}>
              <option value="all">全部状态</option>
              {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </FilterSelect>
            <FilterSelect label="筛选闭环节点" onChange={(value) => setLifecycleFilter(value as LifecycleFilter)} value={lifecycleFilter} wide>
              <option value="all">全部闭环节点</option>
              {Object.entries(lifecycleFilterLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </FilterSelect>
            <label className="flex h-11 items-center gap-2 rounded-lg border border-[#dce4de] bg-white px-3 text-sm text-slate-700">
              <input checked={onlyPending} onChange={(event) => setOnlyPending(event.target.checked)} type="checkbox" />
              只看有人工待办
            </label>
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-[#dde5df] bg-white">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] border-collapse text-left">
                <thead className="bg-[#f3f6f3] text-xs font-medium text-slate-500">
                  <tr><th className="px-5 py-3">实验名称 / 业务上下文</th><th className="px-4 py-3">闭环位置</th><th className="px-4 py-3">状态</th><th className="px-4 py-3">结果摘要</th><th className="px-4 py-3">置信度</th><th className="px-5 py-3"><span className="sr-only">操作</span></th></tr>
                </thead>
                <tbody className="divide-y divide-[#e8ede9]">
                  {experiments.map((experiment) => <ExperimentRow actionCount={actionCenter?.experimentActionCounts[experiment.experimentId] ?? 0} experiment={experiment} key={experiment.experimentId} lifecycle={lifecycleByExperiment.get(experiment.experimentId)} />)}
                </tbody>
              </table>
            </div>
            {experiments.length === 0 ? <div className="px-6 py-14 text-center"><p className="font-medium text-slate-700">没有找到匹配的实验</p><p className="mt-2 text-sm text-slate-500">请调整搜索词或筛选条件。</p></div> : null}
          </div>

          <p className="mt-4 text-xs leading-5 text-slate-500">当前结果用于研发分析、仿真模拟与工艺辅助决策，不直接作为实际生产指令。</p>
        </section>
      </div>
    </div>
  );
}

function FilterSelect({ children, label, onChange, value, wide = false }: { children: React.ReactNode; label: string; onChange: (value: string) => void; value: string; wide?: boolean }) {
  return <label><span className="sr-only">{label}</span><select className={`focus-ring h-11 rounded-lg border border-[#dce4de] bg-white px-3 text-sm text-slate-700 outline-none ${wide ? "min-w-44" : "min-w-40"}`} onChange={(event) => onChange(event.target.value)} value={value}>{children}</select></label>;
}

function ArchiveSidebar() {
  return <aside className="border-b border-[#dde5df] bg-[#f5f8f5] p-4 lg:border-b-0 lg:border-r">
    <nav aria-label="主导航" className="grid gap-1 sm:grid-cols-4 lg:grid-cols-1">
      <Link className="focus-ring rounded-xl bg-[#e2eee7] px-4 py-3 font-medium text-[#174333]" href="/">实验归档</Link>
      <Link className="focus-ring rounded-xl px-4 py-3 text-slate-500 transition hover:bg-white hover:text-[#174333]" href="/runs">运行记录</Link>
      <Link className="focus-ring rounded-xl px-4 py-3 text-slate-500 transition hover:bg-white hover:text-[#174333]" href="/human-actions">人工操作</Link>
      <Link className="focus-ring rounded-xl px-4 py-3 text-slate-500 transition hover:bg-white hover:text-[#174333]" href="/model-assets">模型资产</Link>
      <Link className="focus-ring rounded-xl px-4 py-3 text-slate-500 transition hover:bg-white hover:text-[#174333]" href="/knowledge-assets">企业规律</Link>
      <Link className="focus-ring rounded-xl px-4 py-3 text-slate-500 transition hover:bg-white hover:text-[#174333]" href="/settings">系统设置</Link>
    </nav>
    <div className="mt-8 hidden border-t border-[#dce4de] px-3 pt-5 text-xs leading-6 text-slate-500 lg:block"><div>当前终端</div><div className="font-medium text-slate-700">企业研发工作空间</div></div>
  </aside>;
}

function ArchiveMetrics({ archive }: { archive: ExperimentArchiveResponse }) {
  const cards = [
    { label: "实验总数", value: archive.totalCount.toString(), detail: "当前终端已归档" },
    { label: "进行中", value: archive.runningCount.toString(), detail: "包含正在推进的计算任务" },
    { label: "已完成", value: archive.completedCount.toString(), detail: "已生成验收版本" },
    { label: "平均置信度", value: `${(archive.averageConfidenceScore * 100).toFixed(1)}%`, detail: "按已建模实验计算" },
  ];
  return <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <article className="rounded-xl border border-[#dde5df] bg-white px-5 py-4" key={card.label}><div className="text-xs text-slate-500">{card.label}</div><div className="mt-3 font-mono text-2xl font-semibold tabular-nums text-slate-950">{card.value}</div><div className="mt-2 text-xs text-slate-500">{card.detail}</div></article>)}</div>;
}

function ExperimentRow({ experiment, lifecycle, actionCount }: { experiment: ExperimentArchiveItem; lifecycle?: ExperimentLifecycleSummary; actionCount: number }) {
  const confidence = experiment.confidenceScore;
  return <tr className="group transition-colors hover:bg-[#f8faf8]">
    <td className="px-5 py-4"><Link className="focus-ring rounded font-medium text-slate-900 group-hover:text-[#174333]" href={`/experiments/${experiment.experimentId}`}>{experiment.name}</Link><div className="mt-1 text-xs text-slate-500">{experiment.industry} · {experiment.processType}</div><div className="mt-1 text-xs text-slate-400">{experiment.experimentId}{experiment.batchCode ? ` · 批次 ${experiment.batchCode}` : " · 未分配批次"}</div></td>
    <td className="px-4 py-4 text-sm text-slate-700"><div className="font-medium text-slate-800">{lifecycle?.currentStageLabel ?? stageLabels[experiment.currentStage]}</div>{lifecycle ? <><div className="mt-2 h-1 w-24 overflow-hidden rounded bg-[#e5ebe7]"><div className="h-full bg-[#397b5d]" style={{ width: `${lifecycle.progressPercent}%` }} /></div><Link className="mt-2 block text-[10px] font-medium text-[#397b5d] hover:underline" href={lifecycle.route}>{lifecycle.nextAction} →</Link></> : null}</td>
    <td className="px-4 py-4"><span className={`inline-flex rounded-md px-2 py-1 text-xs ring-1 ring-inset ${statusClasses[experiment.status]}`}>{statusLabels[experiment.status]}</span>{actionCount > 0 ? <div className="mt-2 text-[10px] font-medium text-amber-700">{actionCount} 项人工待办</div> : null}</td>
    <td className="max-w-[16rem] px-4 py-4 text-sm text-slate-600">{experiment.resultSummary}</td>
    <td className="px-4 py-4">{confidence === null ? <span className="text-slate-400">--</span> : <div className="w-24"><div className="font-mono text-sm font-semibold tabular-nums text-[#24664a]">{(confidence * 100).toFixed(1)}%</div><div className="mt-2 h-1 overflow-hidden rounded bg-[#e5ebe7]"><div className="h-full bg-[#397b5d]" style={{ width: `${confidence * 100}%` }} /></div></div>}</td>
    <td className="px-5 py-4 text-right"><Link className="focus-ring rounded text-sm font-medium text-[#174333] hover:underline" href={`/experiments/${experiment.experimentId}`}>进入 <span aria-hidden>→</span></Link></td>
  </tr>;
}

function HumanActionQueue({ actionCenter }: { actionCenter: HumanActionCenter }) {
  const visible = actionCenter.items.slice(0, 6);
  return <section className="mt-6 rounded-xl border border-[#dce4de] bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-medium text-[#2f7054]">研发负责人工作队列</p><h2 className="mt-1 text-lg font-semibold text-slate-900">我的待处理</h2><p className="mt-1 text-xs text-slate-500">只汇总当前模型和计划血缘上的人工动作；点击后在对应工作台完成门禁。</p></div><div className="flex gap-2"><span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">共 {actionCenter.totalCount} 项</span>{actionCenter.highPriorityCount > 0 ? <span className="rounded-full bg-rose-50 px-3 py-1 text-xs text-rose-700">高优先级 {actionCenter.highPriorityCount}</span> : null}</div></div>
    {visible.length > 0 ? <div className="mt-4 grid gap-3 lg:grid-cols-2 xl:grid-cols-3">{visible.map((item) => <Link className="rounded-xl border border-slate-200 p-4 transition hover:border-[#7ca08d] hover:bg-[#f7faf8]" href={item.route} key={item.actionId}><div className="flex items-center justify-between gap-2"><span className={`rounded-full px-2 py-0.5 text-[10px] ${item.priority === "high" ? "bg-rose-50 text-rose-700" : item.priority === "medium" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"}`}>{item.priority === "high" ? "高优先级" : item.priority === "medium" ? "中优先级" : "常规"}</span><span className="text-[10px] text-slate-400">{lifecycleFilterLabels[item.stageKey]}</span></div><h3 className="mt-3 text-sm font-semibold text-slate-900">{item.title}</h3><p className="mt-1 text-xs text-slate-500">{item.experimentName}</p><p className="mt-2 text-xs leading-5 text-slate-600">{item.detail}</p>{item.blockedReasons.length > 0 ? <ul className="mt-2 text-[10px] text-amber-800">{item.blockedReasons.map((reason) => <li key={reason}>· {reason}</li>)}</ul> : null}<div className="mt-3 text-xs font-medium text-[#174333]">前往处理 →</div></Link>)}</div> : <p className="mt-4 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">当前没有需要人工处理的事项。</p>}
    {actionCenter.totalCount > visible.length ? <p className="mt-3 text-xs text-slate-500">当前优先展示前 {visible.length} 项；可使用“只看有人工待办”筛选相关实验。</p> : null}
    <p className="mt-3 text-[10px] text-slate-400">{actionCenter.disclaimer}</p>
  </section>;
}
