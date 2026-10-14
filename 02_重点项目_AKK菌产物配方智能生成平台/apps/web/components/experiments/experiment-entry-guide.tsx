import type { DataCollectionLocalizationRun, ExperimentWorkspaceOverview } from "@/lib/schemas";

export function ExperimentEntryGuide({
  overview,
  intakeRun = null,
}: {
  overview: ExperimentWorkspaceOverview;
  intakeRun?: DataCollectionLocalizationRun | null;
}) {
  const confirmed = intakeRun?.status === "confirmed";
  const hasRun = intakeRun !== null;
  const items = [
    {
      label: "当前任务",
      value: !hasRun ? "接入第一批实验数据" : confirmed ? "清洗并对齐时间轴" : "复核字段与单位映射",
    },
    {
      label: "前置证据",
      value: !hasRun
        ? `实验目标已建立 · ${overview.targetMetrics.length} 项目标指标`
        : `${intakeRun.transformationCount} 个字段 · 原始资产 ${intakeRun.assetId}`,
    },
    {
      label: "可执行动作",
      value: !hasRun ? "上传 CSV / TXT 并开始数据识别" : confirmed ? "创建清洗对齐运行" : "逐项确认标准字段、单位与换算证据",
    },
    {
      label: "下一步",
      value: !hasRun ? "人工确认字段与单位" : confirmed ? "生成数据集快照并进入特征工程" : "签署映射后开放数据清洗",
    },
  ];

  return <section className="rounded-2xl border border-[#cfdcd4] bg-[#f8faf8] p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><div className="text-xs font-semibold tracking-[0.14em] text-[#397b5d]">研发流程引导</div><h1 className="mt-1 text-xl font-semibold text-slate-950">从当前证据继续实验</h1></div>
      <div className="flex gap-2">
        <span className="rounded-full bg-white px-3 py-1 text-xs text-slate-600 ring-1 ring-[#dce4de]">{overview.sourceType === "enterprise" ? "企业实验" : overview.sourceType === "blank" ? "空白档案" : "示例演示"}</span>
        {overview.sourceType === "sample" ? <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-900">{overview.sampleTemplateVersion}</span> : null}
      </div>
    </div>
    <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">{items.map((item) => <div className="rounded-xl border border-[#e0e7e2] bg-white p-4" key={item.label}><div className="text-[10px] font-semibold tracking-[0.12em] text-slate-400">{item.label}</div><div className="mt-2 text-sm font-medium leading-6 text-slate-800">{item.value}</div></div>)}</div>
    {overview.sourceType === "sample" ? <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">这是隔离的行业示例。所有字段确认、建模和仿真步骤仍需人工主动推进；结果不能登记为真实测量、晋升企业正式模型或用于设备控制。</p> : null}
  </section>;
}
