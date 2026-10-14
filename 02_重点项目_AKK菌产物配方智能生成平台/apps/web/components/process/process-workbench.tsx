"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ResponseSurface } from "@/components/process/response-surface";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { generateProcessTask, getLlmStatus, getSimulationLlmStatus, submitProcessFeedback } from "@/lib/api";
import {
  GeneratedProcessTask,
  LlmStatus,
  ProcessCandidatePlan,
  ProcessFeedbackRequest,
  ProcessProductionLine,
  ProcessTaskRequest,
  SimulationLlmStatus,
} from "@/lib/schemas";

const stages = ["目标产品", "产线现状", "方案探索", "状态建议书"];
const defaultConstraints = ["低异味", "低苦味", "不可破坏果冻凝胶体系"];
const modelCard = {
  sampleCount: 180,
  functionR2: 0.861,
  structureR2: 0.697,
  version: "论文锚点模拟模型 v0.2",
};

export function ProcessWorkbench({ productionLines }: { productionLines: ProcessProductionLine[] }) {
  const firstLine = productionLines[0];
  const [stageIndex, setStageIndex] = useState(0);
  const [target, setTarget] = useState<ProcessTaskRequest>({
    targetProductName: "功能果冻",
    targetProductForm: "果冻",
    akkProductType: "AKK 后生元",
    applicationDirection: "肠道健康方向的日常营养补充",
    targetContent: "每批次有效成分 18-24 g",
    activityTarget: "活性保留不低于 82%",
    stabilityTarget: "常温 90 天指标衰减不超过 15%",
    costLimit: "培养与后处理成本不高于 620 元/批",
    optimizationStrategy: "综合平衡",
    allowCoCulture: true,
    targetScale: "中试 200 升",
    constraints: defaultConstraints,
    productionLineId: firstLine?.lineId ?? "",
    currentTemperature: 36,
    currentPh: 6.8,
    currentAgitationRpm: 160,
    currentVolumeL: 200,
    sensorCapability: "pH、温度、ORP、DO 在线",
    downstreamCapability: "离心、膜过滤、浓缩、冻干",
  });
  const [task, setTask] = useState<GeneratedProcessTask>();
  const [selectedPlanId, setSelectedPlanId] = useState("plan-balance");
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [autoRecalculate, setAutoRecalculate] = useState(true);
  const [hasGenerated, setHasGenerated] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string>();
  const [llmStatus, setLlmStatus] = useState<LlmStatus>();
  const [simulationLlmStatus, setSimulationLlmStatus] = useState<SimulationLlmStatus>();
  const [error, setError] = useState<string | null>(null);
  const requestSeq = useRef(0);

  const selectedLine = useMemo(
    () => productionLines.find((line) => line.lineId === target.productionLineId) ?? firstLine,
    [firstLine, productionLines, target.productionLineId],
  );
  const selectedPlan = task?.candidatePlans.find((plan) => plan.planId === selectedPlanId) ?? task?.candidatePlans[0];
  const selectedConfidence = selectedPlan?.scoreBreakdown.confidenceScore ?? 0;

  useEffect(() => {
    getLlmStatus()
      .then(setLlmStatus)
      .catch(() => setLlmStatus(undefined));
    getSimulationLlmStatus()
      .then(setSimulationLlmStatus)
      .catch(() => setSimulationLlmStatus(undefined));
  }, []);

  useEffect(() => {
    if (!autoRecalculate || !hasGenerated) return;
    const timer = window.setTimeout(() => {
      void runGenerate({ keepStage: true, reason: "输入变化后自动重算" });
    }, 700);
    return () => window.clearTimeout(timer);
  }, [target, autoRecalculate, hasGenerated]);

  function update(patch: Partial<ProcessTaskRequest>) {
    setTarget((current) => ({ ...current, ...patch }));
  }

  function selectLine(line: ProcessProductionLine) {
    update({
      productionLineId: line.lineId,
      currentTemperature: clamp(target.currentTemperature ?? 36, line.temperatureRange.min, line.temperatureRange.max),
      currentPh: clamp(target.currentPh ?? 6.8, line.phRange.min, line.phRange.max),
      currentAgitationRpm: clamp(target.currentAgitationRpm ?? 160, line.agitationRange.min, line.agitationRange.max),
      currentVolumeL: Number.parseFloat(line.workingVolume.split("-").at(-1) ?? "50"),
      sensorCapability: line.sensors.join("、"),
      downstreamCapability: line.downstreamCapabilities.join("、"),
    });
  }

  async function runGenerate(options: { keepStage?: boolean; reason?: string } = {}) {
    const seq = requestSeq.current + 1;
    requestSeq.current = seq;
    setIsGenerating(true);
    setError(null);
    try {
      const generated = await generateProcessTask(target);
      if (seq !== requestSeq.current) return;
      setTask(generated);
      setHasGenerated(true);
      setLastUpdatedAt(new Date().toLocaleTimeString("zh-CN", { hour12: false }));
      const stillExists = generated.candidatePlans.some((plan) => plan.planId === selectedPlanId);
      setSelectedPlanId(stillExists ? selectedPlanId : generated.candidatePlans.find((plan) => plan.planId === "plan-balance")?.planId ?? generated.candidatePlans[0]?.planId);
      if (!options.keepStage) setStageIndex(2);
    } catch (err) {
      if (seq === requestSeq.current) setError(err instanceof Error ? err.message : "方案生成失败");
    } finally {
      if (seq === requestSeq.current) setIsGenerating(false);
    }
  }

  async function handleFeedbackSubmit(formData: FormData) {
    if (!task) return;
    const payload: ProcessFeedbackRequest = {
      taskId: task.taskId,
      actualYield: String(formData.get("actualYield") || "待检测"),
      actualActivity: String(formData.get("actualActivity") || "待复测"),
      contaminationObserved: formData.get("contaminationObserved") === "on",
      equipmentAbnormalities: [String(formData.get("equipmentAbnormalities") || "无")],
      conclusion: String(formData.get("conclusion") || "等待复盘"),
      notes: String(formData.get("notes") || ""),
    };
    await submitProcessFeedback(payload);
    setFeedbackSaved(true);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Badge tone="success">内部研发实验建议</Badge>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">新建 AKK 产品工艺任务</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              从要生产的终端产品出发，推导目标产物需求，录入产线现状，再由数学模型实时生成三套候选方案和响应面曲线。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {stages.map((stage, index) => (
              <button
                className={`rounded-md border px-3 py-2 text-xs font-medium ${index === stageIndex ? "border-emerald-700 bg-emerald-700 text-white" : "border-slate-200 bg-white text-slate-600"}`}
                key={stage}
                onClick={() => setStageIndex(index)}
                type="button"
              >
                {stage}
              </button>
            ))}
          </div>
        </div>
      </section>

      <ModelRuntimeBar
        autoRecalculate={autoRecalculate}
        confidence={selectedConfidence}
        isGenerating={isGenerating}
        lastUpdatedAt={lastUpdatedAt}
        llmStatus={llmStatus}
        simulationLlmStatus={simulationLlmStatus}
        onRefresh={() => runGenerate({ keepStage: true, reason: "手动刷新" })}
        onToggleAuto={() => setAutoRecalculate((value) => !value)}
      />

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}

      <div className="grid gap-5 xl:grid-cols-[1fr_330px]">
        <main className="space-y-5">
          {stageIndex === 0 ? <TargetStage target={target} update={update} onNext={() => setStageIndex(1)} /> : null}
          {stageIndex === 1 && selectedLine ? (
            <LineStage
              lines={productionLines}
              selectedLine={selectedLine}
              target={target}
              update={update}
              selectLine={selectLine}
              onBack={() => setStageIndex(0)}
              onGenerate={() => runGenerate()}
              isGenerating={isGenerating}
              hasGenerated={hasGenerated}
            />
          ) : null}
          {stageIndex === 2 && task && selectedPlan ? (
            <ExploreStage
              task={task}
              target={target}
              selectedPlan={selectedPlan}
              selectedPlanId={selectedPlanId}
              onBackTarget={() => setStageIndex(0)}
              onBackLine={() => setStageIndex(1)}
              onSelectPlan={setSelectedPlanId}
              onNext={() => setStageIndex(3)}
            />
          ) : null}
          {stageIndex === 2 && !task ? (
            <Card>
              <CardTitle>尚未生成方案</CardTitle>
              <p className="mt-3 text-sm text-muted-foreground">请先录入目标产品和产线现状，系统会生成三套候选方案。</p>
              <Button className="mt-4" onClick={() => setStageIndex(1)}>返回产线现状</Button>
            </Card>
          ) : null}
          {stageIndex === 3 && task && selectedPlan ? (
            <ReportStage
              task={task}
              selectedPlan={selectedPlan}
              feedbackSaved={feedbackSaved}
              onBackExplore={() => setStageIndex(2)}
              onFeedbackSubmit={handleFeedbackSubmit}
            />
          ) : null}
        </main>

        <TaskSummary target={target} selectedLine={selectedLine} selectedPlan={selectedPlan} task={task} llmStatus={llmStatus} simulationLlmStatus={simulationLlmStatus} />
      </div>
    </div>
  );
}

