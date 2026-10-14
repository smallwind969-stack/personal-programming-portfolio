import {
  ExperimentStageAccess,
  requireExperimentStage,
} from "@/components/experiments/experiment-stage-access";
import { SimulationRuntimeWorkbench } from "@/components/simulation/simulation-runtime-workbench";
import { FeatureBindingAdvisorPanel } from "@/components/simulation/feature-binding-advisor-panel";
import { StageHandoffStrip } from "@/components/experiments/stage-handoff-strip";
import { getDeviceAdapterPacks, getExperimentWorkspaceOverview, getLatestExperimentSimulationRun, getPromotedModels } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ExperimentSimulationPage({ params }: Readonly<{ params: Promise<{ experimentId: string }> }>) {
  const { experimentId } = await params;
  const [overview, run, promotedModels, adapterPacks] = await Promise.all([
    getExperimentWorkspaceOverview(experimentId),
    getLatestExperimentSimulationRun(experimentId),
    getPromotedModels(experimentId),
    getDeviceAdapterPacks(),
  ]);
  const stage = requireExperimentStage(overview.stages, "simulation");
  return (
    <ExperimentStageAccess experimentId={experimentId} stage={stage}>
      <div className="space-y-5">
        <StageHandoffStrip experimentId={experimentId} phase="simulation" stages={overview.stages} />
        {overview.sourceType === "sample" ? (
          <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-950">
            <div className="text-xs font-semibold tracking-[0.12em] text-amber-800">隔离演示通道</div>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">当前不需要设备特征绑定</h2>
            <p className="mt-2">本页面使用规则代理完成交互演示，并保留训练轮次血缘。结果不能登记为真实测量、晋升正式模型或发送到设备。</p>
          </section>
        ) : <FeatureBindingAdvisorPanel experimentId={experimentId} promotedModels={promotedModels} adapterPacks={adapterPacks} activeBindingVersions={run.bindingVersions} parameterDefinitions={overview.productionContext.parameterDefinitions} />}
        <SimulationRuntimeWorkbench demoMode={overview.sourceType === "sample"} experimentId={experimentId} initialRun={run} productionContext={overview.productionContext} />
      </div>
    </ExperimentStageAccess>
  );
}
