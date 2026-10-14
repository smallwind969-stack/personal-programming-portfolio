import { ExperimentAlignmentPreviewResponse } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";

export function ExperimentAlignmentPreviewCard({
  preview,
}: {
  preview: ExperimentAlignmentPreviewResponse;
}) {
  const fields = Array.from(
    new Set(
      preview.alignedRows.flatMap((row) =>
        Object.keys(row).filter((field) => field !== "timestamp"),
      ),
    ),
  );

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>时间轴对齐预览</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            将多设备清洗后的标准字段按 timestamp 合并成宽表，展示缺失时间点和对齐后的建模输入预览。
          </p>
        </div>
        <Badge tone={preview.missingCellCount > 0 ? "warning" : "success"}>
          {preview.missingCellCount > 0
            ? `${preview.missingCellCount} 个缺失单元`
            : "时间轴完整"}
        </Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <MiniMetric label="文件数" value={preview.assetCount.toString()} />
        <MiniMetric label="时间点" value={preview.timestampCount.toString()} />
        <MiniMetric label="缺失单元" value={preview.missingCellCount.toString()} />
      </div>

      {preview.alignedRows.length === 0 ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          完成字段确认和清洗预览后，这里会显示多设备时间轴对齐结果。
        </div>
      ) : (
        <div className="mt-4">
          <DataTable>
            <thead>
              <tr>
                <Th>timestamp</Th>
                {fields.map((field) => (
                  <Th key={field}>{field}</Th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.alignedRows.slice(0, 6).map((row) => (
                <tr key={String(row.timestamp)}>
                  <Td>{row.timestamp}</Td>
                  {fields.map((field) => (
                    <Td key={field}>{row[field] ?? "-"}</Td>
                  ))}
                </tr>
              ))}
            </tbody>
          </DataTable>
        </div>
      )}

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="text-xs font-semibold text-slate-950">设备时间点摘要</div>
          <div className="mt-2 space-y-2 text-xs leading-5 text-slate-700">
            {preview.assetSummaries.length > 0
              ? preview.assetSummaries.map((asset) => (
                  <div key={asset.assetId}>
                    {asset.originalName}: {asset.timestampCount} 个时间点，
                    字段 {asset.fields.join(", ") || "无"}
                  </div>
                ))
              : "暂无设备摘要"}
          </div>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="text-xs font-semibold text-slate-950">对齐日志</div>
          <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
            {preview.alignmentLogs.length > 0
              ? preview.alignmentLogs.slice(0, 5).map((log) => <div key={log}>{log}</div>)
              : "暂无对齐问题"}
          </div>
        </div>
      </div>
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