function ModelRuntimeBar({
  autoRecalculate,
  confidence,
  isGenerating,
  lastUpdatedAt,
  llmStatus,
  simulationLlmStatus,
  onRefresh,
  onToggleAuto,
}: {
  autoRecalculate: boolean;
  confidence: number;
  isGenerating: boolean;
  lastUpdatedAt?: string;
  llmStatus?: LlmStatus;
  simulationLlmStatus?: SimulationLlmStatus;
  onRefresh: () => void;
  onToggleAuto: () => void;
}) {
  const cloudReady = Boolean(simulationLlmStatus?.enabled && simulationLlmStatus.apiKeyConfigured);
  const localReady = Boolean(llmStatus?.enabled && llmStatus.available);
  return (
    <section className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:grid-cols-[1.2fr_0.8fr]">
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="模型版本" value={modelCard.version} />
        <Stat label="模拟样本量" value={`${modelCard.sampleCount} 组`} />
        <Stat label="功能模型精度" value={`R2 ${modelCard.functionR2}`} />
        <Stat label="当前置信度" value={confidence ? `${confidence}/100` : "待生成"} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-slate-50 p-3">
        <div className="text-xs leading-5 text-slate-600">
          <div className="font-medium text-slate-950">{isGenerating ? "模型正在重算" : lastUpdatedAt ? `上次重算 ${lastUpdatedAt}` : "等待首次生成"}</div>
          <div>
            {cloudReady
              ? `云端推理服务已配置：${simulationLlmStatus?.model}`
              : localReady
                ? `本地推理服务已连接：${llmStatus?.model}`
                : "增强推理未接入：当前为数学模型与规则校验结果"}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={onToggleAuto}>{autoRecalculate ? "自动重算开" : "自动重算关"}</Button>
          <Button disabled={isGenerating} onClick={onRefresh}>{isGenerating ? "重算中" : "立即重算"}</Button>
        </div>
      </div>
    </section>
  );
}

