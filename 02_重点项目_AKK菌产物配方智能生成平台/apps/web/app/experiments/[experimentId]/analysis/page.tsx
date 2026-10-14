import { AgentExecutionCenter } from "@/components/experiments/agent-execution-center";
import { analysisIntakeView } from "@/components/experiments/analysis-intake-view";
import { CleaningAlignmentWorkbench } from "@/components/experiments/cleaning-alignment-workbench";
import { DataAnalysisProgressPanel } from "@/components/experiments/data-analysis-progress";
import { DemoModelAdmissionPanel } from "@/components/experiments/demo-model-admission-panel";
import {
  ExperimentAdapterLineageCard,
  WaitingAnalysisAgentCenter,
} from "@/components/experiments/experiment-adapter-lineage-card";
import { ExperimentDatasetSnapshotCard } from "@/components/experiments/experiment-dataset-snapshot-card";
import { ExperimentEntryGuide } from "@/components/experiments/experiment-entry-guide";
import { FeatureEngineeringWorkbench } from "@/components/experiments/feature-engineering-workbench";
import { FirstDataIntakeWorkbench } from "@/components/experiments/first-data-intake-workbench";
import { ModelEvaluationWorkbench } from "@/components/experiments/model-evaluation-workbench";
import { KnowledgeUsageEvidenceCard } from "@/components/experiments/knowledge-usage-evidence-card";
import { StageHandoffStrip } from "@/components/experiments/stage-handoff-strip";
import {
  ExperimentStageAccess,
  requireExperimentStage,
} from "@/components/experiments/experiment-stage-access";
import { ResearchCampaignCenter } from "@/components/experiments/research-campaign-center";
import {
  getCleaningAlignmentRuns,
  getDataAnalysisProgress,
  getDemoModelAdmission,
  getFeatureEngineeringRuns,
  getModelEvaluationReports,
  getExperimentDataIntakeRuns,
  getExperimentWorkspaceOverview,
  getLatestExperimentAgentRun,
  getLatestExperimentDatasetSnapshot,
  getLatestExperimentTrainingResult,
  getEnterpriseKnowledgeUsage,
  listResearchCampaigns,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ExperimentAnalysisPage({
  params,
}: Readonly<{ params: Promise<{ experimentId: string }> }>) {
  const { experimentId } = await params;
  const [overview, intakeRuns, analysisProgress, demoAdmission, knowledgeUsages] = await Promise.all([
    getExperimentWorkspaceOverview(experimentId),
    getExperimentDataIntakeRuns(experimentId),
    getDataAnalysisProgress(experimentId),
    getDemoModelAdmission(experimentId),
    getEnterpriseKnowledgeUsage(experimentId),
  ]);
  const latestIntake = intakeRuns.at(-1) ?? null;
  const stage = requireExperimentStage(overview.stages, "dataAnalysis");

  if (overview.modelVersion === "untrained" && latestIntake?.status !== "confirmed") {
    return (
      <ExperimentStageAccess experimentId={experimentId} stage={stage}>
        <div className="space-y-4">
          <StageHandoffStrip experimentId={experimentId} phase="dataAnalysis" stages={overview.stages} />
          <ExperimentEntryGuide intakeRun={latestIntake} overview={overview} />
          <DataAnalysisProgressPanel progress={analysisProgress} />
          <KnowledgeUsageEvidenceCard experimentId={experimentId} usages={knowledgeUsages} />
          <div id="data-intake"><ExperimentAdapterLineageCard overview={overview} intakeRun={latestIntake} /></div>
          <div id="mapping-review">{analysisIntakeView(latestIntake) === "reviewEvidence" ? <FirstDataIntakeWorkbench initialRun={latestIntake} overview={overview} /> : <WaitingAnalysisAgentCenter experimentId={experimentId} />}</div>
        </div>
      </ExperimentStageAccess>
    );
  }

  const [run, campaigns, dataset, trainingResult, cleaningRuns, featureRuns, evaluationReports] = await Promise.all([
    getLatestExperimentAgentRun(experimentId),
    listResearchCampaigns(experimentId),
    getLatestExperimentDatasetSnapshot(experimentId),
    getLatestExperimentTrainingResult(experimentId),
    getCleaningAlignmentRuns(experimentId),
    getFeatureEngineeringRuns(experimentId),
    getModelEvaluationReports(experimentId),
  ]);
  const latestCleaning = cleaningRuns.at(-1) ?? null;
  const cleaningReady =
    latestCleaning?.status === "completed" || latestCleaning?.status === "confirmed";
  const latestFeatureRun = featureRuns.at(-1) ?? null;
  const featureReady = latestFeatureRun?.status === "confirmed";
  const latestEvaluationReport = evaluationReports.at(-1) ?? null;
  const hasPromotedModel = campaigns.some(
    (campaign) => campaign.promotion?.status === "approved",
  );

  return (
    <ExperimentStageAccess experimentId={experimentId} stage={stage}>
      <div className="space-y-4">
        <StageHandoffStrip experimentId={experimentId} phase="dataAnalysis" stages={overview.stages} />
        <ExperimentEntryGuide intakeRun={latestIntake} overview={overview} />
        <DataAnalysisProgressPanel progress={analysisProgress} />
        <KnowledgeUsageEvidenceCard experimentId={experimentId} usages={knowledgeUsages} />
        <span id="mapping-review" />
        <div id="data-intake"><ExperimentAdapterLineageCard overview={overview} intakeRun={latestIntake} /></div>
        <div id="cleaning-alignment"><CleaningAlignmentWorkbench experimentId={experimentId} initialRun={latestCleaning} /></div>
        <div id="dataset-snapshot"><ExperimentDatasetSnapshotCard
          blockedReason="请先完成数据清洗与时间轴对齐；如发现质量问题，还需要人工复核放行。"
          canCreate={cleaningReady}
          experimentId={experimentId}
          snapshot={dataset}
        /></div>
        {dataset.status === "modeling_ready" ? (
          <div id="feature-engineering"><FeatureEngineeringWorkbench
            experimentId={experimentId}
            initialRun={latestFeatureRun}
            snapshot={dataset}
          /></div>
        ) : null}
        <div id="modeling-evaluation"><AgentExecutionCenter experimentId={experimentId} initialRun={run} /></div>
        {featureReady ? (
          <ResearchCampaignCenter
            baselineMetrics={trainingResult.metrics}
            datasetSnapshotId={dataset.snapshotId}
            experimentId={experimentId}
            initialCampaigns={campaigns}
          />
        ) : (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
            建模实验中心已锁定。请先生成特征集，核对计算公式与泄漏审计结果，并由研发人员确认放行。
          </div>
        )}
        {overview.sourceType === "sample" ? (
          <DemoModelAdmissionPanel experimentId={experimentId} campaigns={campaigns} initialAdmission={demoAdmission} />
        ) : null}
        {featureReady ? (
          <ModelEvaluationWorkbench
            experimentId={experimentId}
            hasPromotedModel={hasPromotedModel}
            initialReport={latestEvaluationReport}
          />
        ) : null}
      </div>
    </ExperimentStageAccess>
  );
}
