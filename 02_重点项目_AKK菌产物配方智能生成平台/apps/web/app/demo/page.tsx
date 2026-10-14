import Link from "next/link";

export default function DemoPage() {
  return <main className="mx-auto max-w-4xl">
    <section className="rounded-2xl border border-[#dce4de] bg-white p-7 shadow-[0_20px_60px_rgba(28,55,43,0.06)] sm:p-10">
      <p className="text-xs font-semibold tracking-[0.14em] text-[#397b5d]">隔离示例入口</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-950">从实验归档开始体验完整流程</h1>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-600">旧版单场景演示已迁移到统一实验工作区。现在可以从实验归档查看状态，也可以建立隔离示例，依次体验数据整理、仿真模拟、工艺优化和报告归档。</p>
      <div className="mt-7 grid gap-3 sm:grid-cols-3">
        <Link className="rounded-xl border border-[#cbd8d0] bg-[#f5f9f6] p-4 transition hover:border-[#7ca08d]" href="/"><b className="text-sm text-slate-900">查看实验归档</b><p className="mt-2 text-xs leading-5 text-slate-500">从当前实验状态和可靠性开始。</p></Link>
        <Link className="rounded-xl bg-[#174333] p-4 text-white transition hover:bg-[#205a45]" href="/experiments/new"><b className="text-sm">新建实验</b><p className="mt-2 text-xs leading-5 text-emerald-50/75">有数据或无数据都可以建立档案。</p></Link>
        <Link className="rounded-xl border border-[#cbd8d0] bg-white p-4 transition hover:border-[#7ca08d]" href="/knowledge-assets"><b className="text-sm text-slate-900">查看企业规律</b><p className="mt-2 text-xs leading-5 text-slate-500">管理已审核、可追溯的研发资产。</p></Link>
      </div>
      <div className="mt-7 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-900">隔离示例仅用于体验页面流程，不代表真实测量、正式模型准入或设备控制结果。</div>
    </section>
  </main>;
}
