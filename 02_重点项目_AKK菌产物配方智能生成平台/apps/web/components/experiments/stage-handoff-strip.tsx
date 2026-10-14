import Link from "next/link";

import { stageHref, statusClasses, statusLabels } from "@/components/experiments/experiment-status";
import type { ExperimentStageSummary } from "@/lib/schemas";

type HandoffPhase = "dataAnalysis" | "simulation" | "optimization" | "report";

const phaseCopy: Record<HandoffPhase, { eyebrow: string; input: string; work: string; output: string; next: string }> = {
  dataAnalysis: {
    eyebrow: "原始记录进入可复用模型",
    input: "设备文件、实验目标与字段确认",
    work: "清洗对齐、特征计算与可靠性复核",
    output: "锁定数据快照、模型版本与准入结论",
    next: "仿真模拟",
  },
  simulation: {
    eyebrow: "数学映射进入虚拟产线",
    input: "已准入模型、参数边界与设备映射",
    work: "分阶段推演、状态观测与风险校验",
    output: "正式仿真快照、预测结果与不确定性",
    next: "工艺优化",
  },
  optimization: {
    eyebrow: "预测结果进入方案决策",
    input: "正式仿真快照、约束条件与目标指标",
    work: "候选搜索、响应比较与人工定版",
    output: "工艺参数版本、结果版本与现实验证计划",
    next: "实验报告",
  },
  report: {
    eyebrow: "全过程证据进入企业资产",
    input: "数据、模型、仿真与工艺版本",
    work: "证据冻结、边界标记与人工审核",
    output: "可追溯报告；审核后可沉淀企业规律",
    next: "企业规律",
  },
};

export function StageHandoffStrip({
  experimentId,
  phase,
  stages,
}: {
  experimentId: string;
  phase: HandoffPhase;
  stages: ExperimentStageSummary[];
}) {
  const copy = phaseCopy[phase];
  const stage = phase === "report" ? stages.at(-1) : stages.find((item) => item.stage === phase);
  const nextStage = phase === "dataAnalysis"
    ? stages.find((item) => item.stage === "simulation")
    : phase === "simulation"
      ? stages.find((item) => item.stage === "optimization")
      : null;
  const nextHref = phase === "optimization"
    ? `/experiments/${encodeURIComponent(experimentId)}/reports`
    : phase === "report"
      ? "/knowledge-assets"
      : nextStage && nextStage.canEnter
        ? stageHref(experimentId, nextStage.stage)
        : null;

  return (
    <section className="rounded-2xl border border-[#dce4de] bg-[#f7f9f7] p-4 sm:p-5" aria-label="阶段交接">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold tracking-[0.14em] text-[#397b5d]">阶段交接</p>
          <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em] text-slate-950">{copy.eyebrow}</h1>
        </div>
        {stage ? <span className={`rounded-full px-3 py-1 text-[10px] ring-1 ring-inset ${statusClasses[stage.status]}`}>{statusLabels[stage.status]}</span> : null}
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch">
        <HandoffCell index="01" label="承接输入" value={copy.input} />
        <Arrow />
        <HandoffCell index="02" label="本阶段处理" value={copy.work} />
        <Arrow />
        <HandoffCell index="03" label="形成交付" value={copy.output} />
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-[#dfe6e1] pt-3 text-xs">
        <span className="text-slate-500">每次重算创建新版本，旧结果与人工决策继续保留。</span>
        {nextHref ? <Link className="font-medium text-[#174333] hover:underline" href={nextHref}>下一环节：{copy.next} →</Link> : <span className="text-amber-700">下一环节等待当前门禁通过</span>}
      </div>
    </section>
  );
}

function HandoffCell({ index, label, value }: { index: string; label: string; value: string }) {
  return <div className="rounded-xl border border-[#e1e7e3] bg-white p-3"><div className="flex items-center gap-2"><span className="font-mono text-[9px] text-[#6d8c7b]">{index}</span><b className="text-xs text-slate-800">{label}</b></div><p className="mt-2 text-xs leading-5 text-slate-500">{value}</p></div>;
}

function Arrow() {
  return <span aria-hidden className="hidden self-center text-slate-300 md:block">→</span>;
}
