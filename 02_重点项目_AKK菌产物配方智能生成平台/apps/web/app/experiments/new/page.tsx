"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { experimentCreateOptions } from "@/components/experiments/experiment-create-options";
import { createExperimentWorkspace, createSampleExperimentWorkspace, getDeviceAdapterPacks } from "@/lib/api";
import type { DeviceAdapterPack, ExperimentCreateRequest } from "@/lib/schemas";

type CreateMode = "enterprise" | "blank";

export default function NewExperimentPage() {
  const router = useRouter();
  const [mode, setMode] = useState<CreateMode>("enterprise");
  const [packs, setPacks] = useState<DeviceAdapterPack[]>([]);
  const [loadingPacks, setLoadingPacks] = useState(true);
  const [savingAction, setSavingAction] = useState<"enterprise" | "blank" | "sample" | null>(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "", batchCode: "", targetProduct: "", targetMetrics: "", objective: "",
    enterpriseKey: "", deviceType: "", packVersion: "",
    industry: "", processType: "", lineName: "", materialSystem: "", criticalParameters: "",
  });

  useEffect(() => {
    getDeviceAdapterPacks()
      .then(setPacks)
      .catch(() => setError("暂时无法读取设备适配资产，仍可不选择设备并创建实验。"))
      .finally(() => setLoadingPacks(false));
  }, []);

  const enterprises = useMemo(() => [...new Set(packs.map((pack) => pack.enterpriseKey))], [packs]);
  const deviceTypes = useMemo(() => [...new Set(packs.filter((pack) => pack.enterpriseKey === form.enterpriseKey).map((pack) => pack.deviceType))], [packs, form.enterpriseKey]);
  const versions = useMemo(() => packs.filter((pack) => pack.enterpriseKey === form.enterpriseKey && pack.deviceType === form.deviceType), [packs, form.enterpriseKey, form.deviceType]);
  const selectedPack = versions.find((pack) => pack.packVersion === form.packVersion);

  async function createSample() {
    setSavingAction("sample");
    setError("");
    try {
      const result = await createSampleExperimentWorkspace({ templateKey: "algae-culture" });
      router.push(`/experiments/${result.overview.experimentId}/analysis`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "示例实验创建失败，请稍后重试。");
      setSavingAction(null);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSavingAction(mode);
    setError("");
    const payload: ExperimentCreateRequest = {
      sourceType: mode,
      name: form.name.trim(),
      batchCode: form.batchCode.trim() || null,
      targetProduct: form.targetProduct.trim(),
      targetMetrics: form.targetMetrics.split(/[，,、]/).map((item) => item.trim()).filter(Boolean),
      objective: form.objective.trim(),
      adapterPack: selectedPack ? {
        enterpriseKey: selectedPack.enterpriseKey,
        deviceType: selectedPack.deviceType,
        packVersion: selectedPack.packVersion,
      } : null,
      productionContext: {
        industry: form.industry.trim(),
        processType: form.processType.trim(),
        lineName: form.lineName.trim() || null,
        materialSystem: form.materialSystem.trim() || null,
        criticalParameters: form.criticalParameters.split(/[，,、]/).map((item) => item.trim()).filter(Boolean),
        parameterDefinitions: [],
      },
    };
    try {
      const created = await createExperimentWorkspace(payload);
      router.push(`/experiments/${created.experimentId}/analysis`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "实验创建失败，请检查填写内容。");
      setSavingAction(null);
    }
  }

  return <main className="mx-auto max-w-6xl">
    <Link className="text-sm text-slate-600 hover:text-[#174333]" href="/">← 返回实验归档</Link>
    <header className="mt-7 max-w-3xl">
      <div className="text-xs font-semibold tracking-[0.16em] text-[#397b5d]">数据分析 · 第一步</div>
      <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-slate-950">新建实验</h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">有真实设备数据时直接建立企业实验；暂时没有数据时，可以使用隔离的行业示例体验完整闭环，或先建立空白档案。</p>
    </header>

    <section className="mt-7 grid gap-3 lg:grid-cols-2">
      <button className={`rounded-2xl border p-5 text-left transition ${mode === "enterprise" ? "border-[#397b5d] bg-[#edf5f0] ring-2 ring-[#397b5d]/10" : "border-[#dce4de] bg-white hover:border-[#8dac9b]"}`} onClick={() => { setMode("enterprise"); setError(""); }} type="button">
        <div className="flex items-center justify-between"><span className="text-xs font-semibold text-[#2f7054]">推荐主入口</span><span className="rounded-full bg-[#174333] px-2.5 py-1 text-[10px] text-white">真实业务</span></div>
        <h2 className="mt-3 text-lg font-semibold text-slate-950">{experimentCreateOptions[0].title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{experimentCreateOptions[0].description}</p>
      </button>
      <div className="rounded-2xl border border-[#dce4de] bg-[#f7f9f7] p-5">
        <div className="text-xs font-semibold text-slate-500">暂时没有实验数据</div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <button className="rounded-xl border border-[#dce4de] bg-white p-4 text-left transition hover:border-[#8dac9b] disabled:opacity-60" disabled={savingAction !== null} onClick={createSample} type="button"><div className="font-semibold text-slate-900">{experimentCreateOptions[1].title}</div><p className="mt-2 text-xs leading-5 text-slate-500">{experimentCreateOptions[1].description}</p><div className="mt-3 text-xs font-medium text-[#174333]">{savingAction === "sample" ? "正在创建示例…" : `${experimentCreateOptions[1].actionLabel} →`}</div></button>
          <button className={`rounded-xl border bg-white p-4 text-left transition hover:border-[#8dac9b] ${mode === "blank" ? "border-[#397b5d] ring-2 ring-[#397b5d]/10" : "border-[#dce4de]"}`} onClick={() => { setMode("blank"); setError(""); }} type="button"><div className="font-semibold text-slate-900">{experimentCreateOptions[2].title}</div><p className="mt-2 text-xs leading-5 text-slate-500">{experimentCreateOptions[2].description}</p><div className="mt-3 text-xs font-medium text-[#174333]">{experimentCreateOptions[2].actionLabel} →</div></button>
        </div>
        <p className="mt-3 text-[10px] leading-5 text-amber-800">示例数据只用于学习研发闭环，不能作为真实测量、正式模型晋升或设备控制依据。</p>
      </div>
    </section>

    <form className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]" onSubmit={submit}>
      <section className="rounded-2xl border border-[#dce4de] bg-white p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold text-slate-950">实验基本信息</h2><span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">{mode === "enterprise" ? "企业实验" : "空白档案"}</span></div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <Field label="实验名称" value={form.name} placeholder="例如：高密度培养预实验" required onChange={(value) => setForm({ ...form, name: value })} />
          <Field label="批次信息" value={form.batchCode} placeholder="例如：B08（可稍后补充）" onChange={(value) => setForm({ ...form, batchCode: value })} />
          <Field label="目标产品或实验对象" value={form.targetProduct} placeholder="例如：菌藻培养产物" required onChange={(value) => setForm({ ...form, targetProduct: value })} />
          <Field label="目标指标" value={form.targetMetrics} placeholder="例如：OD600、活菌率、产率" required onChange={(value) => setForm({ ...form, targetMetrics: value })} />
          <Field label="所属产业" value={form.industry} placeholder="例如：生物制造、精细化工、食品加工" required onChange={(value) => setForm({ ...form, industry: value })} />
          <Field label="工艺类型" value={form.processType} placeholder="例如：发酵、混配、热处理、连续反应" required onChange={(value) => setForm({ ...form, processType: value })} />
          <Field label="产线或装置名称" value={form.lineName} placeholder="例如：中试线 C-02（可稍后补充）" onChange={(value) => setForm({ ...form, lineName: value })} />
          <Field label="物料体系" value={form.materialSystem} placeholder="例如：水性功能材料、培养基体系" onChange={(value) => setForm({ ...form, materialSystem: value })} />
          <label className="sm:col-span-2"><span className="mb-2 block text-sm font-medium text-slate-700">关键工艺参数</span><input className="h-10 w-full rounded-lg border border-[#d8e1db] px-3 text-sm outline-none focus:border-[#397b5d]" placeholder="用逗号分隔，例如：进料流量、温度、压力、黏度" value={form.criticalParameters} onChange={(event) => setForm({ ...form, criticalParameters: event.target.value })} /></label>
          <label className="sm:col-span-2"><span className="mb-2 block text-sm font-medium text-slate-700">实验目标</span><textarea className="min-h-32 w-full rounded-lg border border-[#d8e1db] px-3 py-2 text-sm outline-none focus:border-[#397b5d]" placeholder="说明希望解决的问题、变量范围和预期结果" required value={form.objective} onChange={(event) => setForm({ ...form, objective: event.target.value })} /></label>
        </div>
      </section>

      <aside className="space-y-4">
        <section className="rounded-2xl border border-[#dce4de] bg-[#173e31] p-5 text-white">
          <div className="text-xs text-emerald-100/70">可选 · 企业设备适配</div>
          <h2 className="mt-2 text-lg font-semibold">锁定数据接入规则</h2>
          <p className="mt-2 text-xs leading-5 text-emerald-50/70">锁定后，字段识别和单位换算会记录适配版本与内容指纹。</p>
          <div className="mt-4 space-y-3">
            <Select label="企业" value={form.enterpriseKey} disabled={loadingPacks} onChange={(value) => setForm({ ...form, enterpriseKey: value, deviceType: "", packVersion: "" })} options={enterprises} emptyLabel={loadingPacks ? "读取中…" : "暂不选择"} />
            <Select label="设备类型" value={form.deviceType} disabled={!form.enterpriseKey} onChange={(value) => setForm({ ...form, deviceType: value, packVersion: "" })} options={deviceTypes} emptyLabel="请选择设备" />
            <Select label="适配版本" value={form.packVersion} disabled={!form.deviceType} onChange={(value) => setForm({ ...form, packVersion: value })} options={versions.map((pack) => pack.packVersion)} emptyLabel="请选择版本" />
          </div>
          {selectedPack ? <div className="mt-4 rounded-xl bg-white/10 p-3 text-xs"><div>{selectedPack.entries.length} 条字段映射</div><div className="mt-1 break-all font-mono text-[10px] text-emerald-100/70">{selectedPack.contentHash}</div></div> : null}
          {!loadingPacks && packs.length === 0 ? <Link className="mt-4 inline-flex text-xs text-emerald-200 underline" href="/model-assets">先创建设备适配包</Link> : null}
        </section>
        <button className="h-11 w-full rounded-xl bg-[#174333] text-sm font-medium text-white disabled:opacity-50" disabled={savingAction !== null} type="submit">{savingAction === mode ? "正在创建并锁定血缘…" : mode === "enterprise" ? "创建企业实验并进入数据分析" : "建立空白档案"}</button>
        <p className="text-xs leading-5 text-slate-500">企业实验和空白档案都不会自动运行模型。上传数据并完成字段、单位和质量门禁后，才会开放数学建模。</p>
      </aside>
    </form>
    {error ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{error}</div> : null}
  </main>;
}

function Field({ label, value, placeholder, required = false, onChange }: { label: string; value: string; placeholder: string; required?: boolean; onChange: (value: string) => void }) {
  return <label><span className="mb-2 block text-sm font-medium text-slate-700">{label}</span><input className="h-10 w-full rounded-lg border border-[#d8e1db] px-3 text-sm outline-none focus:border-[#397b5d]" placeholder={placeholder} required={required} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function Select({ label, value, options, emptyLabel, disabled, onChange }: { label: string; value: string; options: string[]; emptyLabel: string; disabled: boolean; onChange: (value: string) => void }) {
  return <label className="block text-xs text-emerald-50/70">{label}<select className="mt-1 h-10 w-full rounded-lg border border-white/15 bg-white/10 px-3 text-sm text-white outline-none disabled:opacity-50" disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)}><option className="text-slate-900" value="">{emptyLabel}</option>{options.map((option) => <option className="text-slate-900" key={option} value={option}>{option}</option>)}</select></label>;
}
