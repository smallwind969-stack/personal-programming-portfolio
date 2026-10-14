import { DeviceAdapterWorkbench } from "@/components/model-assets/device-adapter-workbench";
import { getDeviceAdapterPacks } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DeviceAdaptersPage() {
  return <DeviceAdapterWorkbench initialPacks={await getDeviceAdapterPacks()} />;
}
