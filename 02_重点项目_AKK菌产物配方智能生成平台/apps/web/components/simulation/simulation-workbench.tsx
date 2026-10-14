"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { getSimulationLlmStatus, getSimulationScenarios, predictSimulation } from "@/lib/api";
import {
  SimulationLlmStatus,
  SimulationPredictRequest,
  SimulationPredictResponse,
  SimulationScenario,
} from "@/lib/schemas";

const legacyCarbonSourceOptions = [
  { value: "BFP", label: "红毛藻多糖 BFP" },
  { value: "UBFP", label: "超高压改性 UBFP" },
  { value: "lambdaCarrageenan", label: "λ-卡拉胶" },
  { value: "iotaCarrageenan", label: "ι-卡拉胶" },
  { value: "PHP", label: "桔梗多糖 PHP" },
  { value: "agar", label: "琼胶" },
] as const;

const carbonSourceOptions = [
  { value: "BFP", label: "红毛藻多糖 BFP" },
  { value: "UBFP", label: "超高压改性红毛藻多糖 UBFP" },
  { value: "lambdaCarrageenan", label: "λ-卡拉胶" },
  { value: "iotaCarrageenan", label: "ι-卡拉胶" },
  { value: "fucoidan", label: "岩藻聚糖" },
  { value: "porphyraGlycoprotein", label: "紫菜糖蛋白" },
  { value: "PHP", label: "桔梗多糖 PHP" },
  { value: "agar", label: "琼胶" },
] as const;

const productFormatOptions = [
  { value: "culture-medium", label: "AKK 培养体系" },
  { value: "postbiotic-powder", label: "后生元冻干粉" },
  { value: "fish-ball", label: "凝胶食品基质" },
  { value: "encapsulated-bead", label: "包埋颗粒" },
] as const;

const defaultInput: SimulationPredictRequest = {
  targetProduct: "AKK 后生元冻干粉",
  productFormat: "postbiotic-powder",
  carbonSource: "BFP",
  carbonConcentration: 2,
  cultureHours: 60,
  temperatureC: 37,
  ph: 6.8,
  anaerobicScore: 0.92,
  pressureMpa: 120,
  stirringRpm: 150,
  pretreated: true,
  useLlmAdvisor: false,
  customParameters: {},
};

