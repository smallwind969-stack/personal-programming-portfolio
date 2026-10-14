import { ResearchReportCenter } from "@/components/reports/research-report-center";
import { StageHandoffStrip } from "@/components/experiments/stage-handoff-strip";
import { getExperimentWorkspaceOverview, getResearchReports } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ReportsPage({ params }: { params: Promise<{ experimentId: string }> }) {
  const { experimentId } = await params;
  const [overview, reports] = await Promise.all([getExperimentWorkspaceOverview(experimentId), getResearchReports(experimentId)]);
  return <div className="space-y-5"><StageHandoffStrip experimentId={experimentId} phase="report" stages={overview.stages}/><ResearchReportCenter experimentId={experimentId} experimentName={overview.name} initialReports={reports}/></div>;
}
