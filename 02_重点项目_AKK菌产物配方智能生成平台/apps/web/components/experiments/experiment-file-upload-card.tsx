"use client";

import { ChangeEvent, FormEvent, useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { getExperimentFileAssets, uploadExperimentTextFile } from "@/lib/api";
import { buildExperimentFilePayload, experimentFileAccept } from "@/lib/experiment-file-payload";
import type { ExperimentFileAsset } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

type UploadStatus =
  | { kind: "idle"; message: string }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export function ExperimentFileUploadCard({ experimentId }: { experimentId: string }) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [rawAssets, setRawAssets] = useState<ExperimentFileAsset[]>([]);
  const [sourceAssetId, setSourceAssetId] = useState("");
  const [sourceConversionNote, setSourceConversionNote] = useState("");
  const [status, setStatus] = useState<UploadStatus>({
    kind: "idle",
    message: "请选择设备导出的 CSV 或 TXT 文本文件。",
  });
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    getExperimentFileAssets(experimentId)
      .then((assets) => setRawAssets(assets.filter((asset) => asset.parseStatus === "awaiting_adapter")))
      .catch(() => setRawAssets([]));
  }, [experimentId]);

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
    setStatus({
      kind: "idle",
      message: selectedFile
        ? `已选择：${selectedFile.name}`
        : "请选择设备导出的 CSV 或 TXT 文本文件。",
    });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      setStatus({ kind: "error", message: "请先选择一个文件。" });
      return;
    }

    try {
      const asset = await uploadExperimentTextFile(experimentId, await buildExperimentFilePayload(file, sourceAssetId || undefined, sourceConversionNote));

      setStatus({
        kind: "success",
        message: asset.duplicate
          ? `已识别重复文件，并复用资产：${asset.assetId}`
          : `上传成功：${asset.originalName}，解析 ${asset.rowCount} 行。`,
      });
      startTransition(() => router.refresh());
    } catch (error) {
      setStatus({
        kind: "error",
        message: error instanceof Error ? error.message : "上传失败，请检查文件内容或后端服务。",
      });
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>上传实验设备文件</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            先支持 CSV/TXT 文本数据，上传后会写入文件资产和审计记录，并刷新上方审计摘要。
          </p>
        </div>
        <Badge tone={status.kind === "error" ? "danger" : status.kind === "success" ? "success" : "warning"}>
          数据收集与本地化
        </Badge>
      </div>

      <form className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]" onSubmit={onSubmit}>
        <label className="block">
          <span className="sr-only">选择实验设备文件</span>
          <input
            accept={experimentFileAccept}
            className="block w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700"
            disabled={isPending}
            onChange={onFileChange}
            type="file"
          />
        </label>
        <Button disabled={!file || isPending} type="submit">
          {isPending ? "上传中..." : "上传并记录审计"}
        </Button>
      </form>
      {rawAssets.length > 0 ? <label className="mt-3 block text-xs text-slate-600">转换来源（可选）<select className="mt-1 block w-full rounded-md border border-border bg-white px-3 py-2 text-sm" onChange={(event) => setSourceAssetId(event.target.value)} value={sourceAssetId}><option value="">不关联原始专有文件</option>{rawAssets.map((asset) => <option key={asset.assetId} value={asset.assetId}>{asset.originalName} · {asset.assetId}</option>)}</select><span className="mt-1 block text-[11px] text-slate-500">选择后，当前 CSV/XLSX 将作为该原始文件的结构化派生资产保存。</span></label> : null}

      {sourceAssetId ? <label className="mt-3 block text-xs text-slate-600">转换说明（可选）<input className="mt-1 block w-full rounded-md border border-border bg-white px-3 py-2 text-sm" maxLength={1000} onChange={(event) => setSourceConversionNote(event.target.value)} placeholder="例如：设备专用格式经解密工具 v1.2 转为 UTF-8 CSV" value={sourceConversionNote} /></label> : null}

      <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
        {status.message}
      </div>
    </Card>
  );
}
