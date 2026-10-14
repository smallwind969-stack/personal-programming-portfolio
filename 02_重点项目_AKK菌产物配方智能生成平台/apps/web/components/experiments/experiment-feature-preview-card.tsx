import { ExperimentFeaturePreviewResponse } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";

export function ExperimentFeaturePreviewCard({
  preview,
}: {
  preview: ExperimentFeaturePreviewResponse;
}) {
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>特征工程预览</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            基于时间轴对齐后的宽表计算基础统计、变化量、窗口均值和异常点提示，为后续建模准备输入特征。
          </p>
        </div>
        <Badge tone={preview.anomalyHints.length > 0 ? "warning" : "success"}>
          {preview.anomalyHints.length > 0
            ? `${preview.anomalyHints.length} 个异常提示`
            : "暂无异常提示"}
        </Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <MiniMetric label="对齐行数" value={preview.rowCount.toString()} />
        <MiniMetric label="特征数" value={preview.featureCount.toString()} />
        <MiniMetric label="异常提示" value={preview.anomalyHints.length.toString()} />
      </div>

      {preview.features.length === 0 ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          完成时间轴对齐后，这里会显示数值字段的特征摘要。
        </div>
      ) : (
        <div className="mt-4">
          <DataTable>
            <thead>
              <tr>
                <Th>字段</Th>
                <Th>count</Th>
                <Th>min</Th>
                <Th>max</Th>
                <Th>mean</Th>
                <Th>first</Th>
                <Th>last</Th>
                <Th>delta</Th>
                <Th>windowMean</Th>
              </tr>
            </thead>
            <tbody>
              {preview.features.map((feature) => (
                <tr key={feature.field}>
                  <Td>{feature.field}</Td>
                  <Td>{feature.count}</Td>
                  <Td>{feature.min}</Td>
                  <Td>{feature.max}</Td>
                  <Td>{feature.mean}</Td>
                  <Td>{feature.first}</Td>
                  <Td>{feature.last}</Td>
                  <Td>{feature.delta}</Td>
                  <Td>{feature.windowMean}</Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </div>
      )}

      <div className="mt-4 rounded-lg bg-slate-50 p-3">
        <div className="text-xs font-semibold text-slate-950">异常点提示</div>
        <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
          {preview.anomalyHints.length > 0
            ? preview.anomalyHints.slice(0, 5).map((hint) => (
                <div key={`${hint.field}-${hint.timestamp}`}>
                  {hint.timestamp} / {hint.field} = {hint.value}：{hint.reason}
                </div>
              ))
            : "暂无异常点提示"}
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
