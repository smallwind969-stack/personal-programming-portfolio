import type { ExperimentStageName, ExperimentStageStatus, ExperimentStageSummary } from "@/lib/schemas";

export const stageLabels: Record<ExperimentStageName, string> = {
  dataAnalysis: "数据分析",
  simulation: "仿真模拟",
  optimization: "工艺优化",
};

export const statusLabels: Record<ExperimentStageStatus, string> = {
  waiting: "等待中",
  running: "进行中",
  completed: "已完成",
  needsReview: "待人工确认",
  failed: "执行失败",
  stopped: "已终止",
};

export const statusClasses: Record<ExperimentStageStatus, string> = {
  waiting: "bg-amber-50 text-amber-800 ring-amber-200",
  running: "bg-blue-50 text-blue-800 ring-blue-200",
  completed: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  needsReview: "bg-slate-100 text-slate-700 ring-slate-200",
  failed: "bg-red-50 text-red-800 ring-red-200",
  stopped: "bg-stone-100 text-stone-700 ring-stone-200",
};

export function stageHref(experimentId: string, stage: ExperimentStageSummary["stage"]): string {
  const suffix: Record<ExperimentStageName, string> = {
    dataAnalysis: "analysis",
    simulation: "simulation",
    optimization: "optimization",
  };
  return `/experiments/${encodeURIComponent(experimentId)}/${suffix[stage]}`;
}