export function SimulationWorkbench() {
  const [input, setInput] = useState<SimulationPredictRequest>(defaultInput);
  const [result, setResult] = useState<SimulationPredictResponse | null>(null);
  const [scenarios, setScenarios] = useState<SimulationScenario[]>([]);
  const [llmStatus, setLlmStatus] = useState<SimulationLlmStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<SimulationPredictResponse[]>([]);

  useEffect(() => {
    getSimulationScenarios().then(setScenarios).catch(() => setScenarios([]));
    getSimulationLlmStatus().then(setLlmStatus).catch(() => setLlmStatus(null));
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setIsLoading(true);
      predictSimulation(input)
        .then((nextResult) => {
          setResult(nextResult);
          setError(null);
        })
        .catch((err) => setError(err instanceof Error ? err.message : "预测请求失败"))
        .finally(() => setIsLoading(false));
    }, 260);
    return () => window.clearTimeout(timer);
  }, [input]);

  const bestPoint = useMemo(() => {
    if (!result?.curve.length) return null;
    return result.curve.reduce((best, point) => (point.overallScore > best.overallScore ? point : best), result.curve[0]);
  }, [result]);

  function update<K extends keyof SimulationPredictRequest>(key: K, value: SimulationPredictRequest[K]) {
    setInput((current) => ({ ...current, [key]: value }));
  }

  function applyScenario(scenario: SimulationScenario) {
    setInput({
      targetProduct: scenario.targetProduct,
      productFormat: scenario.productFormat,
      carbonSource: scenario.carbonSource,
      carbonConcentration: scenario.carbonConcentration,
      cultureHours: scenario.cultureHours,
      temperatureC: scenario.temperatureC,
      ph: scenario.ph,
      anaerobicScore: scenario.anaerobicScore,
      pressureMpa: scenario.pressureMpa,
      stirringRpm: scenario.stirringRpm,
      pretreated: scenario.pretreated,
      useLlmAdvisor: input.useLlmAdvisor,
      customParameters: {},
    });
  }

  function saveSnapshot() {
    if (!result) return;
    setHistory((current) => [result, ...current].slice(0, 5));
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <section className="rounded-lg border border-emerald-900/10 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Badge tone="success">研发实验建议</Badge>
            <h1 className="mt-4 text-3xl font-semibold text-slate-950">AKK 论文模拟数据建模工作台</h1>
            <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-600">
              基于本地论文锚点、模拟增强数据和规则模型，预测 AKK 增殖、短链脂肪酸、分子量和屏障相关评分。当前结果用于研发设计，不作为真实生产指令。
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <StatusTile label="模型核心" value="规则 + 回归" />
            <StatusTile label="数据来源" value="论文模拟" />
            <StatusTile label="语义解释" value={llmStatus?.apiKeyConfigured ? "可用" : "未启用"} />
            <StatusTile label="控制边界" value="不下发产线" />
          </div>
        </div>
      </section>

      {error ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">后端暂不可用：{error}</div> : null}

      <div className="grid gap-5 xl:grid-cols-[410px_1fr_340px]">
        <Card className="space-y-5">
          <div className="flex items-center justify-between gap-3">
            <CardTitle>输入目标与产线状态</CardTitle>
            {isLoading ? <Badge>更新中</Badge> : <Badge tone="success">实时预测</Badge>}
          </div>
          <Field label="目标产品">
            <input className="input" value={input.targetProduct} onChange={(event) => update("targetProduct", event.target.value)} />
          </Field>
          <SelectField label="产品形态" value={input.productFormat} options={productFormatOptions} onChange={(value) => update("productFormat", value as SimulationPredictRequest["productFormat"])} />
          <SelectField label="核心碳源" value={input.carbonSource} options={carbonSourceOptions} onChange={(value) => update("carbonSource", value as SimulationPredictRequest["carbonSource"])} />
          <Slider label="碳源浓度" value={input.carbonConcentration} min={0} max={4} step={0.05} unit="g/L 或 %" onChange={(value) => update("carbonConcentration", value)} />
          <Slider label="培养时间" value={input.cultureHours} min={12} max={96} step={1} unit="小时" onChange={(value) => update("cultureHours", value)} />
          <Slider label="温度" value={input.temperatureC} min={25} max={45} step={0.1} unit="℃" onChange={(value) => update("temperatureC", value)} />
          <Slider label="pH" value={input.ph} min={5.5} max={8} step={0.01} unit="" onChange={(value) => update("ph", value)} />
          <Slider label="厌氧水平" value={input.anaerobicScore} min={0} max={1} step={0.01} unit="" onChange={(value) => update("anaerobicScore", value)} />
          <Slider label="压力" value={input.pressureMpa} min={0} max={420} step={1} unit="MPa" onChange={(value) => update("pressureMpa", value)} />
          <Slider label="搅拌" value={input.stirringRpm} min={0} max={300} step={1} unit="rpm" onChange={(value) => update("stirringRpm", value)} />
          <Toggle label="启用预处理/改性" checked={input.pretreated} onChange={(value) => update("pretreated", value)} />
          <Toggle label="启用语义解释" checked={input.useLlmAdvisor} onChange={(value) => update("useLlmAdvisor", value)} />
        </Card>

        <div className="space-y-5">
          <div className="grid gap-4 lg:grid-cols-4">
            <ScoreCard label="综合评分" value={result?.predictions.overallScore} suffix="/100" tone="dark" />
            <ScoreCard label="AKK 增殖" value={result?.predictions.akkGrowthScore} suffix="/100" />
            <ScoreCard label="短链脂肪酸" value={result?.predictions.scfaScore} suffix="/100" />
            <ScoreCard label="分子量" value={result?.predictions.molecularWeightKda} suffix="kDa" />
          </div>
          {result ? <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600"><span className="rounded bg-[#edf5f0] px-2 py-1 font-medium text-[#2f7054]">预测来源：{result.predictionSource === "promoted_model" ? "已晋升真实模型" : "规则仿真模型"}</span>{result.modelVersion ? <span className="font-mono">{result.modelVersion}</span> : null}{result.extrapolated ? <span className="rounded bg-amber-50 px-2 py-1 text-amber-800">超出训练范围</span> : null}</div> : null}
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle>剂量响应仿真曲线</CardTitle>
              {bestPoint ? <Badge tone="success">推荐浓度约 {bestPoint.carbonConcentration}</Badge> : null}
            </div>
            <CurveChart result={result} />
          </Card>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardTitle>推荐工艺窗口</CardTitle>
              {result ? <RecommendedSettings result={result} /> : <EmptyState />}
            </Card>
            <Card>
              <CardTitle>风险与验证</CardTitle>
              {result ? <RiskPanel result={result} /> : <EmptyState />}
            </Card>
          </div>
        </div>

        <aside className="space-y-5">
          <Card>
            <CardTitle>论文场景模板</CardTitle>
            <div className="mt-4 space-y-3">
              {scenarios.map((scenario) => (
                <button className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left text-sm hover:border-emerald-500 hover:bg-emerald-50" key={scenario.scenarioId} onClick={() => applyScenario(scenario)} type="button">
                  <div className="font-medium text-slate-950">{scenario.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{scenario.targetProduct}</div>
                </button>
              ))}
            </div>
          </Card>
          <Card>
            <CardTitle>建议书快照</CardTitle>
            <p className="mt-3 text-sm leading-6 text-slate-600">保存当前预测结果，方便对比不同碳源、pH、温度和搅拌策略。</p>
            <Button className="mt-4" onClick={saveSnapshot}>保存当前快照</Button>
            <div className="mt-4 space-y-2">
              {history.map((item, index) => (
                <div className="rounded-md bg-slate-50 p-2 text-xs text-slate-600" key={`${item.targetProduct}-${index}`}>
                  {item.targetProduct}：综合评分 {item.predictions.overallScore}/100
                </div>
              ))}
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-slate-200 bg-slate-50 p-3"><div className="text-xs text-slate-500">{label}</div><div className="mt-1 font-semibold text-slate-950">{value}</div></div>;
}

function ScoreCard({ label, value, suffix, tone = "light" }: { label: string; value?: number; suffix: string; tone?: "light" | "dark" }) {
  return <div className={`rounded-lg border p-4 ${tone === "dark" ? "border-emerald-800 bg-[#123c37] text-white" : "border-slate-200 bg-white text-slate-950"}`}><div className="text-xs opacity-70">{label}</div><div className="mt-2 text-2xl font-semibold">{value == null ? "-" : value}<span className="ml-1 text-sm opacity-70">{suffix}</span></div></div>;
}

function CurveChart({ result }: { result: SimulationPredictResponse | null }) {
  if (!result) return <EmptyState />;
  const max = Math.max(...result.curve.flatMap((point) => [point.akkGrowthScore, point.scfaScore, point.overallScore, 1]));
  return (
    <div className="mt-5 h-72 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex h-full items-end gap-2">
        {result.curve.map((point) => (
          <div className="flex flex-1 flex-col items-center justify-end gap-1" key={point.carbonConcentration}>
            <div className="flex h-52 w-full items-end justify-center gap-1">
              <i className="w-2 rounded-t bg-emerald-600" style={{ height: `${(point.akkGrowthScore / max) * 100}%` }} />
              <i className="w-2 rounded-t bg-sky-500" style={{ height: `${(point.scfaScore / max) * 100}%` }} />
              <i className="w-2 rounded-t bg-amber-500" style={{ height: `${(point.overallScore / max) * 100}%` }} />
            </div>
            <span className="text-[10px] text-slate-500">{point.carbonConcentration}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-4 text-xs text-slate-500"><span>绿色 AKK 增殖</span><span>蓝色 SCFAs</span><span>橙色 综合评分</span></div>
    </div>
  );
}

function RecommendedSettings({ result }: { result: SimulationPredictResponse }) {
  const s = result.recommendedSettings;
  return <div className="mt-4 space-y-2 text-sm"><Setting label="碳源浓度" value={`${s.carbonConcentration.min}-${s.carbonConcentration.max} ${s.carbonConcentration.unit}`} /><Setting label="温度" value={`${s.temperatureC.min}-${s.temperatureC.max}${s.temperatureC.unit}`} /><Setting label="pH" value={`${s.ph.min}-${s.ph.max}`} /><Setting label="厌氧下限" value={`${s.anaerobicScoreMinimum}`} /><Setting label="培养时间" value={`${s.cultureHours.min}-${s.cultureHours.max}${s.cultureHours.unit}`} /><Setting label="搅拌" value={`${s.stirringRpm.min}-${s.stirringRpm.max} rpm`} /></div>;
}

function RiskPanel({ result }: { result: SimulationPredictResponse }) {
  return <div className="mt-4 space-y-4"><List title="风险提示" items={result.risks} /><List title="验证指标" items={result.validationIndicators} />{result.llmAdvisor.advice ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-600">{result.llmAdvisor.advice}</div> : null}</div>;
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: readonly { value: string; label: string }[]; onChange: (value: string) => void }) {
  return <Field label={label}><select className="input" value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></Field>;
}

function Slider({ label, value, min, max, step, unit, onChange }: { label: string; value: number; min: number; max: number; step: number; unit: string; onChange: (value: number) => void }) {
  return <div><div className="flex justify-between text-xs font-medium text-slate-600"><span>{label}</span><span>{value} {unit}</span></div><input className="mt-2 w-full accent-emerald-700" type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /></div>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"><span>{label}</span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /></label>;
}

function Field({ children, label }: { children: React.ReactNode; label: string }) {
  return <label className="block text-xs font-medium text-slate-600">{label}<div className="mt-2">{children}</div></label>;
}

function Setting({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-500">{label}</span><span className="font-medium text-slate-950">{value}</span></div>;
}

function List({ title, items }: { title: string; items: string[] }) {
  return <div><h3 className="text-sm font-semibold text-slate-950">{title}</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-600">{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}

function EmptyState() {
  return <div className="mt-4 rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">等待预测结果</div>;
}
