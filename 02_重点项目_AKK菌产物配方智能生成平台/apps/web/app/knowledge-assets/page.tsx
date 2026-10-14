import { EnterpriseKnowledgeCenter } from "@/components/knowledge/enterprise-knowledge-center";
import { getEnterpriseKnowledge } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function EnterpriseKnowledgePage() {
  const entries = await getEnterpriseKnowledge();
  return <EnterpriseKnowledgeCenter entries={entries}/>;
}
