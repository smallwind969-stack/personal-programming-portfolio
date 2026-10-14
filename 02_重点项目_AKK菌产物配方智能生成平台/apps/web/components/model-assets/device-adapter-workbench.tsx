"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { compareDeviceAdapterPacks, createDeviceAdapterPack } from "@/lib/api";
import type {
  DeviceAdapterPack, DeviceAdapterPackComparison, DeviceAdapterPackCreate,
} from "@/lib/schemas";

const PARAMETERS = ["temperatureC", "ph", "stirringRpm", "dissolvedOxygenPct", "flowRateLpm", "pressureKpa", "durationHours"];
type Entry = DeviceAdapterPackCreate["entries"][number];
const emptyEntry = (): Entry => ({
  sourceFieldAlias: "", standardField: "", simulationParameter: "temperatureC",
  sourceUnit: null, targetUnit: null, scale: 1, offset: 0,
});

export function DeviceAdapterWorkbench({ initialPacks }: { initialPacks: DeviceAdapterPack[] }) {
  const [packs, setPacks] = useState(initialPacks);
  const [selectedId, setSelectedId] = useState(initialPacks[0]?.packId ?? "");
  const [form, setForm] = useState<DeviceAdapterPackCreate>({
    enterpriseKey: "", deviceType: "", packVersion: "1.0.0", createdBy: "平台管理员",
    entries: [emptyEntry()],
  });
  const [baseVersion, setBaseVersion] = useState("");
  const [targetVersion, setTargetVersion] = useState("");
  const [comparison, setComparison] = useState<DeviceAdapterPackComparison | null>(null);
  const [message, setMessage] = useState("");
  const selected = packs.find((pack) => pack.packId === selectedId) ?? packs[0];
  const family = useMemo(
    () => packs.filter((pack) => selected && pack.enterpriseKey === selected.enterpriseKey && pack.deviceType === selected.deviceType),
    [packs, selected],
  );

  function updateEntry(index: number, patch: Partial<Entry>) {
    setForm((current) => ({
      ...current, entries: current.entries.map((entry, position) => position === index ? { ...entry, ...patch } : entry),
    }));
  }

  async function submit() {
    setMessage("正在校验并生成内容指纹…");
    try {
      const created = await createDeviceAdapterPack(form);
      setPacks((current) => [created, ...current.filter((pack) => pack.packId !== created.packId)]);
      setSelectedId(created.packId);
      setMessage(`适配包 ${created.packVersion} 已保存，可用于字段识别与数据定位。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "创建失败，请检查字段。");
    }
  }

  async function runComparison() {
    if (!selected || !baseVersion || !targetVersion) return;
    setMessage("正在比较两个版本…");
    try {
      setComparison(await compareDeviceAdapterPacks(
        selected.enterpriseKey, selected.deviceType, baseVersion, targetVersion,
      ));
      setMessage("版本差异已生成。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "比较失败。");
    }
  }

  return (
    <main className="min-h-[calc(100vh-7.5rem)] rounded-[1.25rem] border border-[#dce4de] bg-[#f8faf8] p-5 shadow-[0_24px_70px_rgba(28,55,43,0.08)] sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold tracking-[0.18em] text-[#397b5d]">企业适配中心</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-slate-950">模型资产</h1>
          <p className="mt-2 text-sm text-slate-500">管理设备字段、单位换算与仿真参数之间的可追溯映射。</p>
        </div>
        <Link className="rounded-lg border border-[#cad8cf] bg-white px-4 py-2 text-sm text-[#174333]" href="/">返回实验归档</Link>
      </div>

      <div className="mt-7 grid gap-5 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-[#dce4de] bg-white p-3">
          <div className="px-2 pb-3 text-xs font-medium text-slate-500">已登记适配包 · {packs.length}</div>
          <div className="space-y-2">
            {packs.length === 0 && <p className="rounded-xl bg-[#f3f6f3] p-4 text-sm text-slate-500">暂无资产，请创建首个设备适配包。</p>}
            {packs.map((pack) => (
              <button className={`w-full rounded-xl border p-3 text-left transition ${selected?.packId === pack.packId ? "border-[#397b5d] bg-[#eaf3ed]" : "border-transparent bg-[#f7f9f7] hover:border-[#cad8cf]"}`} key={pack.packId} onClick={() => { setSelectedId(pack.packId); setComparison(null); }}>
                <div className="font-medium text-slate-900">{pack.deviceType}</div>
                <div className="mt-1 text-xs text-slate-500">{pack.enterpriseKey} · v{pack.packVersion}</div>
                <div className="mt-2 font-mono text-[10px] text-slate-400">{pack.contentHash.slice(0, 20)}…</div>
              </button>
            ))}
          </div>
        </aside>

        <section className="min-w-0 space-y-5">
          {selected && (
            <article className="rounded-2xl border border-[#dce4de] bg-[#173e31] p-5 text-white">
              <div className="flex flex-wrap justify-between gap-4">
                <div><div className="text-xs text-emerald-100/70">当前资产</div><h2 className="mt-1 text-xl font-semibold">{selected.enterpriseKey} / {selected.deviceType}</h2></div>
                <div className="text-right"><div className="text-xs text-emerald-100/70">版本</div><div className="font-mono text-xl">v{selected.packVersion}</div></div>
              </div>
              <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {selected.entries.map((entry) => <div className="rounded-lg bg-white/8 px-3 py-2 text-xs" key={entry.sourceFieldAlias}><b>{entry.sourceFieldAlias}</b><span className="mx-2 text-emerald-200/60">→</span>{entry.simulationParameter}</div>)}
              </div>
            </article>
          )}

          <article className="rounded-2xl border border-[#dce4de] bg-white p-5">
            <h2 className="text-lg font-semibold text-slate-950">新建设备适配包</h2>
            <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2">
              {(["enterpriseKey", "deviceType", "packVersion", "createdBy"] as const).map((field) => (
                <label className="min-w-0 text-xs text-slate-500" key={field}>{({ enterpriseKey: "企业标识", deviceType: "设备类型", packVersion: "版本号", createdBy: "创建人" })[field]}
                  <input className="mt-1 h-10 min-w-0 w-full rounded-lg border border-[#dce4de] px-3 text-sm text-slate-900 outline-none focus:border-[#397b5d]" value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />
                </label>
              ))}
            </div>
            <div className="mt-4 space-y-3">
              {form.entries.map((entry, index) => (
                <div className="grid min-w-0 gap-2 rounded-xl bg-[#f4f7f4] p-3 md:grid-cols-2 xl:grid-cols-3" key={index}>
                  <input aria-label="原始字段" className="min-w-0 w-full rounded-lg border px-3 py-2 text-sm" placeholder="原始字段，如 Temp" value={entry.sourceFieldAlias} onChange={(e) => updateEntry(index, { sourceFieldAlias: e.target.value })} />
                  <input aria-label="标准字段" className="min-w-0 w-full rounded-lg border px-3 py-2 text-sm" placeholder="标准字段" value={entry.standardField} onChange={(e) => updateEntry(index, { standardField: e.target.value })} />
                  <select aria-label="仿真参数" className="min-w-0 w-full rounded-lg border px-2 py-2 text-sm" value={entry.simulationParameter} onChange={(e) => updateEntry(index, { simulationParameter: e.target.value })}>{PARAMETERS.map((value) => <option key={value}>{value}</option>)}</select>
                  <input aria-label="原单位" className="min-w-0 w-full rounded-lg border px-3 py-2 text-sm" placeholder="原单位" value={entry.sourceUnit ?? ""} onChange={(e) => updateEntry(index, { sourceUnit: e.target.value || null })} />
                  <input aria-label="目标单位" className="min-w-0 w-full rounded-lg border px-3 py-2 text-sm" placeholder="目标单位" value={entry.targetUnit ?? ""} onChange={(e) => updateEntry(index, { targetUnit: e.target.value || null })} />
                  <button className="rounded-lg border border-rose-200 text-sm text-rose-700" disabled={form.entries.length === 1} onClick={() => setForm({ ...form, entries: form.entries.filter((_, position) => position !== index) })}>删除此行</button>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <button className="rounded-lg border border-[#cad8cf] px-4 py-2 text-sm text-[#174333]" onClick={() => setForm({ ...form, entries: [...form.entries, emptyEntry()] })}>＋ 添加映射</button>
              <button className="rounded-lg bg-[#174333] px-5 py-2 text-sm font-medium text-white" onClick={submit}>保存适配包</button>
            </div>
          </article>

          {selected && family.length > 1 && (
            <article className="rounded-2xl border border-[#dce4de] bg-white p-5">
              <h2 className="text-lg font-semibold text-slate-950">版本差异审查</h2>
              <div className="mt-4 flex flex-wrap gap-3">
                <select className="rounded-lg border px-3 py-2 text-sm" value={baseVersion} onChange={(e) => setBaseVersion(e.target.value)}><option value="">基准版本</option>{family.map((pack) => <option key={pack.packVersion}>{pack.packVersion}</option>)}</select>
                <select className="rounded-lg border px-3 py-2 text-sm" value={targetVersion} onChange={(e) => setTargetVersion(e.target.value)}><option value="">目标版本</option>{family.map((pack) => <option key={pack.packVersion}>{pack.packVersion}</option>)}</select>
                <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-40" disabled={!baseVersion || !targetVersion || baseVersion === targetVersion} onClick={runComparison}>开始比较</button>
              </div>
              {comparison && <div className="mt-4 grid gap-3 sm:grid-cols-4">
                <DiffCard label="新增" value={comparison.added.length} tone="text-emerald-700" />
                <DiffCard label="删除" value={comparison.removed.length} tone="text-rose-700" />
                <DiffCard label="修改" value={comparison.changed.length} tone="text-amber-700" />
                <DiffCard label="未变化" value={comparison.unchangedCount} tone="text-slate-700" />
                {comparison.changed.map((item) => <div className="sm:col-span-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-900" key={item.sourceFieldAlias}><b>{item.sourceFieldAlias}</b>：{item.changedFields.join("、")}</div>)}
              </div>}
            </article>
          )}
          {message && <div aria-live="polite" className="rounded-xl border border-[#dce4de] bg-[#eef5f0] px-4 py-3 text-sm text-[#245741]">{message}</div>}
          <p className="text-xs text-slate-500">适配包只定义数据字段与仿真参数映射，不直接向真实设备下发控制指令；启用前仍需人工确认。</p>
        </section>
      </div>
    </main>
  );
}

function DiffCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div className="rounded-xl bg-[#f5f7f5] p-4"><div className="text-xs text-slate-500">{label}</div><div className={`mt-1 font-mono text-2xl font-semibold ${tone}`}>{value}</div></div>;
}
