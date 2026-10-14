import { ProductInnovationWorkbench } from "@/components/experiments/product-innovation-workbench";
import { getExperimentWorkspaceOverview, getLatestProductInnovationRun, getLatestProductRequirementVersion, getProductInnovationRun } from "@/lib/api";

export default async function ProductInnovationPage({ params }: Readonly<{ params: Promise<{ experimentId: string }> }>) {
  const { experimentId } = await params;
  const overview = await getExperimentWorkspaceOverview(experimentId);
  const confirmed = await getLatestProductRequirementVersion(experimentId).catch(() => null);
  const run = confirmed
    ? await getProductInnovationRun(experimentId, confirmed.sourceRunId).catch(() => null)
    : await getLatestProductInnovationRun(experimentId).catch(() => null);
  return <ProductInnovationWorkbench
    experimentId={experimentId}
    initialRun={run}
    initialConfirmed={confirmed}
    initialBrief={`${overview.objective}；目标产物：${overview.targetProduct ?? "待定义产物"}`}
    initialIndustry={overview.sourceType === "sample" ? "菌藻培养与生物制造" : ""}
  />;
}
