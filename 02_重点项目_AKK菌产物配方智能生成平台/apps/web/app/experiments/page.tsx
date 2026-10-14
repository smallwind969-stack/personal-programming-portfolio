import {
  getExperimentAlignmentPreview,
  getExperimentCleaningPreview,
  getExperimentConfirmedFieldMappings,
  getExperimentFieldDictionary,
  getExperimentFieldMappingSuggestions,
  getExperimentFeaturePreview,
  getExperimentFileAssets,
  getExperimentFileAuditSummary,
  getExperimentModelingPlanPreview,
  getLatestExperimentResearchBrief,
  getLatestExperimentSimulationInput,
  getLatestExperimentTrainingResult,
  getLatestExperimentTrainingTask,
  getExperimentRecords,
  getFormulaResults,
  getLatestExperimentDatasetSnapshot,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { DataTable, Td, Th } from "@/components/ui/table";
import { ExperimentAlignmentPreviewCard } from "@/components/experiments/experiment-alignment-preview-card";
import { ExperimentCleaningPreviewCard } from "@/components/experiments/experiment-cleaning-preview-card";
import { ExperimentDatasetSnapshotCard } from "@/components/experiments/experiment-dataset-snapshot-card";
import { ExperimentFieldMappingCard } from "@/components/experiments/experiment-field-mapping-card";
import { ExperimentFieldMappingConfirmCard } from "@/components/experiments/experiment-field-mapping-confirm-card";
import { ExperimentFeaturePreviewCard } from "@/components/experiments/experiment-feature-preview-card";
import { ExperimentFieldDictionaryCard } from "@/components/experiments/experiment-field-dictionary-card";
import { ExperimentFileAssetsCard } from "@/components/experiments/experiment-file-assets-card";
import { ExperimentFileUploadCard } from "@/components/experiments/experiment-file-upload-card";
import { ExperimentModelingPlanCard } from "@/components/experiments/experiment-modeling-plan-card";
import { ExperimentResearchBriefCard } from "@/components/experiments/experiment-research-brief-card";
import { ExperimentSimulationInputCard } from "@/components/experiments/experiment-simulation-input-card";
import { ExperimentTrainingResultCard } from "@/components/experiments/experiment-training-result-card";
import { ExperimentTrainingTaskCard } from "@/components/experiments/experiment-training-task-card";

const SUMMARY_EXPERIMENT_ID = "exp-akk-summary";

export default async function ExperimentsPage() {
  const [
    records,
    results,
    fileAuditSummary,
    fileAssets,
    fieldMapping,
    confirmedFieldMappings,
    fieldDictionary,
    cleaningPreview,
    alignmentPreview,
    featurePreview,
    latestDatasetSnapshot,
    modelingPlanPreview,
    latestTrainingTask,
    latestTrainingResult,
    latestResearchBrief,
    latestSimulationInput,
  ] = await Promise.all([
    getExperimentRecords(),
    getFormulaResults(),
    getExperimentFileAuditSummary(SUMMARY_EXPERIMENT_ID),
    getExperimentFileAssets(SUMMARY_EXPERIMENT_ID),
    getExperimentFieldMappingSuggestions(SUMMARY_EXPERIMENT_ID),
    getExperimentConfirmedFieldMappings(SUMMARY_EXPERIMENT_ID),
    getExperimentFieldDictionary(SUMMARY_EXPERIMENT_ID),
    getExperimentCleaningPreview(SUMMARY_EXPERIMENT_ID),
    getExperimentAlignmentPreview(SUMMARY_EXPERIMENT_ID),
    getExperimentFeaturePreview(SUMMARY_EXPERIMENT_ID),
    getLatestExperimentDatasetSnapshot(SUMMARY_EXPERIMENT_ID),
    getExperimentModelingPlanPreview(SUMMARY_EXPERIMENT_ID),
    getLatestExperimentTrainingTask(SUMMARY_EXPERIMENT_ID),
    getLatestExperimentTrainingResult(SUMMARY_EXPERIMENT_ID),
    getLatestExperimentResearchBrief(SUMMARY_EXPERIMENT_ID),
    getLatestExperimentSimulationInput(SUMMARY_EXPERIMENT_ID),
  ]);

  const passCount = records.filter((record) => record.status === "pass").length;
  const watchCount = records.filter((record) => record.status === "watch").length;
  const failCount = records.filter((record) => record.status === "fail").length;
  const passRate = records.length ? Math.round((passCount / records.length) * 100) : 0;
  const latestResult = results[0];
  const latestResultName = latestResult?.candidates[0]?.candidateName ?? "暂无方案";
  const latestStatus =
    failCount > 0 ? "需要优化" : watchCount > 0 ? "建议复测" : "可进入下一轮";
  const latestUpload = fileAuditSummary.lastEvent;
  const latestUploadNames = latestUpload?.fileNames.join(" / ") ?? "暂无上传文件";
  const fileUploadStage = fileAuditSummary.stageSummary[0]?.stageLabel ?? "文件上传";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-xs font-medium text-primary">工业打样数据看板</div>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950">实验平台</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            当前展示面向研发实验的数据资产化入口：记录实验结果、追踪设备文件上传，并逐步接入清洗、对齐、建模和报告生成。
          </p>
        </div>
        <Badge tone={failCount > 0 ? "warning" : "success"}>{latestStatus}</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-5">
        <MetricCard label="实验记录" value={records.length.toString()} />
        <MetricCard label="通过" value={passCount.toString()} tone="success" />
        <MetricCard label="待观察" value={watchCount.toString()} tone="warning" />
        <MetricCard label="需优化" value={failCount.toString()} tone="danger" />
        <MetricCard
          label="通过率"
          value={`${passRate}%`}
          tone={passRate >= 60 ? "success" : "warning"}
        />
      </div>

      <ExperimentFileUploadCard experimentId={SUMMARY_EXPERIMENT_ID} />

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>实验数据入口审计</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              展示多设备原始文件进入平台后的可追溯状态，后续会继续接入数据收集定位、清洗、对齐和解释阶段。
            </p>
          </div>
          <Badge tone={fileAuditSummary.eventCount > 0 ? "success" : "warning"}>
            {fileUploadStage}
          </Badge>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <MetricCard label="上传审计事件" value={fileAuditSummary.eventCount.toString()} />
          <MetricCard
            label="文件资产数量"
            value={fileAuditSummary.assetCount.toString()}
            tone="success"
          />
          <MetricCard label="阶段数量" value={fileAuditSummary.stageSummary.length.toString()} />
        </div>
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
          最近上传：{latestUploadNames}
        </div>
      </Card>

      <ExperimentFileAssetsCard assets={fileAssets} experimentId={SUMMARY_EXPERIMENT_ID} />

      <ExperimentFieldMappingCard mapping={fieldMapping} />

      <ExperimentFieldDictionaryCard
        dictionary={fieldDictionary}
        experimentId={SUMMARY_EXPERIMENT_ID}
        mapping={fieldMapping}
      />

      <ExperimentFieldMappingConfirmCard
        confirmedMappings={confirmedFieldMappings}
        experimentId={SUMMARY_EXPERIMENT_ID}
        mapping={fieldMapping}
      />

      <ExperimentCleaningPreviewCard preview={cleaningPreview} />

      <ExperimentAlignmentPreviewCard preview={alignmentPreview} />

      <ExperimentFeaturePreviewCard preview={featurePreview} />

      <ExperimentDatasetSnapshotCard
        experimentId={SUMMARY_EXPERIMENT_ID}
        snapshot={latestDatasetSnapshot}
      />

      <ExperimentModelingPlanCard plan={modelingPlanPreview} />

      <ExperimentTrainingTaskCard
        experimentId={SUMMARY_EXPERIMENT_ID}
        task={latestTrainingTask}
      />

      <ExperimentTrainingResultCard result={latestTrainingResult} />

      <ExperimentResearchBriefCard brief={latestResearchBrief} />

      <ExperimentSimulationInputCard simulation={latestSimulationInput} />

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>最近方案实验概览</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">{latestResultName}</p>
            </div>
            <Badge tone="success">合成工业数据</Badge>
          </div>

          <div className="mt-4 space-y-3">
            <ProgressRow label="通过" value={passCount} total={records.length} tone="bg-emerald-500" />
            <ProgressRow label="待观察" value={watchCount} total={records.length} tone="bg-amber-500" />
            <ProgressRow label="需优化" value={failCount} total={records.length} tone="bg-red-500" />
          </div>

          <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-6 text-slate-700">
            研发判断：通过项可作为下一轮样品评审依据；待观察项建议设置梯度复测；需优化项应回到配方设计台调整比例或工艺条件。
          </div>
        </Card>

        <Card>
          <CardTitle>下一轮验证建议</CardTitle>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <ActionCard
              title="稳定性复测"
              text="对酸性体系、浊度和关键标志物保留率做加速条件观察。"
            />
            <ActionCard
              title="感官小试"
              text="组织 3-5 个比例梯度的口感、底味、外观和接受度评估。"
            />
            <ActionCard
              title="方案审核"
              text="把知识库引用、配比假设和实验数据归档，进入研发审核流程。"
            />
          </div>
        </Card>
      </section>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>实验记录明细</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              每条记录对应方案样品的一个验证指标。
            </p>
          </div>
          <Badge>Research use only</Badge>
        </div>
        <div className="mt-4">
          <DataTable>
            <thead>
              <tr>
                <Th>样品编号</Th>
                <Th>测试项目</Th>
                <Th>结果</Th>
                <Th>目标范围</Th>
                <Th>状态</Th>
                <Th>结论</Th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.experimentId}>
                  <Td>
                    <div className="font-medium text-slate-950">{record.sampleCode}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{record.resultId}</div>
                  </Td>
                  <Td>{record.testName}</Td>
                  <Td>
                    <span className="font-semibold text-slate-950">{record.metricValue}</span>{" "}
                    {record.unit}
                  </Td>
                  <Td>{record.targetRange}</Td>
                  <Td>
                    <StatusBadge status={record.status} />
                  </Td>
                  <Td>{record.conclusion}</Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </div>
      </Card>
    </div>
  );
}

function MetricCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  return (
    <Card>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
      <div className="mt-2">
        <Badge tone={tone}>实时汇总</Badge>
      </div>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "pass") return <Badge tone="success">通过</Badge>;
  if (status === "watch") return <Badge tone="warning">待观察</Badge>;
  return <Badge tone="danger">需优化</Badge>;
}

function ProgressRow({
  label,
  value,
  total,
  tone,
}: {
  label: string;
  value: number;
  total: number;
  tone: string;
}) {
  const percent = total ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span>{percent}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${tone}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function ActionCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg border border-border bg-slate-50 p-3">
      <div className="font-semibold text-slate-950">{title}</div>
      <p className="mt-2 text-xs leading-5 text-slate-700">{text}</p>
    </div>
  );
}
