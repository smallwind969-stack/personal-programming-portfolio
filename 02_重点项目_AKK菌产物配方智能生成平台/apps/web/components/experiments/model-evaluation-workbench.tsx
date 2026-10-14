"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import {
  createModelEvaluationReport,
  reviewModelEvaluationReport,
} from "@/lib/api";
import type { ModelEvaluationReport } from "@/lib/schemas";

export function ModelEvaluationWorkbench({
  experimentId,
  initialReport,
  hasPromotedModel,
}: {
  experimentId: string;
  initialReport: ModelEvaluationReport | null;
  hasPromotedModel: boolean;
}) {
  const router = useRouter();
  const [report, setReport] = useState(initialReport);
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(
    initialReport
      ? "已恢复最近一次模型可靠性报告。"
      : hasPromotedModel
        ? "已检测到晋升模型，可以开始独立可靠性评估。"
        : "请先在数学建模环节晋升一个真实模型。",
  );

  async function create() {
    setBusy(true);
    setMessage("正在验证模型产物，并计算残差、漂移、覆盖率和仿真准入评分……");
    try {
      const created = await createModelEvaluationReport(experimentId);
      setReport(created);
      setMessage(
        created.recommendedAdmission
          ? "自动可靠性检查通过，等待研发人员确认适用边界。"
          : "自动检查未达到仿真准入要求，请查看阻断原因。",
      );
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "模型可靠性评估失败。");
    } finally {
      setBusy(false);
    }
  }

  async function review(decision: "approved" | "rejected") {
    if (!report || reason.trim().length < 2) return;
    setBusy(true);
    try {
      const reviewed = await reviewModelEvaluationReport(
        experimentId, report.reportId, decision, operator, reason,
      );
      setReport(reviewed);
      setMessage(
        decision === "approved"
          ? "可靠性报告已签署，仿真入口和实验总览已同步解锁。"
          : "该模型已拒绝进入仿真，请补充数据或重新训练。",
      );
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "可靠性报告评审失败。");
    } finally {
      setBusy(false);
    }
  }

  const statusLabel =
    report?.status === "confirmed"
      ? "已确认，可进入仿真"
      : report?.status === "rejected"
        ? "已拒绝"
        : report
          ? "等待人工评审"
          : "尚未评估";

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>模型评估与可靠性门禁</CardTitle>
          <p className="mt-1 max-w-3xl text-xs leading-6 text-muted-foreground">
            独立检查晋升模型的残差、交叉验证稳定性、分布漂移、训练范围覆盖和预测区间，并决定它是否足以支撑仿真。
          </p>
        </div>
        <Badge tone={report?.status === "confirmed" ? "success" : "warning"}>
          {statusLabel}
        </Badge>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={busy || !hasPromotedModel} onClick={create}>
          {busy ? "评估中……" : report ? "重新评估当前模型" : "开始可靠性评估"}
        </Button>
        <span className="text-xs text-muted-foreground">{message}</span>
      </div>

      {report ? (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Metric label="可靠性评分" value={`${(report.reliabilityScore * 100).toFixed(1)}%`} />
            <Metric label="留出集 R²" value={metric(report.performanceMetrics.r2)} />
            <Metric label="留出集 MAE" value={metric(report.performanceMetrics.mae)} />
            <Metric label="区间半宽" value={`±${metric(report.predictionInterval.margin)}`} />
            <Metric label="产物完整性" value={report.artifactVerified ? "通过" : "失败"} />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-900">残差诊断</h3>
              <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-slate-600">
                <Line label="平均残差" value={metric(report.residualDiagnostics.meanResidual)} />
                <Line label="残差标准差" value={metric(report.residualDiagnostics.residualStd)} />
                <Line label="最大绝对残差" value={metric(report.residualDiagnostics.maxAbsoluteResidual)} />
                <Line label="一阶自相关" value={metric(report.residualDiagnostics.lag1Autocorrelation)} />
              </div>
              <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                经验 95% 预测区间：预测值 ± {metric(report.predictionInterval.margin)}；
                样本 {report.predictionInterval.sampleCount} 行，经验覆盖率
                {(report.predictionInterval.empiricalCoverage * 100).toFixed(1)}%。
                <div className="mt-1 text-amber-700">{report.predictionInterval.limitation}</div>
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-900">可靠性评分构成</h3>
              <div className="mt-3 space-y-3">
                {Object.entries(report.scoreBreakdown).map(([name, value]) => (
                  <div key={name}>
                    <div className="flex justify-between text-xs text-slate-600">
                      <span>{scoreLabel(name)}</span>
                      <span>{(value * 100).toFixed(1)}%</span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded bg-slate-100">
                      <div className="h-full bg-[#397b5d]" style={{ width: `${value * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-3 py-2">特征</th>
                  <th className="px-3 py-2">标准化均值漂移</th>
                  <th className="px-3 py-2">训练范围覆盖</th>
                  <th className="px-3 py-2">风险</th>
                  <th className="px-3 py-2">模型效应</th>
                </tr>
              </thead>
              <tbody>
                {report.driftDiagnostics.map((drift) => {
                  const effect = report.featureEffects.find((item) => item.feature === drift.feature);
                  return (
                    <tr className="border-t border-slate-100" key={drift.feature}>
                      <td className="px-3 py-3 font-medium">{drift.feature}</td>
                      <td className="px-3 py-3">{drift.standardizedMeanShift.toFixed(3)}</td>
                      <td className="px-3 py-3">{(drift.holdoutRangeCoverage * 100).toFixed(1)}%</td>
                      <td className={`px-3 py-3 ${
                        drift.severity === "high"
                          ? "text-red-700"
                          : drift.severity === "medium"
                            ? "text-amber-700"
                            : "text-emerald-700"
                      }`}>
                        {drift.severity === "high" ? "高" : drift.severity === "medium" ? "中" : "低"}
                      </td>
                      <td className="px-3 py-3">
                        {effect
                          ? `${(effect.normalizedImportance * 100).toFixed(1)}% · ${effect.effect.toFixed(4)}`
                          : "-"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className={`mt-4 rounded-xl border p-4 ${
            report.recommendedAdmission
              ? "border-emerald-200 bg-emerald-50"
              : "border-red-200 bg-red-50"
          }`}>
            <div className="text-sm font-semibold">
              {report.recommendedAdmission ? "系统建议：允许进入仿真评审" : "系统建议：暂不允许进入仿真"}
            </div>
            <div className="mt-2 space-y-1 text-xs">
              {report.admissionReasons.map((item) => <div key={item}>· {item}</div>)}
            </div>
          </div>

          <div className="mt-4 rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-6 text-slate-600">
            <div>报告：{report.reportId} · 版本 {report.reportVersion}</div>
            <div>模型：{report.modelVersion} · {report.modelType}</div>
            <div>模型产物：{report.artifactFingerprint}</div>
            <div>输入指纹：{report.inputFingerprint}</div>
          </div>

          {report.status === "needsReview" ? (
            <div className="mt-4 grid gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 md:grid-cols-[180px_1fr_auto_auto]">
              <input
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
                onChange={(event) => setOperator(event.target.value)}
                value={operator}
              />
              <input
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
                onChange={(event) => setReason(event.target.value)}
                placeholder="填写残差、漂移和适用边界的人工判断依据"
                value={reason}
              />
              <Button
                disabled={busy || !report.recommendedAdmission || reason.trim().length < 2}
                onClick={() => review("approved")}
              >
                确认并开放仿真
              </Button>
              <button
                className="rounded-md border border-red-300 px-4 py-2 text-sm text-red-700 disabled:opacity-50"
                disabled={busy || reason.trim().length < 2}
                onClick={() => review("rejected")}
                type="button"
              >
                拒绝该模型
              </button>
            </div>
          ) : null}
        </>
      ) : null}
    </Card>
  );
}

function metric(value: number | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(4) : "--";
}

function scoreLabel(name: string) {
  return {
    predictivePerformance: "预测性能",
    crossValidationStability: "交叉验证稳定性",
    distributionStability: "分布稳定性",
    rangeCoverage: "训练范围覆盖",
    residualBias: "残差偏差",
    dataAdequacy: "样本充分度",
  }[name] ?? name;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-slate-400">{label}</div>
      <div className="mt-1 font-mono text-slate-800">{value}</div>
    </div>
  );
}
