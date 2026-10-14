import { HumanActionWorkbench } from "@/components/human-actions/human-action-workbench";
import { getHumanActionCenter } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HumanActionsPage() {
  return <HumanActionWorkbench initialCenter={await getHumanActionCenter()} />;
}
