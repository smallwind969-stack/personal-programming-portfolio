"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createDemoModelAdmission } from "@/lib/api";
import type { DemoModelAdmission, ResearchCampaign } from "@/lib/schemas";

export function DemoModelAdmissionPanel({ experimentId, campaigns, initialAdmission }: {
  experimentId: string;
  campaigns: ResearchCampaign[];
  initialAdmission: DemoModelAdmission | null;
}) {
  const router = useRouter();
  const [admission, setAdmission] = useState(initialAdmission);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const campaign = [...campaigns].reverse().find((item) =>
    item.trials.some((candidate) => candidate.status === "keep" && Boolean(candidate.modelCard)),
  );
  const trial = campaign
    ? [...campaign.trials].reverse().find((item) => item.status === "keep" && Boolean(item.modelCard)) ?? null
    : null;

  async function admit() {
    if (!campaign || !trial) return;
    setBusy(true);
    setMessage("正在校验训练产物、数据集指纹和最佳轮次……");
    try {
      const created = await createDemoModelAdmission(
        experimentId, campaign.campaignId, trial.trialId,
        "演示负责人", "允许该训练轮次进入隔离仿真体验",
      );
      setAdmission(created);
      setMessage("演示模型血缘已锁定，仿真入口已经开放。");
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "演示模型准入失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold tracking-[0.12em] text-amber-800">示例实验 · 隔离模型通道</div>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">仿真演示准入</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">引用实际训练轮次和数据血缘，但不写入企业正式模型注册表。该通道只能用于体验仿真与工艺优化。</p>
        </div>
        <span className={`rounded-md px-3 py-1.5 text-xs ${admission ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
          {admission ? "已准入" : trial ? "等待人工准入" : "等待建模轮次"}
        </span>
      </div>
      {admission ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Info label="演示模型版本" value={admission.demoModelVersion} />
          <Info label="目标字段" value={admission.targetField} />
          <Info label="演示准入评分" value={`${(admission.reliabilityScore * 100).toFixed(1)}%`} />
        </div>
      ) : trial && campaign ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-white p-4 text-sm text-slate-700">
          <div>候选轮次：<span className="font-mono">{trial.trialId}</span></div>
          <div className="mt-1">模型：{trial.modelType ?? "待识别"} · R² {trial.metrics.r2?.toFixed(3) ?? "--"}</div>
          <button className="mt-4 rounded-lg bg-[#174333] px-5 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy} onClick={admit} type="button">
            {busy ? "校验中……" : "人工确认进入演示仿真"}
          </button>
        </div>
      ) : (
        <p className="mt-4 text-sm text-amber-900">完成特征确认并运行至少一个具有模型卡的保留轮次后，才可进行演示准入。</p>
      )}
      <ul className="mt-4 grid gap-1 text-xs leading-5 text-amber-900 sm:grid-cols-2">
        {(admission?.restrictions ?? ["不得晋升为企业正式模型", "不得登记为真实实验测量", "不得发送设备控制指令", "仅用于平台功能演示和研发流程教学"]).map((item) => <li key={item}>— {item}</li>)}
      </ul>
      {admission ? <p className="mt-3 text-xs leading-5 text-slate-500">{admission.limitations.join("；")}</p> : null}
      {message ? <p aria-live="polite" className="mt-3 text-xs text-slate-600">{message}</p> : null}
    </section>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-white p-3"><div className="text-xs text-slate-500">{label}</div><div className="mt-1 break-all font-mono text-sm font-semibold text-slate-900">{value}</div></div>;
}
