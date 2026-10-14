"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { deleteExperimentFileAsset } from "@/lib/api";
import { ExperimentFileAsset } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";

export function ExperimentFileAssetsCard({ experimentId, assets }: { experimentId: string; assets: ExperimentFileAsset[] }) {
  const router = useRouter();
  const [visibleAssets, setVisibleAssets] = useState(assets);
  const [message, setMessage] = useState("");
  const [removingAssetId, setRemovingAssetId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const assetNames = new Map(visibleAssets.map((asset) => [asset.assetId, asset.originalName]));

  useEffect(() => setVisibleAssets(assets), [assets]);

  async function removeAsset(asset: ExperimentFileAsset) {
    const reason = window.prompt(`请填写移除“${asset.originalName}”的原因：`, "误上传或重复采集")?.trim();
    if (!reason) return;
    if (!window.confirm(`确认移除“${asset.originalName}”？此操作会留下审计记录。`)) return;
    setRemovingAssetId(asset.assetId);
    setMessage("");
    try {
      await deleteExperimentFileAsset(experimentId, asset.assetId, "研发负责人", reason);
      setVisibleAssets((current) => current.filter((item) => item.assetId !== asset.assetId));
      setMessage(`已移除 ${asset.originalName}，原因已写入审计记录。`);
      startTransition(() => router.refresh());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "移除失败，请稍后重试。");
    } finally {
      setRemovingAssetId(null);
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>最近上传文件资产</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            用于确认每个设备文件的格式、列名、行数、hash 和重复识别结果，是后续字段映射与清洗确认的基础。
          </p>
        </div>
        <Badge tone={assets.length > 0 ? "success" : "warning"}>
          {visibleAssets.length > 0 ? `${visibleAssets.length} 个文件资产` : "暂无文件资产"}
        </Badge>
      </div>

      {visibleAssets.length === 0 ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          上传 CSV/TXT 后，这里会显示文件格式、解析行数、字段名和内容 hash。
        </div>
      ) : (
        <div className="mt-4">
          <DataTable>
            <thead>
              <tr>
                <Th>文件名</Th>
                <Th>格式</Th>
                <Th>行数</Th>
                <Th>字段</Th>
                <Th>内容 hash</Th>
                <Th>来源链路</Th>
                <Th>状态</Th>
                <Th><span className="sr-only">人工操作</span></Th>
              </tr>
            </thead>
            <tbody>
              {visibleAssets.map((asset) => (
                <tr key={asset.assetId}>
                  <Td>
                    <div className="font-medium text-slate-950">{asset.originalName}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{asset.assetId}</div>
                  </Td>
                  <Td>{asset.detectedFormat}</Td>
                  <Td>{asset.rowCount}</Td>
                  <Td>
                    <div className="max-w-72 truncate" title={asset.columnNames.join(", ")}>
                      {asset.columnNames.length > 0 ? asset.columnNames.join(", ") : "未识别字段"}
                    </div>
                  </Td>
                  <Td>
                    <code className="text-[11px] text-slate-600">
                      {asset.contentHash.slice(0, 12)}
                    </code>
                  </Td>
                  <Td>
                    {asset.derivedFromAssetId ? (
                      <div className="max-w-48">
                        <div className="text-xs font-medium text-[#174333]">由原始设备文件转换</div>
                        <div className="mt-1 truncate text-[11px] text-slate-500" title={asset.derivedFromAssetId}>
                          {assetNames.get(asset.derivedFromAssetId) ?? asset.derivedFromAssetId}
                        </div>
                        {asset.sourceConversionNote ? <div className="mt-1 line-clamp-2 text-[11px] leading-4 text-slate-500" title={asset.sourceConversionNote}>{asset.sourceConversionNote}</div> : null}
                      </div>
                    ) : asset.parseStatus === "awaiting_adapter" ? (
                      <span className="text-xs text-amber-700">原始证据，待转换</span>
                    ) : (
                      <span className="text-xs text-slate-500">独立上传</span>
                    )}
                  </Td>
                  <Td>
                    <Badge tone={asset.duplicate ? "warning" : "success"}>
                      {asset.duplicate ? "重复复用" : asset.parseStatus === "awaiting_adapter" ? "待设备适配" : "已解析"}
                    </Badge>
                  </Td>
                  <Td>
                    <Button className="px-2.5 py-1.5 text-xs" disabled={isPending || removingAssetId !== null} onClick={() => void removeAsset(asset)} type="button" variant="secondary">
                      {removingAssetId === asset.assetId ? "移除中…" : "移除"}
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </div>
      )}
      <p aria-live="polite" className={`mt-3 text-xs leading-5 ${message ? "text-slate-600" : "sr-only"}`}>{message}</p>
    </Card>
  );
}
