import {
  ExperimentStageAccess,
  requireExperimentStage,
} from "@/components/experiments/experiment-stage-access";
import { ExperimentalFeedbackWorkbench } from "@/components/optimization/experimental-feedback-workbench";
import { FeedbackRetrainingWorkbench } from "@/components/optimization/feedback-retraining-workbench";
import { OptimizationWorkbench } from "@/components/optimization/optimization-workbench";
import { SupplementaryExecutionWorkbench } from "@/components/optimization/supplementary-execution-workbench";
import { SupplementaryExperimentWorkbench } from "@/components/optimization/supplementary-experiment-workbench";
import { SupplementaryMeasurementWorkbench } from "@/components/optimization/supplementary-measurement-workbench";
import { StageHandoffStrip } from "@/components/experiments/stage-handoff-strip";
import {
  getExperimentWorkspaceOverview,
  getFeedbackRetrainingRuns,
  getLatestOptimizationRun,
  getModelEvaluationReports,
  getOptimizationRuns,
  getSupplementaryDesignRuns,
  getSupplementaryExecutionBatches,
  getSupplementaryMeasurementBatches,
  getValidationBatches,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ExperimentOptimizationPage({ params }: Readonly<{ params: Promise<{ experimentId: string }> }>) {
  const { experimentId } = await params;
  const [overview, run, runs, batches, retrainingRuns, evaluationReports, supplementaryRuns, executionBatches, measurementBatches] = await Promise.all([
    getExperimentWorkspaceOverview(experimentId),
    getLatestOptimizationRun(experimentId),
    getOptimizationRuns(experimentId),
    getValidationBatches(experimentId),
    getFeedbackRetrainingRuns(experimentId),
    getModelEvaluationReports(experimentId),
    getSupplementaryDesignRuns(experimentId),
    getSupplementaryExecutionBatches(experimentId),
    getSupplementaryMeasurementBatches(experimentId),
  ]);
  const stage = requireExperimentStage(overview.stages, "optimization");

  if (overview.sourceType === "sample") {
    return (
      <ExperimentStageAccess experimentId={experimentId} stage={stage}>
        <div className="space-y-5">
          <StageHandoffStrip experimentId={experimentId} phase="optimization" stages={overview.stages} />
          <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-950">
            <div className="text-xs font-semibold tracking-[0.12em] text-amber-800">隔离演示通道</div>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">三套方案只用于体验决策流程</h2>
            <p className="mt-2">候选分数和响应面来自确定性规则代理，不是已晋升模型的产线预测。真实测量、补实验执行和反馈重训练仅以只读准入预览展示。</p>
          </section>
          <OptimizationWorkbench demoMode experimentId={experimentId} initialRun={run} />
          <SampleFeedbackLoopPreview />
        </div>
      </ExperimentStageAccess>
    );
  }

  const approvedRuns = runs.filter((item) => item.status === "completed" && item.officialParameterVersion && item.newResultVersion);
  const latestReport = evaluationReports.at(-1) ?? null;
  return (
    <ExperimentStageAccess experimentId={experimentId} stage={stage}>
      <div className="space-y-5">
        <StageHandoffStrip experimentId={experimentId} phase="optimization" stages={overview.stages} />
        <OptimizationWorkbench experimentId={experimentId} initialRun={run} />
        <SupplementaryExperimentWorkbench experimentId={experimentId} latestReport={latestReport} initialRuns={supplementaryRuns}/>
        <SupplementaryExecutionWorkbench experimentId={experimentId} approvedDesigns={supplementaryRuns.filter((item) => item.status === "approved" && item.planVersion)} initialBatches={executionBatches}/>
        <SupplementaryMeasurementWorkbench experimentId={experimentId} completedExecutions={executionBatches.filter((item) => item.status === "completed")} initialBatches={measurementBatches}/>
        <ExperimentalFeedbackWorkbench experimentId={experimentId} approvedRuns={approvedRuns} initialBatches={batches}/>
        <FeedbackRetrainingWorkbench experimentId={experimentId} batches={batches} initialRuns={retrainingRuns}/>
      </div>
    </ExperimentStageAccess>
  );
}

function SampleFeedbackLoopPreview() {
  const steps = [
    ["01", "现实验证批次", "等待企业真实实验回传；示例数据不会创建验证批次。"],
    ["02", "反馈数据集", "需要独立批次、质量检查和人工确认后才能形成训练资产。"],
    ["03", "权重更新与复评", "需要至少三批合格反馈，并在留出集上重新评估后才开放。"],
  ];
  return <section className="rounded-2xl border border-slate-200 bg-white p-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-xs font-semibold tracking-[0.12em] text-slate-500">后续闭环预览</p><h2 className="mt-1 text-xl font-semibold text-slate-950">现实验证 → 反馈数据 → 模型复评</h2><p className="mt-2 text-sm leading-6 text-slate-600">示例模式只展示准入顺序，不写入虚构反馈、不伪造重训练结果。</p></div>
      <span className="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-800">等待真实实验</span>
    </div>
    <div className="mt-5 grid gap-3 md:grid-cols-3">{steps.map(([index, title, detail]) => <article className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4" key={index}><div className="font-mono text-xs text-slate-400">{index}</div><h3 className="mt-2 font-semibold text-slate-800">{title}</h3><p className="mt-2 text-xs leading-5 text-slate-600">{detail}</p><span className="mt-4 inline-flex rounded bg-white px-2 py-1 text-[10px] text-slate-500">暂未开放</span></article>)}</div>
  </section>;
}
