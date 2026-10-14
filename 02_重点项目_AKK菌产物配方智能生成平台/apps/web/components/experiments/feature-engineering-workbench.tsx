"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import {
  confirmFeatureEngineeringRun,
  createFeatureEngineeringRun,
} from "@/lib/api";
import type {
  ExperimentDatasetSnapshot,
  FeatureEngineeringRun,
} from "@/lib/schemas";

export function FeatureEngineeringWorkbench({
  experimentId,
  snapshot,
  initialRun,
}: {
  experimentId: string;
  snapshot: ExperimentDatasetSnapshot;
  initialRun: FeatureEngineeringRun | null;
}) {
  const router = useRouter();
  const numericFields = useMemo(
    () =>
      Array.from(
        new Set(
          snapshot.alignedRows.flatMap((row) =>
            Object.entries(row)
              .filter(([key, value]) => key !== "timestamp" && typeof value === "number")
              .map(([key]) => key),
          ),
        ),
      ).sort(),
    [snapshot.alignedRows],
  );
  const [run, setRun] = useState(initialRun);
  const [target, setTarget] = useState(initialRun?.targetField ?? "");
  const [sources, setSources] = useState<string[]>(initialRun?.config.sourceFields ?? []);
  const [lagSteps, setLagSteps] = useState(
    initialRun?.config.lagSteps.join(",") ?? "1",
  );
  const [rollingWindows, setRollingWindows] = useState(
    initialRun?.config.rollingWindows.join(",") ?? "3",
  );
  const [includeRaw, setIncludeRaw] = useState(initialRun?.config.includeRaw ?? true);
  const [includeDiff, setIncludeDiff] = useState(initialRun?.config.includeDiff ?? true);
  const [selected, setSelected] = useState<string[]>(
    initialRun?.selectedFeatureNames.length
      ? initialRun.selectedFeatureNames
      : initialRun?.candidateFeatureNames ?? [],
  );
  const [operator, setOperator] = useState("研发负责人");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(
    initialRun ? "已恢复最近一次特征集版本。" : "请选择目标变量和输入字段。",
  );

  function parsePositiveList(value: string, minimum: number) {
    if (!value.trim()) return [];
    const result = value
      .split(",")
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isInteger(item) && item >= minimum);
    return Array.from(new Set(result));
  }

  async function create() {
    if (!target || sources.length === 0) return;
    setBusy(true);
    setMessage("正在生成历史特征、计算公式并执行数据泄漏审计……");
    try {
      const created = await createFeatureEngineeringRun(experimentId, {
        targetField: target,
        sourceFields: sources,
        includeRaw,
        includeDiff,
        lagSteps: parsePositiveList(lagSteps, 1),
        rollingWindows: parsePositiveList(rollingWindows, 2),
      });
      setRun(created);
      const blocked = new Set(
        created.leakageIssues
          .filter((item) => item.severity === "blocking")
          .map((item) => item.featureName),
      );
      setSelected(
        created.candidateFeatureNames.filter((name) => !blocked.has(name)),
      );
      setMessage("候选特征集已生成，请核对公式、缺失率和风险后人工确认。");
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "特征工程运行失败。");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!run || selected.length === 0 || reason.trim().length < 2) return;
    setBusy(true);
    try {
      const confirmed = await confirmFeatureEngineeringRun(
        experimentId,
        run.featureSetId,
        { operator, reason, selectedFeatureNames: selected },
      );
      setRun(confirmed);
      setMessage("特征集已由人工确认，后续建模只能使用该锁定版本。");
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "特征集确认失败。");
    } finally {
      setBusy(false);
    }
  }

  function toggleSource(field: string) {
    setSources((current) =>
      current.includes(field)
        ? current.filter((item) => item !== field)
        : [...current, field],
    );
  }

  function toggleSelected(field: string) {
    setSelected((current) =>
      current.includes(field)
        ? current.filter((item) => item !== field)
        : [...current, field],
    );
  }

  const blockingNames = new Set(
    run?.leakageIssues
      .filter((item) => item.severity === "blocking")
      .map((item) => item.featureName) ?? [],
  );

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>特征工程与泄漏检查</CardTitle>
          <p className="mt-1 max-w-3xl text-xs leading-6 text-muted-foreground">
            由研发人员确定预测目标；系统只使用当前与历史数据生成可复现特征，并在建模前检查目标泄漏和未来信息泄漏。
          </p>
        </div>
        <Badge tone={run?.status === "confirmed" ? "success" : "warning"}>
          {run?.status === "confirmed"
            ? "特征集已确认"
            : run?.status === "needsReview"
              ? "等待人工确认"
              : run?.status === "superseded"
                ? "已被新版本替代"
                : "尚未运行"}
        </Badge>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <label className="text-xs text-slate-600">
          预测目标变量
          <select
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            onChange={(event) => {
              setTarget(event.target.value);
              setSources((current) => current.filter((field) => field !== event.target.value));
            }}
            value={target}
          >
            <option value="">请选择需要预测的实验结果</option>
            {numericFields.map((field) => (
              <option key={field} value={field}>{field}</option>
            ))}
          </select>
        </label>

        <div className="text-xs text-slate-600">
          可作为模型输入的基础字段
          <div className="mt-1 flex min-h-10 flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-2">
            {numericFields.filter((field) => field !== target).map((field) => (
              <label className="flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1" key={field}>
                <input
                  checked={sources.includes(field)}
                  onChange={() => toggleSource(field)}
                  type="checkbox"
                />
                {field}
              </label>
            ))}
          </div>
        </div>

        <label className="text-xs text-slate-600">
          滞后步数（用英文逗号分隔）
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            onChange={(event) => setLagSteps(event.target.value)}
            value={lagSteps}
          />
        </label>
        <label className="text-xs text-slate-600">
          滚动窗口（至少为 2）
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            onChange={(event) => setRollingWindows(event.target.value)}
            value={rollingWindows}
          />
        </label>
      </div>

      <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-600">
        <label className="flex items-center gap-2">
          <input checked={includeRaw} onChange={(event) => setIncludeRaw(event.target.checked)} type="checkbox" />
          保留原始值
        </label>
        <label className="flex items-center gap-2">
          <input checked={includeDiff} onChange={(event) => setIncludeDiff(event.target.checked)} type="checkbox" />
          生成一阶变化量
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={busy || !target || sources.length === 0} onClick={create}>
          {busy ? "计算中……" : run ? "生成新特征集版本" : "开始特征工程"}
        </Button>
        <span className="text-xs text-muted-foreground">{message}</span>
      </div>

      {run ? (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <MiniMetric label="原始行数" value={run.rowCount.toString()} />
            <MiniMetric label="候选特征" value={run.candidateFeatureNames.length.toString()} />
            <MiniMetric label="当前可用行" value={run.usableRowCount.toString()} />
          </div>

          {run.leakageIssues.length ? (
            <div className="mt-4 space-y-2">
              {run.leakageIssues.map((issue, index) => (
                <div
                  className={`rounded-lg border px-3 py-2 text-xs ${
                    issue.severity === "blocking"
                      ? "border-red-200 bg-red-50 text-red-800"
                      : "border-amber-200 bg-amber-50 text-amber-800"
                  }`}
                  key={`${issue.code}-${index}`}
                >
                  {issue.severity === "blocking" ? "阻断" : "提示"} · {issue.message}
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
              泄漏审计通过：未发现目标字段直连或未来数据参与当前特征。
            </div>
          )}

          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[820px] text-left text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-3 py-2">启用</th>
                  <th className="px-3 py-2">特征名称</th>
                  <th className="px-3 py-2">类型</th>
                  <th className="px-3 py-2">计算公式</th>
                  <th className="px-3 py-2">有效行</th>
                  <th className="px-3 py-2">缺失率</th>
                </tr>
              </thead>
              <tbody>
                {run.definitions.map((definition) => (
                  <tr className="border-t border-slate-100" key={definition.name}>
                    <td className="px-3 py-2">
                      <input
                        checked={selected.includes(definition.name)}
                        disabled={run.status === "confirmed" || blockingNames.has(definition.name)}
                        onChange={() => toggleSelected(definition.name)}
                        type="checkbox"
                      />
                    </td>
                    <td className="px-3 py-2 font-medium">{definition.name}</td>
                    <td className="px-3 py-2">{definition.kind}</td>
                    <td className="px-3 py-2 font-mono">{definition.formula}</td>
                    <td className="px-3 py-2">{definition.validCount}</td>
                    <td className="px-3 py-2">{(definition.missingRate * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-6 text-slate-600">
            <div>特征集：{run.featureSetId} · 版本 {run.runVersion}</div>
            <div>数据快照：{run.snapshotId}</div>
            <div>输入指纹：{run.inputFingerprint}</div>
            <div>输出哈希：{run.outputHash}</div>
          </div>

          {run.status === "needsReview" ? (
            <div className="mt-4 grid gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 md:grid-cols-[180px_1fr_auto]">
              <input
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
                onChange={(event) => setOperator(event.target.value)}
                value={operator}
              />
              <input
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
                onChange={(event) => setReason(event.target.value)}
                placeholder="填写目标与特征选择依据（至少 2 个字）"
                value={reason}
              />
              <Button
                disabled={busy || selected.length === 0 || reason.trim().length < 2}
                onClick={confirm}
              >
                确认特征集并开放建模
              </Button>
            </div>
          ) : null}
        </>
      ) : numericFields.length < 2 ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          当前快照不足两个数值字段，无法区分预测目标和模型输入。请补充包含工艺条件与实验结果的数据。
        </div>
      ) : null}
    </Card>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-950">{value}</div>
    </div>
  );
}
