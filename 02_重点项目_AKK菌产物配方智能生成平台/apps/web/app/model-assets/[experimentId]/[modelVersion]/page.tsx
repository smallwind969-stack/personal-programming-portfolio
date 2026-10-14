import { ModelAssetDetailView } from "@/components/model-assets/model-asset-detail";
import { getModelAssetDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ModelAssetDetailPage({ params }: { params: Promise<{ experimentId: string; modelVersion: string }> }) {
  const { experimentId, modelVersion } = await params;
  return <ModelAssetDetailView detail={await getModelAssetDetail(experimentId, modelVersion)} />;
}
