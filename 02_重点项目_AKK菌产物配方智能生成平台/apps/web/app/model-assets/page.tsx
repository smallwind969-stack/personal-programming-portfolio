import { ModelAssetCenter } from "@/components/model-assets/model-asset-center";
import { getModelAssets } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ModelAssetsPage() {
  return <ModelAssetCenter assets={await getModelAssets()} />;
}
