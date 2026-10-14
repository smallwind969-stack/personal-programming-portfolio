"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  confirmExperimentFieldMappings,
  getExperimentDataIntakeRuns,
  getExperimentFileAssets,
  uploadExperimentTextFile,
  verifyExperimentFileAsset,
} from "@/lib/api";
import type { DataCollectionLocalizationRun, ExperimentFileAsset, ExperimentWorkspaceOverview } from "@/lib/schemas";
import { buildExperimentFilePayload, experimentFileAccept, experimentParseStatusLabel } from "@/lib/experiment-file-payload";

type ReviewRow = { assetId: string; originalColumn: string; standardField: string; displayName: string; unit: string };

function reviewRows(latest: DataCollectionLocalizationRun | null): ReviewRow[] {
  return (latest?.transformations ?? []).map((item) => ({
    assetId: item.assetId, originalColumn: item.originalColumn,
    standardField: item.standardField ?? "", displayName: item.standardField ?? item.originalColumn,
    unit: item.targetUnit ?? item.sourceUnit ?? "",
  }));
}

export function FirstDataIntakeWorkbench({ overview, initialRun = null }: { overview: ExperimentWorkspaceOverview; initialRun?: DataCollectionLocalizationRun | null }) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [rawAssets, setRawAssets] = useState<ExperimentFileAsset[]>([]);
  const [sourceAssetId, setSourceAssetId] = useState("");
  const [sourceConversionNote, setSourceConversionNote] = useState("");
  const [run, setRun] = useState<DataCollectionLocalizationRun | null>(initialRun);
  const [rows, setRows] = useState<ReviewRow[]>(reviewRows(initialRun));
  const [busy, setBusy] = useState(false);
  const [integrity, setIntegrity] = useState<"unknown" | "verified" | "failed">("unknown");
  const [message, setMessage] = useState(initialRun ? "已恢复数据接入证据，请继续人工复核。" : "请选择设备导出的 CSV 或 TXT 文件。");

  function adoptRun(latest: DataCollectionLocalizationRun | null) {
    setRun(latest);
    setRows(reviewRows(latest));
  }

  useEffect(() => {
    getExperimentDataIntakeRuns(overview.experimentId)
      .then((runs) => {
        const latest = runs.at(-1) ?? null;
        adoptRun(latest);
        if (latest) {
          verifyExperimentFileAsset(overview.experimentId, latest.assetId)
            .then((result) => setIntegrity(result.verified ? "verified" : "failed"))
            .catch(() => setIntegrity("failed"));
        }
        if (latest) setMessage(latest.status === "confirmed" ? "最近一次数据接入已完成人工确认。" : "已恢复最近一次数据接入运行，请继续人工复核。");
      })
      .catch(() => undefined);
  }, [overview.experimentId]);

  useEffect(() => {
    getExperimentFileAssets(overview.experimentId)
      .then((assets) => setRawAssets(assets.filter((asset) => asset.parseStatus === "awaiting_adapter")))
      .catch(() => setRawAssets([]));
  }, [overview.experimentId]);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setMessage(selected ? `已选择：${selected.name}` : "请选择设备导出的 CSV 或 TXT 文件。");
  }

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true); setMessage("正在解析文件并生成字段、单位与来源证据…");
    try {
      const asset = await uploadExperimentTextFile(
        overview.experimentId,
        await buildExperimentFilePayload(file, sourceAssetId || undefined, sourceConversionNote),
      );
      if (asset.parseStatus !== "parsed") {
        setRawAssets((current) => current.some((item) => item.assetId === asset.assetId) ? current : [...current, asset]);
        setSourceAssetId("");
        setSourceConversionNote("");
        setMessage(`${experimentParseStatusLabel(asset.parseStatus)}。原始文件与 SHA-256 已留存，完成设备适配后再进入字段识别。`);
        setIntegrity("verified");
        return;
      }
      setSourceAssetId("");
      setSourceConversionNote("");
      const runs = await getExperimentDataIntakeRuns(overview.experimentId);
      const latest = runs.find((item) => item.runId === asset.intakeRunId) ?? runs.at(-1) ?? null;
      adoptRun(latest);
      if (latest) {
        const checked = await verifyExperimentFileAsset(overview.experimentId, latest.assetId);
        setIntegrity(checked.verified ? "verified" : "failed");
      }
      setMessage(`已解析 ${asset.rowCount} 行、${asset.columnNames.length} 个字段；请逐项复核后确认。`);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "数据接入运行失败。");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!run || rows.some((row) => !row.standardField.trim())) {
      setMessage("每个原始字段都必须填写标准字段，不能跳过未知字段。");
      return;
    }
    setBusy(true); setMessage("正在写入人工确认记录…");
    try {
      await confirmExperimentFieldMappings(overview.experimentId, {
        mappings: rows.map((row) => ({
          assetId: row.assetId, originalColumn: row.originalColumn,
          standardField: row.standardField.trim(), displayName: row.displayName.trim() || row.standardField.trim(),
          unit: row.unit.trim() || null, confirmedBy: "研发负责人", confirmed: true,
        })),
      });
      const latest = (await getExperimentDataIntakeRuns(overview.experimentId)).at(-1) ?? null;
      adoptRun(latest);
      setMessage("字段与单位已人工确认。现在可以进入数据分析并生成受控训练快照。");
      router.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "人工确认失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-6 rounded-2xl border border-[#cfdcd4] bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><div className="text-xs font-semibold tracking-[0.14em] text-[#397b5d]">数据收集与本地化</div><h2 className="mt-1 text-xl font-semibold text-slate-950">{run ? "复核数据接入证据" : "上传首批实验数据"}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">系统读取已锁定的设备适配规则，生成字段和单位转换证据，并停在人工确认节点。</p></div>
        <span className={`rounded-md px-3 py-1.5 text-xs ${run?.status === "confirmed" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{run?.status === "confirmed" ? "已人工确认" : run ? "待人工确认" : "等待文件"}</span>
      </div>
      <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={upload}>
        <input accept={experimentFileAccept} className="min-w-0 flex-1 rounded-lg border border-[#d8e1db] bg-white px-3 py-2 text-sm" disabled={busy} onChange={selectFile} type="file" />
        <button className="rounded-lg bg-[#174333] px-5 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={!file || busy} type="submit">{busy ? "处理中…" : "上传并开始识别"}</button>
      </form>

      {rawAssets.length > 0 ? <label className="mt-3 block text-xs text-slate-600">转换来源（可选）<select className="mt-1 block w-full rounded-lg border border-[#d8e1db] bg-white px-3 py-2 text-sm" disabled={busy} onChange={(event) => setSourceAssetId(event.target.value)} value={sourceAssetId}><option value="">不关联原始设备文件</option>{rawAssets.map((asset) => <option key={asset.assetId} value={asset.assetId}>{asset.originalName} · {asset.assetId}</option>)}</select><span className="mt-1 block leading-5 text-slate-500">上传由设备适配或解密工具转换得到的 CSV/XLSX 时，选择原始文件可固定完整来源链路。</span></label> : null}

      {sourceAssetId ? <label className="mt-3 block text-xs text-slate-600">转换说明（可选）<input className="mt-1 block w-full rounded-lg border border-[#d8e1db] bg-white px-3 py-2 text-sm" disabled={busy} maxLength={1000} onChange={(event) => setSourceConversionNote(event.target.value)} placeholder="例如：设备专用格式经解密工具 v1.2 转为 UTF-8 CSV" value={sourceConversionNote} /></label> : null}

      {run && <div className="mt-5">
        <div className="flex flex-wrap gap-3 text-xs text-slate-500"><span>转换项 {run.transformationCount}</span><span>适配命中 {run.matchedCount}</span><span>待确认 {run.pendingReviewCount}</span><span className={integrity === "verified" ? "text-emerald-700" : integrity === "failed" ? "text-rose-700" : ""}>原始文件完整性：{integrity === "verified" ? "SHA-256 已验证" : integrity === "failed" ? "验证失败" : "验证中"}</span>{run.adapterPack && <span>适配版本 {run.adapterPack.deviceType} v{run.adapterPack.packVersion}</span>}</div>
        <div className="mt-3 overflow-x-auto rounded-xl border border-[#e0e7e2]">
          <table className="w-full min-w-[820px] text-left text-xs">
            <thead className="bg-[#f3f6f3] text-slate-500"><tr><th className="px-3 py-3">原始字段</th><th className="px-3 py-3">适配结果</th><th className="px-3 py-3">标准字段（可修改）</th><th className="px-3 py-3">目标单位</th><th className="px-3 py-3">换算公式 / 证据</th></tr></thead>
            <tbody>{run.transformations.map((item, index) => <tr className="border-t border-[#e7ece8]" key={`${item.assetId}-${item.originalColumn}`}><td className="px-3 py-3 font-mono text-slate-800">{item.originalColumn}</td><td className="px-3 py-3"><span className={item.matched ? "text-emerald-700" : "text-amber-700"}>{item.matched ? item.simulationParameter ? `已识别 · ${item.simulationParameter}` : "已识别标准字段" : "未识别，必须人工填写"}</span></td><td className="px-3 py-2"><input className="w-full rounded border px-2 py-1.5" value={rows[index]?.standardField ?? ""} onChange={(event) => setRows(rows.map((row, position) => position === index ? { ...row, standardField: event.target.value } : row))} /></td><td className="px-3 py-2"><input className="w-24 rounded border px-2 py-1.5" value={rows[index]?.unit ?? ""} onChange={(event) => setRows(rows.map((row, position) => position === index ? { ...row, unit: event.target.value } : row))} /></td><td className="px-3 py-3 text-slate-500"><div className="font-mono">y = x × {item.scale} + {item.offset}</div><div className="mt-1">{item.evidence.join("；")}</div></td></tr>)}</tbody>
          </table>
        </div>
        {run.status !== "confirmed" && <button className="mt-4 rounded-lg border border-[#174333] px-5 py-2 text-sm font-medium text-[#174333] disabled:opacity-50" disabled={busy} onClick={confirm} type="button">人工确认全部字段与单位</button>}
      </div>}
      <div aria-live="polite" className="mt-4 rounded-lg bg-[#f4f7f4] px-3 py-2 text-xs leading-5 text-slate-600">{message}</div>
    </section>
  );
}
