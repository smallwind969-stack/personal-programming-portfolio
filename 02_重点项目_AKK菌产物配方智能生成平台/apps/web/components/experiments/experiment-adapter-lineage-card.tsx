import Link from "next/link";

import type { DataCollectionLocalizationRun, ExperimentWorkspaceOverview } from "@/lib/schemas";

export function ExperimentAdapterLineageCard({ overview, intakeRun = null }: { overview: ExperimentWorkspaceOverview; intakeRun?: DataCollectionLocalizationRun | null }) {
  const pack = overview.adapterPack;
  const intakeConfirmed = intakeRun?.status === "confirmed";
  const nodes = [
    { label: "设备规则锁定", state: pack ? "已完成" : "待配置", detail: pack ? `${pack.enterpriseKey} / ${pack.deviceType} / v${pack.packVersion}` : "未选择设备适配包，可从模型资产中创建" },
    { label: "字段识别与单位换算", state: intakeConfirmed ? "已完成" : intakeRun ? "待确认" : "等待数据", detail: intakeRun ? `已生成 ${intakeRun.transformationCount} 项转换证据` : "上传原始设备文件后，系统将自动生成并展示转换证据" },
    { label: "人工确认", state: intakeConfirmed ? "已完成" : "等待上游", detail: intakeConfirmed ? "字段与单位已由研发人员确认，可以生成受控数据快照" : "确认字段、单位、时间轴和异常处理后，才允许生成训练快照" },
  ];
  return (
    <section className="rounded-2xl border border-[#dce4de] bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><div className="text-xs font-semibold tracking-[0.14em] text-[#397b5d]">数据接入血缘</div><h2 className="mt-1 text-lg font-semibold text-slate-950">首次实验准备进程</h2></div>
        {!pack && <Link className="rounded-lg border border-[#cad8cf] px-3 py-2 text-xs text-[#174333]" href="/model-assets">配置模型资产</Link>}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {nodes.map((node, index) => <div className="rounded-xl bg-[#f4f7f4] p-4" key={node.label}><div className="flex items-center justify-between gap-2"><span className="text-sm font-medium text-slate-900">{index + 1}. {node.label}</span><span className={`rounded px-2 py-1 text-[10px] ${node.state === "已完成" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{node.state}</span></div><p className="mt-3 text-xs leading-5 text-slate-500">{node.detail}</p></div>)}
      </div>
      {pack && <div className="mt-3 break-all rounded-lg border border-[#e0e7e2] px-3 py-2 font-mono text-[10px] text-slate-500">适配内容指纹：{pack.contentHash}</div>}
    </section>
  );
}

export function WaitingAnalysisAgentCenter({ experimentId }: { experimentId: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-[#aebfb4] bg-[#f6f8f6] p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><div className="text-xs font-semibold tracking-[0.14em] text-amber-700">数据分析 · 等待输入</div><h2 className="mt-2 text-xl font-semibold text-slate-950">尚未启动算法进程</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">上传至少一个实验数据文件后，系统才会开始字段识别、单位换算、时间轴对齐和建模。当前不会用虚构数据推进模型。</p></div>
        <Link className="rounded-xl bg-[#174333] px-5 py-3 text-sm font-medium text-white" href={`/experiments/${experimentId}`}>进入实验工作区上传数据</Link>
      </div>
      <div className="mt-5 grid gap-2 sm:grid-cols-4">{["原始数据接收", "字段与单位识别", "时间轴对齐", "人工确认"].map((label, index) => <div className="rounded-lg bg-white px-3 py-3 text-xs text-slate-500" key={label}><span className="mr-2 font-mono text-slate-300">0{index + 1}</span>{label}<div className="mt-2 text-[10px] text-amber-700">等待上游</div></div>)}</div>
    </section>
  );
}
