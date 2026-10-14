import Link from "next/link";
import type { ReactNode } from "react";

import type {
  ExperimentStageName,
  ExperimentStageSummary,
} from "@/lib/schemas";

export function ExperimentStageAccess({
  experimentId,
  stage,
  children,
}: {
  experimentId: string;
  stage: ExperimentStageSummary;
  children: ReactNode;
}) {
  if (stage.canEnter) return <>{children}</>;

  return (
    <section className="rounded-2xl border border-[#dce4de] bg-white p-7 shadow-[0_20px_60px_rgba(28,55,43,0.06)]">
      <div className="text-xs font-medium text-amber-700">阶段准入未通过</div>
      <h1 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-slate-950">
        {stage.label}尚未开放
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">{stage.detail}</p>
      <Link
        className="focus-ring mt-6 inline-flex rounded text-sm font-medium text-[#174333] hover:underline"
        href={`/experiments/${encodeURIComponent(experimentId)}`}
      >
        返回实验总览 <span aria-hidden className="ml-2">→</span>
      </Link>
    </section>
  );
}

export function requireExperimentStage(
  stages: ExperimentStageSummary[],
  stageName: ExperimentStageName,
): ExperimentStageSummary {
  const stage = stages.find((item) => item.stage === stageName);
  if (!stage) throw new Error(`Missing experiment stage: ${stageName}`);
  return stage;
}
