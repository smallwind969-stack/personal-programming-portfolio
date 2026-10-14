import { ProcessCandidatePlan, ProcessSurface } from "@/lib/schemas";

function axisRange(values: number[]) {
  return { min: Math.min(...values), max: Math.max(...values) };
}

function toPercent(value: number, min: number, max: number) {
  if (max === min) return 50;
  return ((value - min) / (max - min)) * 100;
}

function midpoint(min: number, max: number) {
  return (min + max) / 2;
}

export function ResponseSurface({
  currentPh,
  currentTemperature,
  selectedPlan,
  surface,
}: {
  currentPh: number;
  currentTemperature: number;
  selectedPlan: ProcessCandidatePlan;
  surface: ProcessSurface;
}) {
  const temperatures = surface.points.map((point) => point.temperature);
  const phValues = surface.points.map((point) => point.ph);
  const tempRange = axisRange(temperatures);
  const phRange = axisRange(phValues);
  const bestPoint = surface.points.reduce((best, point) => (point.score > best.score ? point : best), surface.points[0]);
  const selectedTemperature = midpoint(selectedPlan.recommendedParameters.temperature.min, selectedPlan.recommendedParameters.temperature.max);
  const selectedPh = midpoint(selectedPlan.recommendedParameters.ph.min, selectedPlan.recommendedParameters.ph.max);

  const bestLeft = toPercent(bestPoint.temperature, tempRange.min, tempRange.max);
  const bestTop = 100 - toPercent(bestPoint.ph, phRange.min, phRange.max);
  const currentLeft = toPercent(currentTemperature, tempRange.min, tempRange.max);
  const currentTop = 100 - toPercent(currentPh, phRange.min, phRange.max);
  const selectedLeft = toPercent(selectedTemperature, tempRange.min, tempRange.max);
  const selectedTop = 100 - toPercent(selectedPh, phRange.min, phRange.max);

  const tempTicks = [tempRange.min, 35, 36, 37, 38, tempRange.max].filter(
    (value, index, arr) => value >= tempRange.min && value <= tempRange.max && arr.indexOf(value) === index,
  );
  const phTicks = [phRange.max, 7.4, 7.2, 7.0, 6.8, 6.6, 6.4, phRange.min].filter(
    (value, index, arr) => value >= phRange.min && value <= phRange.max && arr.indexOf(value) === index,
  );

  return (
    <div className="rounded-lg border border-slate-200 bg-[#0b1d19] p-4 text-white">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">响应面：{surface.xAxisLabel} × {surface.yAxisLabel} × {surface.zAxisLabel}</div>
          <div className="mt-1 text-xs leading-5 text-slate-300">
            白点为当前产线状态，黄点为理论最佳点，绿点为所选方案。颜色越亮，综合评分越高。
          </div>
        </div>
        <div className="rounded-md border border-white/15 px-2 py-1 text-xs text-slate-200">实时响应面</div>
      </div>

      <div className="mt-5">
        <div className="grid grid-cols-[52px_1fr] gap-3">
          <div className="relative h-[330px]">
            <div className="absolute left-0 top-0 flex h-full flex-col justify-between text-[11px] text-slate-300">
              {phTicks.map((ph) => <span key={ph}>pH {Number.isInteger(ph) ? ph : ph.toFixed(1)}</span>)}
            </div>
            <div className="absolute bottom-12 left-6 origin-left -rotate-90 text-xs text-slate-300">pH {phRange.min} 到 {phRange.max}</div>
          </div>

          <div>
            <div className="relative h-[330px] overflow-hidden rounded-lg border border-white/15 bg-slate-900">
              <div
                className="absolute inset-0"
                style={{
                  background:
                    "radial-gradient(circle at 58% 43%, rgba(255,232,93,0.98) 0%, rgba(246,175,58,0.94) 15%, rgba(75,200,151,0.82) 29%, rgba(47,136,122,0.72) 44%, rgba(43,93,143,0.78) 62%, rgba(30,47,78,0.96) 100%)",
                }}
              />
              <div
                className="absolute inset-0 opacity-35"
                style={{
                  backgroundImage:
                    "linear-gradient(rgba(255,255,255,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.18) 1px, transparent 1px)",
                  backgroundSize: "14.285% 16.666%",
                }}
              />
              <div
                className="absolute right-0 top-0 h-full w-[24%] opacity-55"
                style={{
                  background:
                    "repeating-linear-gradient(45deg, rgba(255,108,108,.34) 0 10px, rgba(255,108,108,.08) 10px 20px)",
                }}
              />

              <Marker label="当前产线" left={currentLeft} top={currentTop} tone="current" />
              <Marker label="理论最佳" left={bestLeft} top={bestTop} tone="best" />
              <Marker label="所选方案" left={selectedLeft} top={selectedTop} tone="selected" />
            </div>

            <div className="mt-2 flex justify-between px-1 text-[11px] text-slate-300">
              {tempTicks.map((temperature) => (
                <span key={temperature}>{Number.isInteger(temperature) ? temperature : temperature.toFixed(1)}℃</span>
              ))}
            </div>
            <div className="mt-2 text-center text-xs text-slate-300">温度从 {tempRange.min}℃ 到 {tempRange.max}℃</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-4 text-[11px] text-slate-300">
          <LegendDot tone="current" label={`当前产线：${currentTemperature}℃ / pH ${currentPh}`} />
          <LegendDot tone="best" label={`理论最佳：${bestPoint.temperature}℃ / pH ${bestPoint.ph} / ${bestPoint.score} 分`} />
          <LegendDot tone="selected" label={`所选方案：${selectedTemperature.toFixed(1)}℃ / pH ${selectedPh.toFixed(2)}`} />
          <span>右侧斜纹区为风险升高区。</span>
        </div>
      </div>
    </div>
  );
}

function Marker({ left, top, tone, label }: { left: number; top: number; tone: "current" | "best" | "selected"; label: string }) {
  const color = {
    current: "bg-white",
    best: "bg-yellow-300",
    selected: "bg-emerald-300",
  }[tone];

  return (
    <span
      className={`absolute z-10 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white ${color} shadow-[0_0_0_5px_rgba(0,0,0,.24)]`}
      style={{ left: `${Math.max(0, Math.min(100, left))}%`, top: `${Math.max(0, Math.min(100, top))}%` }}
      title={label}
    />
  );
}

function LegendDot({ tone, label }: { tone: "current" | "best" | "selected"; label: string }) {
  const color = {
    current: "bg-white",
    best: "bg-yellow-300",
    selected: "bg-emerald-300",
  }[tone];
  return <span className="inline-flex items-center gap-1.5"><i className={`h-2.5 w-2.5 rounded-full ${color}`} />{label}</span>;
}