function TargetStage({ target, update, onNext }: { target: ProcessTaskRequest; update: (patch: Partial<ProcessTaskRequest>) => void; onNext: () => void }) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <CardTitle>第一步：输入要生产的产品</CardTitle>
          <p className="mt-2 text-sm leading-6 text-slate-600">这里输入的是最终产品，例如功能果冻、饮料、软糖。系统会根据产品目标反推需要的 AKK 相关产物窗口。</p>
        </div>
        <Badge>可随时修改</Badge>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Field label="终端产品名称"><input className="input" value={target.targetProductName} onChange={(event) => update({ targetProductName: event.target.value })} /></Field>
        <Field label="产品形态">
          <select className="input" value={target.targetProductForm} onChange={(event) => update({ targetProductForm: event.target.value })}>
            <option>果冻</option><option>饮料</option><option>软糖</option><option>酸奶</option><option>营养粉</option>
          </select>
        </Field>
        <Field label="目标应用方向"><input className="input" value={target.applicationDirection} onChange={(event) => update({ applicationDirection: event.target.value })} /></Field>
        <Field label="目标规模">
          <select className="input" value={target.targetScale} onChange={(event) => update({ targetScale: event.target.value })}>
            <option>小试 20 升</option><option>中试 200 升</option><option>放大 1000 升</option>
          </select>
        </Field>
        <Field label="需要的 AKK 相关产物">
          <select className="input" value={target.akkProductType} onChange={(event) => update({ akkProductType: event.target.value })}>
            <option>AKK 后生元</option><option>AKK 活菌体</option><option>AKK 代谢产物</option><option>AKK 与菌藻协同产物</option>
          </select>
        </Field>
        <Field label="目标产物含量"><input className="input" value={target.targetContent ?? ""} onChange={(event) => update({ targetContent: event.target.value })} /></Field>
        <Field label="活性保留目标"><input className="input" value={target.activityTarget ?? ""} onChange={(event) => update({ activityTarget: event.target.value })} /></Field>
        <Field label="稳定性目标"><input className="input" value={target.stabilityTarget ?? ""} onChange={(event) => update({ stabilityTarget: event.target.value })} /></Field>
        <Field label="成本上限"><input className="input" value={target.costLimit ?? ""} onChange={(event) => update({ costLimit: event.target.value })} /></Field>
        <Field label="优化策略">
          <select className="input" value={target.optimizationStrategy} onChange={(event) => update({ optimizationStrategy: event.target.value })}>
            <option>综合平衡</option><option>产出优先</option><option>稳定优先</option><option>快速验证</option>
          </select>
        </Field>
      </div>
      <Field label="产品限制">
        <input className="input" value={target.constraints.join("、")} onChange={(event) => update({ constraints: event.target.value.split(/[、，,]/).map((item) => item.trim()).filter(Boolean) })} />
      </Field>
      <label className="mt-4 flex items-center gap-2 text-sm text-slate-700">
        <input checked={target.allowCoCulture} onChange={(event) => update({ allowCoCulture: event.target.checked })} type="checkbox" />
        允许共培养或协同培养窗口
      </label>
      <div className="mt-5 flex justify-end"><Button onClick={onNext}>继续录入产线现状</Button></div>
    </Card>
  );
}

