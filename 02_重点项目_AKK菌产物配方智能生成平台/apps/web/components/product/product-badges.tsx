import { Badge } from "@/components/ui/badge";
import { formatRisk } from "@/lib/display";
import { AkkProduct } from "@/lib/schemas";

export const riskTone = {
  low: "success",
  medium: "warning",
  high: "danger",
} as const;

export function RiskBadge({ riskLevel }: { riskLevel: AkkProduct["riskLevel"] }) {
  return <Badge tone={riskTone[riskLevel]}>{formatRisk(riskLevel)}</Badge>;
}

export function EvidenceBadge({ evidenceLevel }: { evidenceLevel: string }) {
  return <Badge>证据等级 {evidenceLevel}</Badge>;
}
