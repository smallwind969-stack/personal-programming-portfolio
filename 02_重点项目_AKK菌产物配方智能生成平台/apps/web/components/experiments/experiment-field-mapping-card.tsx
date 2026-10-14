import { ExperimentFieldMappingSuggestionResponse } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";

export function ExperimentFieldMappingCard({
  mapping,
}: {
  mapping: ExperimentFieldMappingSuggestionResponse;
}) {
  const suggestions = mapping.assets.flatMap((asset) =>
    asset.suggestions.map((suggestion) => ({
      ...suggestion,
      assetId: asset.assetId,
      originalName: asset.originalName,
    })),
  );
  const confirmationCount = suggestions.filter(
    (suggestion) => suggestion.requiresHumanConfirmation,
  ).length;

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>字段识别与标准化建议</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            把设备原始列名映射为平台标准字段，并标出需要人工确认的位置，避免清洗和建模阶段误读数据。
          </p>
        </div>
        <Badge tone={confirmationCount > 0 ? "warning" : "success"}>
          {confirmationCount > 0 ? `${confirmationCount} 项需确认` : "无需人工确认"}
        </Badge>
      </div>

      {suggestions.length === 0 ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          上传文件后，系统会基于列名生成标准字段映射建议。
        </div>
      ) : (
        <div className="mt-4">
          <DataTable>
            <thead>
              <tr>
                <Th>来源文件</Th>
                <Th>原始字段</Th>
                <Th>标准字段</Th>
                <Th>单位</Th>
                <Th>置信度</Th>
                <Th>确认状态</Th>
                <Th>原因</Th>
              </tr>
            </thead>
            <tbody>
              {suggestions.map((suggestion) => (
                <tr key={`${suggestion.assetId}-${suggestion.originalColumn}`}>
                  <Td>
                    <div className="font-medium text-slate-950">{suggestion.originalName}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{suggestion.assetId}</div>
                  </Td>
                  <Td>{suggestion.originalColumn}</Td>
                  <Td>
                    {suggestion.standardField ? (
                      <div>
                        <div className="font-medium text-slate-950">{suggestion.standardField}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {suggestion.displayName}
                        </div>
                      </div>
                    ) : (
                      <span className="text-slate-500">未识别</span>
                    )}
                  </Td>
                  <Td>{suggestion.unit ?? "-"}</Td>
                  <Td>{Math.round(suggestion.confidenceScore * 100)}%</Td>
                  <Td>
                    <Badge tone={suggestion.requiresHumanConfirmation ? "warning" : "success"}>
                      {suggestion.requiresHumanConfirmation ? "需要确认" : "自动通过"}
                    </Badge>
                  </Td>
                  <Td>
                    <div className="max-w-80 text-xs leading-5 text-slate-700">
                      {suggestion.reason}
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