function LineStage({
  lines,
  selectedLine,
  target,
  update,
  selectLine,
  onBack,
  onGenerate,
  isGenerating,
  hasGenerated,
}: {
  lines: ProcessProductionLine[];
  selectedLine: ProcessProductionLine;
  target: ProcessTaskRequest;
  update: (patch: Partial<ProcessTaskRequest>) => void;
  selectLine: (line: ProcessProductionLine) => void;
  onBack: () => void;
  onGenerate: () => void;
  isGenerating: boolean;
  hasGenerated: boolean;
}) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <CardTitle>第二步：产线现状与可调整空间</CardTitle>
          <p className="mt-2 text-sm leading-6 text-slate-600">这些数值不是展示用，修改后会进入后端评分，影响方案分数、置信度和响应面曲线。</p>
        </div>
        <Badge tone={hasGenerated ? "success" : "warning"}>{hasGenerated ? "修改后自动重算" : "等待首次生成"}</Badge>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-3">
          {lines.map((line) => (
            <button
              className={`w-full rounded-lg border p-3 text-left ${line.lineId === selectedLine.lineId ? "border-emerald-600 bg-emerald-50" : "border-border bg-white"}`}
              key={line.lineId}
              onClick={() => selectLine(line)}
              type="button"
            >
              <div className="text-sm font-semibold text-slate-950">{line.lineName}</div>
              <div className="mt-1 text-xs text-slate-500">{line.equipmentType} / {line.workingVolume}</div>
              <div className="mt-2 text-xs text-emerald-700">基础可执行性 {line.feasibilityScore}/100</div>
            </button>
          ))}
        </div>
        <div className="rounded-lg border border-border bg-slate-50 p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <NumberField label="当前体积 L" value={target.currentVolumeL ?? 0} onChange={(value) => update({ currentVolumeL: value })} />
            <NumberField label="当前温度 ℃" value={target.currentTemperature ?? 36} onChange={(value) => update({ currentTemperature: value })} />
            <NumberField label="当前 pH" value={target.currentPh ?? 6.8} onChange={(value) => update({ currentPh: value })} />
            <NumberField label="当前搅拌 rpm" value={target.currentAgitationRpm ?? 160} onChange={(value) => update({ currentAgitationRpm: value })} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Field label="检测能力"><input className="input" value={target.sensorCapability ?? ""} onChange={(event) => update({ sensorCapability: event.target.value })} /></Field>
            <Field label="后处理能力"><input className="input" value={target.downstreamCapability ?? ""} onChange={(event) => update({ downstreamCapability: event.target.value })} /></Field>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <InfoBox title="设备能力">
              温度 {selectedLine.temperatureRange.min}-{selectedLine.temperatureRange.max}℃；pH {selectedLine.phRange.min}-{selectedLine.phRange.max}；搅拌 {selectedLine.agitationRange.min}-{selectedLine.agitationRange.max} rpm。
            </InfoBox>
            <InfoBox title="模型会检查">
              温度、pH、搅拌、体积、传感器和后处理能力都会影响方案风险、可执行性与置信度。
            </InfoBox>
          </div>
        </div>
      </div>
      <div className="mt-5 flex justify-end gap-3">
        <Button variant="secondary" onClick={onBack}>返回修改目标产品</Button>
        <Button disabled={isGenerating} onClick={onGenerate}>{isGenerating ? "生成中..." : hasGenerated ? "重新生成方案" : "生成具体方案"}</Button>
      </div>
    </Card>
  );
}

