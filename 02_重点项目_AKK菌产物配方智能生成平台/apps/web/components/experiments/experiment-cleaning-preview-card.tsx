import { ExperimentCleaningPreviewResponse } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";

export function ExperimentCleaningPreviewCard({
  preview,
}: {
  preview: ExperimentCleaningPreviewResponse;
}) {
  const totalIssues = preview.assets.reduce(
    (sum, asset) =>
      sum +
      asset.quality.missingValueCount +
      asset.quality.invalidNumericCount +
      asset.quality.unmappedColumnCount,
    0,
  );

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>数据清洗预览</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            基于已确认字段映射生成标准字段视图，并统计缺失值、非法数值和未映射列，供入库前人工确认。
          </p>
        </div>
        <Badge tone={totalIssues > 0 ? "warning" : "success"}>
          {totalIssues > 0 ? `${totalIssues} 个质量提示` : "清洗预览通过"}
        </Badge>
      </div>

      {preview.assets.length === 0 ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          上传文件并确认字段映射后，这里会显示清洗预览。
        </div>
      ) : (
        <div className="mt-4">
          <DataTable>
            <thead>
              <tr>
                <Th>文件</Th>
                <Th>行数</Th>
                <Th>缺失值</Th>
                <Th>非法数值</Th>
                <Th>未映射列</Th>
                <Th>标准字段样例</Th>
                <Th>清洗日志</Th>
              </tr>
            </thead>
            <tbody>
              {preview.assets.map((asset) => (
                <tr key={asset.assetId}>
                  <Td>
                    <div className="font-medium text-slate-950">{asset.originalName}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{asset.assetId}</div>
                  </Td>
                  <Td>{asset.rowCount}</Td>
                  <Td>{asset.quality.missingValueCount}</Td>
                  <Td>{asset.quality.invalidNumericCount}</Td>
                  <Td>{asset.quality.unmappedColumnCount}</Td>
                  <Td>
                    <code className="block max-w-80 whitespace-pre-wrap text-[11px] text-slate-700">
                      {JSON.stringify(asset.cleanedRows[0] ?? {}, null, 2)}
                    </code>
                  </Td>
                  <Td>
                    <div className="max-w-80 space-y-1 text-xs leading-5 text-slate-700">
                      {asset.cleaningLogs.length > 0
                        ? asset.cleaningLogs.slice(0, 3).map((log) => <div key={log}>{log}</div>)
                        : "暂无清洗问题"}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </div>
      )}
    </Card>
  );
}
