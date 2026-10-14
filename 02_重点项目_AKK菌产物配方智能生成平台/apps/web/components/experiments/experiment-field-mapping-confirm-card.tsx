"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import {
  ExperimentConfirmedFieldMappingSet,
  ExperimentFieldMappingSuggestionResponse,
} from "@/lib/schemas";
import { confirmExperimentFieldMappings } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

export function ExperimentFieldMappingConfirmCard({
  experimentId,
  mapping,
  confirmedMappings,
}: {
  experimentId: string;
  mapping: ExperimentFieldMappingSuggestionResponse;
  confirmedMappings: ExperimentConfirmedFieldMappingSet;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState(
    confirmedMappings.mappingCount > 0
      ? `已保存 ${confirmedMappings.mappingCount} 条字段映射。`
      : "尚未保存字段映射确认结果。",
  );

  const confirmableMappings = mapping.assets.flatMap((asset) =>
    asset.suggestions
      .filter((suggestion) => suggestion.standardField)
      .map((suggestion) => ({
        assetId: asset.assetId,
        originalColumn: suggestion.originalColumn,
        standardField: suggestion.standardField ?? "",
        displayName: suggestion.displayName,
        unit: suggestion.unit ?? null,
        confirmedBy: "researcher",
        confirmed: true,
      })),
  );

  async function onConfirm() {
    if (confirmableMappings.length === 0) {
      setMessage("当前没有可自动确认的字段，请先上传可识别的设备文件。");
      return;
    }

    try {
      const result = await confirmExperimentFieldMappings(experimentId, {
        mappings: confirmableMappings,
      });
      setMessage(`已保存 ${result.mappingCount} 条字段映射，可进入清洗和对齐阶段。`);
      startTransition(() => router.refresh());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "字段映射确认失败。");
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>字段映射人工确认</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            将当前可识别字段保存为实验级确认配置。未知字段会继续保留为待确认项，后续可加入手动编辑。
          </p>
        </div>
        <Badge tone={confirmedMappings.mappingCount > 0 ? "success" : "warning"}>
          {confirmedMappings.mappingCount > 0
            ? `${confirmedMappings.mappingCount} 条已确认`
            : "待确认"}
        </Badge>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={isPending || confirmableMappings.length === 0} onClick={onConfirm}>
          {isPending ? "保存中..." : `确认 ${confirmableMappings.length} 条可识别字段`}
        </Button>
        <span className="text-xs text-muted-foreground">
          需要人工编辑的未知字段不会被自动保存。
        </span>
      </div>

      <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
        {message}
      </div>
    </Card>
  );
}
