"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  stageHref,
  statusLabels,
} from "@/components/experiments/experiment-status";
import type { ExperimentStageSummary } from "@/lib/schemas";

export function ExperimentWorkspaceNav({
  experimentId,
  name,
  stages,
}: {
  experimentId: string;
  name: string;
  stages: ExperimentStageSummary[];
}) {
  const pathname = usePathname();
  const overviewHref = `/experiments/${encodeURIComponent(experimentId)}`;

  return (
    <aside className="rounded-2xl border border-[#dce4de] bg-[#f5f8f5] p-4 lg:sticky lg:top-5 lg:h-[calc(100vh-6.5rem)]">
      <div className="text-xs text-slate-500">当前实验</div>
      <div className="mt-3 rounded-xl border border-[#dce4de] bg-white px-3 py-3">
        <div className="text-sm font-medium leading-5 text-slate-900">{name}</div>
        <div className="mt-1 font-mono text-[11px] text-slate-400">{experimentId}</div>
      </div>

      <nav aria-label="实验工作区" className="mt-4 space-y-1">
        <Link className={navClass(pathname === `${overviewHref}/agents`)} href={`${overviewHref}/agents`}>流程进程</Link>
        <Link className={navClass(pathname === overviewHref)} href={overviewHref}>实验总览</Link>
        <Link className={navClass(pathname === `${overviewHref}/innovation`)} href={`${overviewHref}/innovation`}>产品创新</Link>
        {stages.map((stage, index) => {
          const href = stageHref(experimentId, stage.stage);
          const content = (
            <>
              <span>{index + 1}. {stage.label}</span>
              <span className="text-[10px] opacity-70">{statusLabels[stage.status]}</span>
            </>
          );
          return stage.canEnter ? (
            <Link className={navClass(pathname === href)} href={href} key={stage.stage}>{content}</Link>
          ) : (
            <span aria-disabled="true" className="flex cursor-not-allowed items-center justify-between rounded-lg px-3 py-3 text-sm text-slate-400" key={stage.stage} title={stage.detail}>{content}</span>
          );
        })}
        <Link className={navClass(pathname === `${overviewHref}/reports`)} href={`${overviewHref}/reports`}>实验报告</Link>
      </nav>

      <Link className="focus-ring mt-8 inline-flex rounded px-2 py-1 text-xs text-slate-500 hover:text-[#174333] lg:absolute lg:bottom-5 lg:left-4" href="/">
        <span aria-hidden className="mr-2">←</span>返回实验归档
      </Link>
    </aside>
  );
}

function navClass(active: boolean): string {
  return [
    "focus-ring flex items-center justify-between rounded-lg px-3 py-3 text-sm transition",
    active ? "bg-[#e2eee7] font-medium text-[#174333]" : "text-slate-600 hover:bg-white hover:text-slate-900",
  ].join(" ");
}
