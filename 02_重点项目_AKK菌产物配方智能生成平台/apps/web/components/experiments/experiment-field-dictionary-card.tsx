"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import {
  ExperimentFieldDictionary,
  ExperimentFieldMappingSuggestionResponse,
} from "@/lib/schemas";
import { upsertExperimentFieldDictionary } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

export function ExperimentFieldDictionaryCard({
  experimentId,
  dictionary,
  mapping,
}: {
  experimentId: string;
  dictionary: ExperimentFieldDictionary;
  mapping: ExperimentFieldMappingSuggestionResponse;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const unknownColumns = useMemo(
    () =>
      mapping.assets.flatMap((asset) =>
        asset.suggestions
          .filter((suggestion) => !suggestion.standardField)
          .map((suggestion) => suggestion.originalColumn),
      ),
    [mapping],
  );
  const [sourceColumn, setSourceColumn] = useState(unknownColumns[0] ?? "");
  const [standardField, setStandardField] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [unit, setUnit] = useState("");
  const [message, setMessage] = useState(
    dictionary.entryCount > 0
      ? `企业字段词典已有 ${dictionary.entryCount} 条规则。`
      : "尚未添加企业字段词典规则。",
  );

  async function onSave() {
    if (!sourceColumn.trim() || !standardField.trim() || !displayName.trim()) {
      setMessage("请填写原始字段、标准字段和显示名。");
      return;
    }

    try {
      const result = await upsertExperimentFieldDictionary(experimentId, {
        entries: [
          {
            sourceColumn: sourceColumn.trim(),
            standardField: standardField.trim(),
            displayName: displayName.trim(),
            unit: unit.trim() || null,
            createdBy: "researcher",
          },
        ],
      });
      setMessage(`已保存 ${result.entryCount} 条企业字段词典规则，字段建议将重新识别。`);
      startTransition(() => router.refresh());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "企业字段词典保存失败。");
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>企业字段词典扩展</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            将未知字段沉淀为企业自定义词典。后续同名字段会优先按企业词典识别，减少重复人工判断。
          </p>
        </div>
        <Badge tone={unknownColumns.length > 0 ? "warning" : "success"}>
          {unknownColumns.length > 0 ? `${unknownColumns.length} 个未知字段` : "暂无未知字段"}
        </Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <label className="grid gap-1 text-xs text-slate-600">
          原始字段
          <input
            className="rounded-md border border-border px-3 py-2 text-sm text-slate-900"
            onChange={(event) => setSourceColumn(event.target.value)}
            placeholder="UnknownSignal"
            value={sourceColumn}
          />
        </label>
        <label className="grid gap-1 text-xs text-slate-600">
          标准字段
          <input
            className="rounded-md border border-border px-3 py-2 text-sm text-slate-900"
            onChange={(event) => setStandardField(event.target.value)}
            placeholder="custom_unknown_signal"
            value={standardField}
          />
        </label>
        <label className="grid gap-1 text-xs text-slate-600">
          显示名
          <input
            className="rounded-md border border-border px-3 py-2 text-sm text-slate-900"
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="自定义信号"
            value={displayName}
          />
        </label>
        <label className="grid gap-1 text-xs text-slate-600">
          单位
          <input
            className="rounded-md border border-border px-3 py-2 text-sm text-slate-900"
            onChange={(event) => setUnit(event.target.value)}
            placeholder="a.u."
            value={unit}
          />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={isPending} onClick={onSave}>
          {isPending ? "保存中..." : "保存到企业字段词典"}
        </Button>
        <span className="text-xs text-muted-foreground">
          保存后字段识别建议会优先使用企业词典。
        </span>
      </div>

      <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
        {message}
      </div>
    </Card>
  );
}
