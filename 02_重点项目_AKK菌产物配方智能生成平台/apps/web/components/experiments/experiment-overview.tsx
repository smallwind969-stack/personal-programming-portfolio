import Link from "next/link";

import {
  stageHref,
  statusClasses,
  statusLabels,
} from "@/components/experiments/experiment-status";
import type {
  DataCollectionLocalizationRun,
  ExperimentFileAsset,
  ExperimentStageSummary,
  ExperimentWorkspaceOverview,
} from "@/lib/schemas";
import { FirstDataIntakeWorkbench } from "@/components/experiments/first-data-intake-workbench";
import { ExperimentFileAssetsCard } from "@/components/experiments/experiment-file-assets-card";

const stageAgents: Record<ExperimentStageSummary["stage"], string[]> = {
  dataAnalysis: ["数据收集与定位", "清洗与时间对齐", "特征工程与数学建模"],
  simulation: ["虚拟产线编排", "仪器参数临时试算", "产物结果预测"],
  optimization: ["优化策略生成", "参数搜索与方案对比", "现实反馈与模型重训练"],
};

export function ExperimentOverview({ overview, initialIntakeRun = null, fileAssets = [] }: { overview: ExperimentWorkspaceOverview; initialIntakeRun?: DataCollectionLocalizationRun | null; fileAssets?: ExperimentFileAsset[] }) {
  const confidence = overview.confidenceScore;
  return (
    <div className="rounded-2xl border border-[#dce4de] bg-[#fbfcfb] px-5 pb-7 pt-6 shadow-[0_20px_60px_rgba(28,55,43,0.06)] sm:px-7">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="font-mono text-xs text-slate-400">实验总览 / {overview.experimentId}</div>
          <h1 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-slate-950 sm:text-3xl">{overview.name}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{overview.objective}</p>
          <div className="mt-2 text-xs text-slate-400">
            {overview.batchCode ? `批次 ${overview.batchCode} · ` : ""}更新于 {formatDate(overview.updatedAt)}
          </div>
        </div>
        <span className="rounded-md bg-amber-50 px-3 py-1.5 text-xs text-amber-800 ring-1 ring-inset ring-amber-200">{overview.statusLabel}</span>
      </header>

      <ProductionContextCard overview={overview} />

      <section className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-xl bg-[#173e32] px-5 py-4 text-white">
          <div className="text-xs text-emerald-100/70">综合模型可靠性</div>
          <div className="mt-3 font-mono text-3xl font-semibold tabular-nums">{confidence === null ? "--" : `${(confidence * 100).toFixed(1)}%`}</div>
          <div className="mt-3 h-1 overflow-hidden rounded bg-white/15"><div className="h-full bg-[#9dd4bb]" style={{ width: `${(confidence ?? 0) * 100}%` }} /></div>
        </article>
        {overview.reliabilityMetrics.map((metric) => (
          <MetricCard detail={metric.detail} key={metric.label} label={metric.label} value={metric.value} />
        ))}
      </section>

      <section className="mt-6 rounded-xl border border-[#dde5df] bg-white p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-slate-900">三阶段实验工作流</h2>
          <span className="text-xs text-slate-400">所有步骤保留运行和人工确认记录</span>
        </div>
        <div className="mt-4 grid gap-3 xl:grid-cols-3">
          {overview.stages.map((stage, index) => (
            <StageCard experimentId={overview.experimentId} index={index} key={stage.stage} stage={stage} />
          ))}
        </div>
      </section>

      <section className="mt-5 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <article className="rounded-xl border border-[#dde5df] bg-white p-5">
          <h2 className="font-semibold text-slate-900">当前结果摘要</h2>
          {overview.resultMetrics.length ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {overview.resultMetrics.map((metric) => <MetricCard detail={metric.detail} key={metric.label} label={metric.label} value={metric.value} />)}
            </div>
          ) : <p className="mt-4 text-sm text-slate-500">当前还没有可用的实验结果。</p>}
        </article>
        <article className="rounded-xl border border-[#dde5df] bg-white p-5">
          <h2 className="font-semibold text-slate-900">建模依据</h2>
          <dl className="mt-4 grid gap-3 text-sm">
            <div><dt className="text-xs text-slate-400">模型类型</dt><dd className="mt-1 font-medium text-slate-800">{overview.modelType}</dd></div>
            <div><dt className="text-xs text-slate-400">模型版本</dt><dd className="mt-1 font-mono text-slate-800">{overview.modelVersion}</dd></div>
          </dl>
        </article>
      </section>

      {overview.modelVersion === "untrained" ? <FirstDataIntakeWorkbench overview={overview} initialRun={initialIntakeRun} /> : null}

      <div className="mt-5">
        <ExperimentFileAssetsCard assets={fileAssets} experimentId={overview.experimentId} />
      </div>

      <section className="mt-5 grid gap-4 xl:grid-cols-2">
        <ReviewList items={overview.riskItems} title="具体风险事项" />
        <ReviewList items={overview.validationItems} title="待验证与人工确认" />
      </section>

      <p className="mt-5 text-xs leading-5 text-slate-500">
        当前输出为研发实验建议，需经过实际实验和人工验收，不直接作为生产指令。
      </p>
    </div>
  );
}

function ProductionContextCard({ overview }: { overview: ExperimentWorkspaceOverview }) {
  const context = overview.productionContext;
  return <section className="mt-5 rounded-xl border border-[#dce4de] bg-white px-4 py-4" aria-label="产线业务上下文"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[10px] font-semibold tracking-[0.12em] text-[#397b5d]">业务上下文</p><h2 className="mt-1 font-semibold text-slate-900">{context.industry} · {context.processType}</h2></div><span className="rounded-full bg-[#eef5f0] px-3 py-1 text-[10px] text-[#246247]">随实验版本锁定</span></div><dl className="mt-4 grid gap-3 text-xs sm:grid-cols-3"><div><dt className="text-slate-400">产线或装置</dt><dd className="mt-1 text-slate-700">{context.lineName ?? "暂未登记"}</dd></div><div><dt className="text-slate-400">物料体系</dt><dd className="mt-1 text-slate-700">{context.materialSystem ?? "暂未登记"}</dd></div><div><dt className="text-slate-400">关键工艺参数</dt><dd className="mt-1 text-slate-700">{context.criticalParameters.length ? context.criticalParameters.join("、") : "将依据设备数据识别"}</dd></div></dl>{context.parameterDefinitions.length ? <div className="mt-4 border-t border-slate-100 pt-3"><p className="text-[10px] text-slate-400">参数字典 · {context.parameterDefinitions.length} 项</p><div className="mt-2 flex flex-wrap gap-2">{context.parameterDefinitions.map((parameter) => <span className="rounded-lg bg-[#f3f7f4] px-2.5 py-1.5 text-[11px] text-slate-700" key={`${parameter.key}-${parameter.label}`}>{parameter.label}{parameter.unit ? `（${parameter.unit}）` : ""}{parameter.min !== null && parameter.max !== null ? ` ${parameter.min}–${parameter.max}` : " · 待校准"}</span>)}</div></div> : null}</section>;
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="rounded-xl border border-[#e0e6e2] bg-[#f8faf8] px-4 py-3"><div className="text-xs text-slate-500">{label}</div><div className="mt-2 font-mono text-xl font-semibold tabular-nums text-slate-900">{value}</div><div className="mt-2 text-xs leading-5 text-slate-500">{detail}</div></article>;
}

function StageCard({ experimentId, index, stage }: { experimentId: string; index: number; stage: ExperimentStageSummary }) {
  const content = <><div className="flex items-center justify-between gap-3"><div className="text-xs text-slate-400">阶段 {String(index + 1).padStart(2, "0")}</div><span className={`rounded-md px-2 py-1 text-[10px] ring-1 ring-inset ${statusClasses[stage.status]}`}>{statusLabels[stage.status]}</span></div><h3 className="mt-3 font-semibold text-slate-900">{stage.label}</h3><ul className="mt-3 space-y-1.5 text-xs leading-5 text-slate-500">{stageAgents[stage.stage].map((agent) => <li key={agent}>· {agent}</li>)}</ul><p className="mt-3 text-xs leading-5 text-slate-500">{stage.detail}</p></>;
  return stage.canEnter ? <Link className="focus-ring rounded-xl border border-[#dce4de] bg-white p-4 transition hover:-translate-y-0.5 hover:border-[#9eb9aa] hover:shadow-[0_12px_30px_rgba(28,55,43,0.06)]" href={stageHref(experimentId, stage.stage)}>{content}<div className="mt-4 text-xs font-medium text-[#174333]">进入工作区 →</div></Link> : <article className="rounded-xl border border-dashed border-[#d7ddd9] bg-[#f7f8f7] p-4 text-slate-500">{content}<div className="mt-4 text-xs">当前阶段已锁定</div></article>;
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  return <article className="rounded-xl border border-[#dde5df] bg-white p-5"><h2 className="font-semibold text-slate-900">{title}</h2>{items.length ? <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">{items.map((item) => <li className="flex gap-2" key={item}><span aria-hidden className="text-[#397b5d]">—</span><span>{item}</span></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">暂无记录。</p>}</article>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Shanghai" }).format(new Date(value));
}