function ExploreStage({
  task,
  target,
  selectedPlan,
  selectedPlanId,
  onBackTarget,
  onBackLine,
  onSelectPlan,
  onNext,
}: {
  task: GeneratedProcessTask;
  target: ProcessTaskRequest;
  selectedPlan: ProcessCandidatePlan;
  selectedPlanId: string;
  onBackTarget: () => void;
  onBackLine: () => void;
  onSelectPlan: (planId: string) => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>第三步：三个候选方案与具体数值</CardTitle>
            <p className="mt-2 text-sm leading-6 text-slate-600">切换方案会同步参数窗口、评分条和曲线落点；返回前两步修改输入后会自动重算。</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onBackTarget}>改目标产品</Button>
            <Button variant="secondary" onClick={onBackLine}>改产线现状</Button>
          </div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          {task.candidatePlans.map((plan) => (
            <button
              className={`rounded-lg border p-4 text-left ${plan.planId === selectedPlanId ? "border-emerald-600 bg-emerald-50" : "border-border bg-white"}`}
              key={plan.planId}
              onClick={() => onSelectPlan(plan.planId)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="font-semibold text-slate-950">{plan.displayName}</div>
                <div className="text-2xl font-bold text-emerald-700">{plan.scoreBreakdown.overallScore}</div>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-600">{plan.summary}</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
                <span>产物 {plan.scoreBreakdown.yieldScore}</span>
                <span>活性 {plan.scoreBreakdown.activityScore}</span>
                <span>风险 {plan.scoreBreakdown.riskScore}</span>
                <span>置信度 {plan.scoreBreakdown.confidenceScore}</span>
              </div>
            </button>
          ))}
        </div>
      </Card>
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <ResponseSurface
          currentPh={target.currentPh ?? 6.8}
          currentTemperature={target.currentTemperature ?? 36}
          selectedPlan={selectedPlan}
          surface={task.surface}
        />
        <Card>
          <CardTitle>{selectedPlan.displayName}参数窗口</CardTitle>
          <div className="mt-4 grid gap-3 text-sm">
            <Parameter label="温度" value={`${selectedPlan.recommendedParameters.temperature.min}-${selectedPlan.recommendedParameters.temperature.max}℃`} />
            <Parameter label="pH" value={`${selectedPlan.recommendedParameters.ph.min}-${selectedPlan.recommendedParameters.ph.max}`} />
            <Parameter label="培养时间" value={`${selectedPlan.recommendedParameters.cultureTimeHours.min}-${selectedPlan.recommendedParameters.cultureTimeHours.max}小时`} />
            <Parameter label="搅拌" value={`${selectedPlan.recommendedParameters.agitationRpm.min}-${selectedPlan.recommendedParameters.agitationRpm.max} rpm`} />
            <Parameter label="接种比例" value={selectedPlan.recommendedParameters.inoculationRatio} />
            <Parameter label="共培养比例" value={selectedPlan.recommendedParameters.coCultureRatio ?? "不启用"} />
          </div>
          <div className="mt-5 space-y-3">
            <MetricBar label="目标产物" value={selectedPlan.scoreBreakdown.yieldScore} />
            <MetricBar label="活性保留" value={selectedPlan.scoreBreakdown.activityScore} />
            <MetricBar label="稳定性" value={selectedPlan.scoreBreakdown.stabilityScore} />
            <MetricBar label="成本友好" value={selectedPlan.scoreBreakdown.costScore} />
            <MetricBar label="风险控制" value={selectedPlan.scoreBreakdown.riskScore} />
          </div>
          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-semibold text-slate-900">模型解释</div>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-5 text-slate-600">
              {selectedPlan.explanation.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
          <div className="mt-5">
            <Button onClick={onNext}>生成状态建议书</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

function ReportStage({
  task,
  selectedPlan,
  feedbackSaved,
  onBackExplore,
  onFeedbackSubmit,
}: {
  task: GeneratedProcessTask;
  selectedPlan: ProcessCandidatePlan;
  feedbackSaved: boolean;
  onBackExplore: () => void;
  onFeedbackSubmit: (formData: FormData) => void;
}) {
  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Badge tone="success">研发实验建议</Badge>
            <h2 className="mt-3 text-xl font-semibold text-slate-950">{task.report.title}</h2>
          </div>
          <Button variant="secondary" onClick={onBackExplore}>返回调整方案</Button>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">{task.disclaimer}</p>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <ListBlock title="推荐产线状态" items={task.report.parameterWindows} />
          <ListBlock title="预期效果" items={task.report.predictedOutcomes} />
          <ListBlock title="风险控制" items={task.report.riskControls} />
          <ListBlock title="必须验证的实验指标" items={task.report.validationPlan} />
        </div>
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">{task.report.nextStepSuggestion}</div>
      </Card>
      <Card>
        <CardTitle>实验回填</CardTitle>
        <form action={onFeedbackSubmit} className="mt-4 grid gap-4 md:grid-cols-2">
          <Field label="实际目标产物"><input className="input" name="actualYield" placeholder="例如：有效成分 21.3 g/批" /></Field>
          <Field label="实际活性"><input className="input" name="actualActivity" placeholder="例如：保留率 84%" /></Field>
          <Field label="设备异常"><input className="input" name="equipmentAbnormalities" placeholder="无 / pH 波动 / 搅拌异常" /></Field>
          <Field label="实验结论"><input className="input" name="conclusion" defaultValue={`${selectedPlan.displayName}等待复盘`} /></Field>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input name="contaminationObserved" type="checkbox" />
            观察到污染风险
          </label>
          <Field label="备注"><textarea className="input min-h-24" name="notes" placeholder="记录失败原因、感官问题、稳定性变化等" /></Field>
          <div className="md:col-span-2"><Button type="submit">保存回填记录</Button>{feedbackSaved ? <span className="ml-3 text-sm text-emerald-700">已保存</span> : null}</div>
        </form>
      </Card>
    </div>
  );
}

function TaskSummary({
  target,
  selectedLine,
  selectedPlan,
  task,
  llmStatus,
  simulationLlmStatus,
}: {
  target: ProcessTaskRequest;
  selectedLine?: ProcessProductionLine;
  selectedPlan?: ProcessCandidatePlan;
  task?: GeneratedProcessTask;
  llmStatus?: LlmStatus;
  simulationLlmStatus?: SimulationLlmStatus;
}) {
  const cloudReady = Boolean(simulationLlmStatus?.enabled && simulationLlmStatus.apiKeyConfigured);
  const localReady = Boolean(llmStatus?.enabled && llmStatus.available);
  return (
    <aside className="sticky top-6 self-start rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-950">任务摘要</h2>
      <dl className="mt-4 space-y-4 text-sm">
        <SummaryItem label="终端产品" value={`${target.targetProductName} / ${target.targetProductForm}`} />
        <SummaryItem label="目标产物" value={`${target.akkProductType}；${target.targetContent ?? ""}`} />
        <SummaryItem label="产线现状" value={selectedLine ? `${selectedLine.lineName}；${target.currentVolumeL ?? "-"} L` : "未选择"} />
        <SummaryItem label="当前方案" value={selectedPlan ? `${selectedPlan.displayName}；${selectedPlan.scoreBreakdown.overallScore}/100` : "尚未生成"} />
        <SummaryItem label="建议书" value={task ? task.report.title : "待生成"} />
      </dl>
      <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs leading-5 text-emerald-950">
        当前结果为研发实验建议。真实实验数据回填后，可继续训练更可靠的数学模型。
      </div>
      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
        <div className="font-semibold text-slate-950">增强推理接口</div>
        {cloudReady ? (
          <div>云端接口密钥已配置，模型：{simulationLlmStatus?.model}。</div>
        ) : localReady ? (
          <div>本地推理服务已连接，模型：{llmStatus?.model}。</div>
        ) : (
          <div>未接入增强推理服务。配置本地环境变量并重启后，可启用解释与建议增强。</div>
        )}
      </div>
    </aside>
  );
}

function Field({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <label className="block text-xs font-medium text-slate-600">
      {label}
      <div className="mt-2">{children}</div>
    </label>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <Field label={label}>
      <input className="input" type="number" value={Number.isFinite(value) ? value : 0} onChange={(event) => onChange(Number(event.target.value))} />
    </Field>
  );
}

function InfoBox({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs leading-5 text-slate-600">
      <div className="mb-1 font-semibold text-slate-900">{title}</div>
      {children}
    </div>
  );
}

function Parameter({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-950">{value}</span>
    </div>
  );
}

function MetricBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-600"><span>{label}</span><span>{value}/100</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-600" style={{ width: `${clamp(value, 0, 100)}%` }} /></div>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-600">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium leading-5 text-slate-950">{value}</dd>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}
