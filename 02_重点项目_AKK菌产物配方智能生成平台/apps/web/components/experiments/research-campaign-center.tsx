"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createResearchCampaign,
  enqueueNextResearchIteration,
  enqueueResearchTrial,
  getAgentCommand,
  getResearchCampaign,
  promoteResearchTrial,
} from "@/lib/api";
import type { AgentCommandTask, ResearchCampaign } from "@/lib/schemas";

export function ResearchCampaignCenter({
  experimentId,
  initialCampaigns,
  datasetSnapshotId,
  baselineMetrics,
}: {
  experimentId: string;
  initialCampaigns: ResearchCampaign[];
  datasetSnapshotId: string;
  baselineMetrics: { mae: number; rmse: number; r2: number };
}) {
  const [campaign, setCampaign] = useState<ResearchCampaign | null>(
    initialCampaigns.at(-1) ?? null,
  );
  const [task, setTask] = useState<AgentCommandTask | null>(null);
  const [algorithm, setAlgorithm] = useState("ridge");
  const [parameterKey, setParameterKey] = useState("alpha");
  const [parameterValue, setParameterValue] = useState("1.0");
  const [hypothesis, setHypothesis] = useState("比较线性基线与当前最佳模型的时间外推能力");
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("候选模型通过固定评测门槛，模型卡和适用边界已核对");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!task || ["completed", "deadLetter", "cancelled"].includes(task.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getAgentCommand(task.taskId);
        setTask(next);
        if (next.status === "completed" && campaign) {
          setCampaign(await getResearchCampaign(experimentId, campaign.campaignId));
          setBusy(false);
        }
        if (["deadLetter", "cancelled"].includes(next.status)) {
          setError(next.errorMessage ?? "候选训练任务未完成");
          setBusy(false);
        }
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "无法读取训练任务状态");
        setBusy(false);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [task, campaign, experimentId]);

  const best = useMemo(
    () => campaign?.trials.find((trial) => trial.trialId === campaign.bestTrialId),
    [campaign],
  );

  async function createBaseline() {
    setBusy(true);
    setError(null);
    try {
      setCampaign(await createResearchCampaign(
        experimentId, datasetSnapshotId, baselineMetrics,
      ));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法建立固定评测基线");
    } finally {
      setBusy(false);
    }
  }

  async function runManualTrial() {
    if (!campaign) return;
    const numeric = Number(parameterValue);
    if (!Number.isFinite(numeric)) {
      setError("超参数必须是有效数字");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setTask(await enqueueResearchTrial(
        experimentId, campaign.campaignId, hypothesis,
        { algorithm, [parameterKey]: numeric },
      ));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "候选训练任务入队失败");
      setBusy(false);
    }
  }

  async function runAutomaticIteration() {
    if (!campaign) return;
    setBusy(true);
    setError(null);
    try {
      setTask(await enqueueNextResearchIteration(experimentId, campaign.campaignId));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "自动候选任务入队失败");
      setBusy(false);
    }
  }

  async function approve() {
    if (!campaign || !best) return;
    setBusy(true);
    setError(null);
    try {
      setCampaign(await promoteResearchTrial(
        experimentId, campaign.campaignId, best.trialId, operator, reason,
      ));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "模型晋升失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-medium text-[#2f7054]">数学建模与候选搜索</div>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">
            固定评测协议 · 候选模型比较 · 人工晋升
          </h2>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
            真实训练使用时间顺序留出集和扩展窗口交叉验证；演示模式会明确标注，不会伪装成已训练模型。
          </p>
        </div>
        {campaign ? (
          <div className="text-right">
            <span className={`rounded px-2 py-1 font-mono text-[10px] ${
              campaign.mode === "real_runner"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-amber-50 text-amber-700"
            }`}>
              {campaign.mode === "real_runner" ? "真实 sklearn 训练" : "演示评测"} · {campaign.status}
            </span>
            <div className="mt-2 text-[10px] text-slate-400">{campaign.runnerKey}</div>
          </div>
        ) : null}
      </div>

      {campaign?.runnerFallbackReason ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          真实训练器不可用，已切换演示评测：{campaign.runnerFallbackReason}
        </div>
      ) : null}
      {error ? (
        <div className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</div>
      ) : null}

      {!campaign ? (
        <button
          className="mt-5 rounded-lg bg-[#174333] px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          disabled={busy || !datasetSnapshotId}
          onClick={createBaseline}
          type="button"
        >
          {busy ? "正在训练基线……" : "建立固定评测基线"}
        </button>
      ) : (
        <>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <Stat label="单次预算" value={`${campaign.fixedBudgetSeconds}s`} />
            <Stat label="主指标" value={`${campaign.primaryMetric} ↑`} />
            <Stat label="最佳 R²" value={formatMetric(best?.metrics.r2)} />
            <Stat label="候选次数" value={String(Math.max(0, campaign.trials.length - 1))} />
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="border-y border-slate-200 bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-3 py-2">序号</th>
                  <th className="px-3 py-2">算法与假设</th>
                  <th className="px-3 py-2">R²</th>
                  <th className="px-3 py-2">MAE</th>
                  <th className="px-3 py-2">相对基线</th>
                  <th className="px-3 py-2">结论</th>
                </tr>
              </thead>
              <tbody>
                {campaign.trials.map((trial) => (
                  <tr className="border-b border-slate-100 align-top" key={trial.trialId}>
                    <td className="px-3 py-3 font-mono">{trial.sequence}</td>
                    <td className="px-3 py-3">
                      <div className="font-medium text-slate-700">
                        {trial.modelCard?.algorithm ?? trial.modelType ?? "固定基线"}
                      </div>
                      <div className="mt-1 text-slate-500">{trial.hypothesis}</div>
                      <div className="mt-1 font-mono text-[10px] text-slate-400">
                        {JSON.stringify(trial.parameterPatch)}
                      </div>
                    </td>
                    <td className="px-3 py-3 font-mono">{formatMetric(trial.metrics.r2)}</td>
                    <td className="px-3 py-3 font-mono">{formatMetric(trial.metrics.mae)}</td>
                    <td className="px-3 py-3 font-mono">
                      {trial.deltaFromBaseline >= 0 ? "+" : ""}{trial.deltaFromBaseline.toFixed(3)}
                    </td>
                    <td className="px-3 py-3">
                      <span className={`rounded px-2 py-1 ${
                        trial.status === "keep"
                          ? "bg-emerald-50 text-emerald-700"
                          : trial.status === "crash"
                            ? "bg-rose-50 text-rose-700"
                            : "bg-slate-100 text-slate-600"
                      }`}>
                        {trial.status === "keep" ? "保留" : trial.status === "crash" ? "失败" : "淘汰"}
                      </span>
                      {trial.errorMessage ? (
                        <div className="mt-2 max-w-xs text-[10px] text-rose-600">{trial.errorMessage}</div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {best?.modelCard ? <ModelCardDetails card={best.modelCard} /> : null}

          {campaign.status !== "completed" ? (
            <>
              <div className="mt-5 flex justify-end border-t border-slate-100 pt-5">
                <button
                  className="rounded-lg bg-[#174333] px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
                  disabled={busy}
                  onClick={runAutomaticIteration}
                  type="button"
                >
                  自动生成下一候选
                </button>
              </div>
              <div className="mt-3 grid gap-3 lg:grid-cols-[10rem_1fr_10rem_8rem_auto]">
                <select
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  onChange={(event) => setAlgorithm(event.target.value)}
                  value={algorithm}
                >
                  <option value="ridge">Ridge</option>
                  <option value="random_forest">随机森林</option>
                  <option value="gradient_boosting">梯度提升</option>
                </select>
                <input
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  onChange={(event) => setHypothesis(event.target.value)}
                  value={hypothesis}
                />
                <select
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  onChange={(event) => setParameterKey(event.target.value)}
                  value={parameterKey}
                >
                  <option value="alpha">正则强度</option>
                  <option value="nEstimators">树数量</option>
                  <option value="learningRate">学习率</option>
                  <option value="maxDepth">树深度</option>
                  <option value="minSamplesLeaf">叶节点样本数</option>
                  <option value="subsample">子采样比例</option>
                </select>
                <input
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  onChange={(event) => setParameterValue(event.target.value)}
                  value={parameterValue}
                />
                <button
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-40"
                  disabled={busy || hypothesis.trim().length < 2}
                  onClick={runManualTrial}
                  type="button"
                >
                  提交人工候选
                </button>
              </div>
            </>
          ) : null}

          {task ? (
            <div className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-700">
              后台任务 {task.taskId} · {task.status} · 尝试 {task.attempts}/{task.maxAttempts}
            </div>
          ) : null}

          {campaign.status === "needsReview" && best ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <div className="text-sm font-semibold text-amber-900">
                当前最佳候选达到人工评审阶段
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <input
                  className="rounded border border-amber-200 bg-white px-3 py-2 text-sm"
                  onChange={(event) => setOperator(event.target.value)}
                  value={operator}
                />
                <input
                  className="rounded border border-amber-200 bg-white px-3 py-2 text-sm"
                  onChange={(event) => setReason(event.target.value)}
                  value={reason}
                />
              </div>
              <button
                className="mt-3 rounded bg-amber-800 px-4 py-2 text-sm text-white disabled:opacity-40"
                disabled={busy || !operator.trim() || !reason.trim()}
                onClick={approve}
                type="button"
              >
                人工确认并晋升模型版本
              </button>
            </div>
          ) : null}

          {campaign.promotion ? (
            <div className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
              已由 {campaign.promotion.operator} 签署 · {campaign.promotion.promotedModelVersion} · {campaign.promotion.reason}
            </div>
          ) : null}
        </>
      )}

      <div className="mt-4 text-[10px] text-slate-400">
        评测协议：{campaign?.evaluationHarnessHash ?? "等待创建"} · 研发实验建议
      </div>
    </section>
  );
}

function ModelCardDetails({
  card,
}: {
  card: NonNullable<ResearchCampaign["trials"][number]["modelCard"]>;
}) {
  return (
    <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <summary className="cursor-pointer text-sm font-semibold text-slate-800">
        查看当前最佳模型卡
      </summary>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <Stat label="算法" value={card.algorithm} />
        <Stat label="训练行" value={String(card.trainRows)} />
        <Stat label="留出行" value={String(card.holdoutRows)} />
        <Stat label="交叉验证折数" value={String(card.crossValidationFolds.length)} />
      </div>
      <div className="mt-4 grid gap-4 text-xs text-slate-600 md:grid-cols-2">
        <div className="rounded-lg bg-white p-3">
          <div className="font-medium text-slate-800">固定验证协议</div>
          <div className="mt-2">按时间顺序切分：是</div>
          <div>随机打乱：{card.shuffle ? "是" : "否"}</div>
          <div>CV 均值：R² {formatMetric(card.crossValidationMean.r2)} · MAE {formatMetric(card.crossValidationMean.mae)}</div>
          <div>CV 标准差：R² {formatMetric(card.crossValidationStd.r2)} · MAE {formatMetric(card.crossValidationStd.mae)}</div>
        </div>
        <div className="rounded-lg bg-white p-3">
          <div className="font-medium text-slate-800">版本与血缘</div>
          <div className="mt-2">模型类型：{card.modelType}</div>
          <div>sklearn：{card.sklearnVersion}</div>
          <div>目标字段：{card.targetField}</div>
          <div className="truncate" title={card.datasetFingerprint}>数据指纹：{card.datasetFingerprint}</div>
        </div>
      </div>
      {card.holdoutDiagnostics?.r2Stable === false ? (
        <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
          <div className="font-semibold">R² 当前不稳定，不能单独解释模型质量</div>
          <div className="mt-1">留出集与训练集的目标标准差比为 {(card.holdoutDiagnostics.varianceRatio * 100).toFixed(1)}%，目标在留出阶段接近平台期。归一化 MAE 为 {(card.holdoutDiagnostics.normalizedMaeByTrainRange * 100).toFixed(2)}%。建议增加多批次、扰动工况和平台期前后的独立验证数据。</div>
        </div>
      ) : null}
      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
        <div className="font-medium">已知限制</div>
        {card.limitations.map((item) => <div className="mt-1" key={item}>· {item}</div>)}
      </div>
    </details>
  );
}

function formatMetric(value: number | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(3) : "--";
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[#f6f8f6] p-3">
      <div className="text-[10px] text-slate-400">{label}</div>
      <div className="mt-1 font-mono text-sm font-semibold text-slate-800">{value}</div>
    </div>
  );
}
