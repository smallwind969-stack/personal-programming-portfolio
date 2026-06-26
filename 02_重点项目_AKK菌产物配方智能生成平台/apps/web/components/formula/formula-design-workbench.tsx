"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { generateFormula } from "@/lib/api";
import { formatCategory, formatRisk, getIngredientProfile } from "@/lib/display";
import { AkkProduct, LlmStatus } from "@/lib/schemas";

type RatioMap = Record<string, number>;
type StageKey = "target" | "formula" | "evidence" | "submit";
type RecommendationPlan = {
  ids: string[];
  ratios: RatioMap;
  tags: string[];
  namePrefix: string;
  reason: string;
};

const stages: { key: StageKey; label: string; desc: string }[] = [
  { key: "target", label: "01 目标输入", desc: "商品类型与客户需求" },
  { key: "formula", label: "02 原料配比", desc: "AKK 产物与比例" },
  { key: "evidence", label: "03 证据风险", desc: "知识库与验证点" },
  { key: "submit", label: "04 生成报告", desc: "输出方案建议书" },
];

const targetOptions = ["低糖", "肠道健康", "后生元概念", "清洁标签", "轻负担", "饱腹感", "即饮化", "儿童友好", "银发营养"];
const chartColors = ["#0d6b61", "#f2b84b", "#3d6fb6", "#8a63d2", "#d96c6c"];

const quickExamples = [
  "低糖肠道健康酸奶，面向女性白领，口感清爽，成本中等",
  "儿童可食用肠道健康软糖，低糖、果味、方便携带",
  "银发人群营养粉，强调肠道舒适、复水快、蛋白和膳食纤维",
  "运动后即饮功能饮料，清爽低负担，减少沉淀和底味",
  "体重管理代餐奶昔，饱腹感强，配料表尽量清洁",
];

function normalizeRatios(productIds: string[], ratios: RatioMap) {
  const total = productIds.reduce((sum, id) => sum + (ratios[id] || 0), 0);
  if (!total) return {};
  return productIds.reduce<RatioMap>((acc, id) => {
    acc[id] = Number((((ratios[id] || 0) / total) * 100).toFixed(1));
    return acc;
  }, {});
}

function findProduct(products: AkkProduct[], category: string, fallbackIndex: number) {
  return products.find((item) => item.productCategory === category) ?? products[fallbackIndex] ?? products[0];
}

function includesAny(text: string, keywords: string[]) {
  return keywords.some((keyword) => text.includes(keyword.toLowerCase()));
}

function inferTags(text: string) {
  const tags = new Set<string>();
  if (includesAny(text, ["低糖", "控糖", "无糖", "减糖"])) tags.add("低糖");
  if (includesAny(text, ["肠", "胃", "akk", "菌", "消化"])) tags.add("肠道健康");
  if (includesAny(text, ["后生元", "灭活", "postbiotic"])) tags.add("后生元概念");
  if (includesAny(text, ["清洁", "配料表", "clean label"])) tags.add("清洁标签");
  if (includesAny(text, ["轻", "低负担"])) tags.add("轻负担");
  if (includesAny(text, ["饱腹", "代餐", "体重"])) tags.add("饱腹感");
  if (includesAny(text, ["饮料", "即饮", "水"])) tags.add("即饮化");
  if (includesAny(text, ["儿童", "孩子", "软糖", "糖果"])) tags.add("儿童友好");
  if (includesAny(text, ["银发", "老人", "老年"])) tags.add("银发营养");
  return Array.from(tags).slice(0, 5);
}

function inferProductPlan(text: string, products: AkkProduct[]): RecommendationPlan {
  const normalized = text.toLowerCase();
  const postbiotic = findProduct(products, "postbiotic", 0);
  const metabolite = findProduct(products, "metabolite_blend", 1);
  const fiber = findProduct(products, "fiber_complex", 2);
  const tags = inferTags(normalized);

  if (includesAny(normalized, ["牛奶", "酸奶", "乳", "奶", "yogurt", "milk"])) {
    return {
      ids: [postbiotic.productId, fiber.productId, metabolite.productId],
      ratios: { [postbiotic.productId]: 58, [fiber.productId]: 28, [metabolite.productId]: 14 },
      tags: Array.from(new Set(["低糖", "肠道健康", "后生元概念", ...tags])).slice(0, 5),
      namePrefix: "AKK 乳品",
      reason: "识别为乳品/酸奶方向：后生元粉末承担 AKK 主卖点，纤维复配物改善质构、低糖厚度和饱腹表达，代谢物组合低比例补充风味与功能概念。",
    };
  }

  if (includesAny(normalized, ["饮料", "即饮", "水", "beverage", "drink"])) {
    return {
      ids: [metabolite.productId, postbiotic.productId, fiber.productId],
      ratios: { [metabolite.productId]: 45, [postbiotic.productId]: 35, [fiber.productId]: 20 },
      tags: Array.from(new Set(["即饮化", "轻负担", "肠道健康", ...tags])).slice(0, 5),
      namePrefix: "AKK 即饮",
      reason: "识别为功能饮料方向：优先提高水相适配性和清爽口感，用代谢物组合做主体，后生元粉末承接 AKK 差异化概念，纤维低比例参与口感和标签表达。",
    };
  }

  if (includesAny(normalized, ["粉", "营养", "银发", "老人", "代餐", "奶昔", "meal", "powder"])) {
    return {
      ids: [fiber.productId, postbiotic.productId, metabolite.productId],
      ratios: { [fiber.productId]: 50, [postbiotic.productId]: 42, [metabolite.productId]: 8 },
      tags: Array.from(new Set(["饱腹感", "肠道健康", "银发营养", ...tags])).slice(0, 5),
      namePrefix: "AKK 营养",
      reason: "识别为营养粉/代餐方向：纤维复配物作为结构和饱腹基础，后生元粉末强化肠道健康概念，代谢物组合低比例补充风味和功能表达。",
    };
  }

  if (includesAny(normalized, ["软糖", "糖果", "果冻", "gummy", "jelly"])) {
    return {
      ids: [postbiotic.productId, fiber.productId],
      ratios: { [postbiotic.productId]: 62, [fiber.productId]: 38 },
      tags: Array.from(new Set(["儿童友好", "低糖", "后生元概念", ...tags])).slice(0, 5),
      namePrefix: "AKK 软糖",
      reason: "识别为软糖/果冻方向：后生元粉末作为核心功能原料，纤维复配物用于支撑质构、低糖和咀嚼体验。",
    };
  }

  return {
    ids: [postbiotic.productId, metabolite.productId],
    ratios: { [postbiotic.productId]: 70, [metabolite.productId]: 30 },
    tags: tags.length ? tags : ["肠道健康", "后生元概念"],
    namePrefix: "AKK 商品",
    reason: "未识别到明确品类，默认采用后生元粉末为主、代谢物组合为辅的通用 AKK 商品概念方案。",
  };
}

function buildName(productType: string, prefix: string, tags: string[]) {
  const core = productType.trim() || "自定义商品";
  const tagText = tags.slice(0, 2).filter((tag) => !core.includes(tag)).join("");
  return `${prefix}${tagText ? ` ${tagText}` : ""}${core}方案`;
}

function scoreText(score: number) {
  if (score >= 80) return "适合推进";
  if (score >= 65) return "可打样";
  if (score >= 50) return "需优化";
  return "暂缓";
}

export function FormulaDesignWorkbench({ llmStatus, products }: { llmStatus?: LlmStatus; products: AkkProduct[] }) {
  const router = useRouter();
  const initialIds = products.slice(0, 2).map((product) => product.productId);
  const [activeStage, setActiveStage] = useState<StageKey>("target");
  const [selectedIds, setSelectedIds] = useState<string[]>(initialIds);
  const [ratios, setRatios] = useState<RatioMap>(() =>
    initialIds.reduce<RatioMap>((acc, id, index) => {
      acc[id] = index === 0 ? 70 : 30;
      return acc;
    }, {}),
  );
  const [customProductType, setCustomProductType] = useState("低糖肠道健康酸奶");
  const [customDemand, setCustomDemand] = useState("面向女性白领，口感清爽，成本中等，适合早餐和轻食渠道。");
  const [projectName, setProjectName] = useState("AKK 乳品低糖肠道健康酸奶方案");
  const [targetTags, setTargetTags] = useState<string[]>(["低糖", "肠道健康", "后生元概念"]);
  const [agentReason, setAgentReason] = useState("先输入目标商品，点击智能推荐配方后，系统会切换到原料配比并给出推荐比例。");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const selectedProducts = products.filter((product) => selectedIds.includes(product.productId));
  const normalizedRatios = normalizeRatios(selectedIds, ratios);
  const demandText = `${customProductType} ${customDemand} ${targetTags.join(" ")}`;

  const liveResult = useMemo(() => {
    const weighted = selectedProducts.reduce(
      (acc, product) => {
        const ratio = normalizedRatios[product.productId] || 0;
        const profile = getIngredientProfile(product.productCategory);
        acc.cost += (profile.costIndex * ratio) / 100;
        acc.stability += (profile.stabilityIndex * ratio) / 100;
        acc.risk += ((product.riskLevel === "high" ? 86 : product.riskLevel === "medium" ? 58 : 32) * ratio) / 100;
        return acc;
      },
      { cost: 0, stability: 0, risk: 0 },
    );
    const fit = Math.min(Math.round((weighted.stability + (100 - weighted.risk) + targetTags.length * 9 + 52) / 3), 96);
    return {
      fit,
      cost: Math.round(weighted.cost),
      risk: Math.round(weighted.risk),
      stability: Math.round(weighted.stability),
      readiness: Math.min(Math.round((fit + weighted.stability + (100 - weighted.risk)) / 3), 96),
    };
  }, [normalizedRatios, selectedProducts, targetTags.length]);

  const advantages = [
    `目标商品为“${customProductType || "自定义商品"}”，适合用本地 LLM 做需求解析和知识库匹配。`,
    `当前卖点围绕 ${targetTags.slice(0, 4).join("、") || "AKK 概念"} 展开，可生成客户沟通版方案。`,
    selectedProducts.some((product) => product.productCategory === "fiber_complex")
      ? "引入纤维复配物，有利于结构、复水、饱腹感或软糖质构表达。"
      : "以后生元和代谢物组合为主，有利于强化 AKK 差异化和功能概念。",
  ];

  function runAgentRecommendation(input?: string) {
    const productType = input ?? customProductType;
    const text = `${productType} ${customDemand} ${targetTags.join(" ")}`;
    const plan = inferProductPlan(text, products);
    const nextTags = plan.tags.length ? plan.tags : targetTags;
    setCustomProductType(productType);
    setTargetTags(nextTags);
    setSelectedIds(plan.ids);
    setRatios(plan.ratios);
    setProjectName(buildName(productType, plan.namePrefix, nextTags));
    setAgentReason(
      `${plan.reason} 当前推荐配比：${plan.ids
        .map((id) => `${products.find((product) => product.productId === id)?.productName ?? id} ${plan.ratios[id]}%`)
        .join(" / ")}。`,
    );
    setActiveStage("formula");
  }

  function toggleProduct(product: AkkProduct) {
    setSelectedIds((current) => {
      if (current.includes(product.productId)) {
        const next = current.filter((id) => id !== product.productId);
        return next.length ? next : current;
      }
      setRatios((ratioMap) => ({ ...ratioMap, [product.productId]: 20 }));
      return [...current, product.productId];
    });
  }

  function toggleTarget(tag: string) {
    setTargetTags((current) => (current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag]));
  }

  async function submitFormula() {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const constraints = [
        ...selectedIds.map((id) => `custom_ratio:${id}:${normalizedRatios[id] || 0}`),
        `project_name:${projectName}`,
        `custom_application:${customProductType}`,
        `customer_demand:${customDemand}`,
        "llm_agent_mode:local_ollama",
        "cost_preference:balanced",
        "clean_label_preferred:true",
      ];
      const result = await generateFormula({
        applicationTargetId: "custom",
        targetProperties: [...targetTags, customProductType, customDemand].filter(Boolean),
        constraints,
        preferredProductIds: selectedIds,
        excludedProductIds: [],
        maxIngredientCount: selectedIds.length,
        notes: `custom product: ${customProductType}; demand: ${customDemand}`,
      });
      router.push(`/formula/results/${encodeURIComponent(result.resultId)}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "生成失败，请确认后端服务是否可用。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-4">
      <section className="rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={llmStatus?.enabled && llmStatus.available ? "success" : "warning"}>
                {llmStatus?.enabled && llmStatus.available ? "本地大模型已连接" : "规则模板模式"}
              </Badge>
              {llmStatus ? <Badge>{llmStatus.provider} · {llmStatus.model}</Badge> : null}
              <Badge>Research use only</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">配方设计工作流</h1>
            <p className="mt-2 max-w-3xl text-xs leading-6 text-muted-foreground">
              按“输入目标、推荐配比、证据风险、生成报告”的顺序推进；每一步只展示当前任务，避免把所有信息堆在同一屏。
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => runAgentRecommendation()} variant="secondary">智能推荐配方</Button>
            <Button onClick={() => setActiveStage("submit")}>准备生成</Button>
          </div>
        </div>

        <div className="mt-5 grid gap-2 md:grid-cols-4">
          {stages.map((stage) => (
            <button
              className={`rounded-xl border px-3 py-3 text-left transition ${
                activeStage === stage.key ? "border-primary bg-emerald-50 text-primary" : "border-border bg-white text-slate-600 hover:bg-slate-50"
              }`}
              key={stage.key}
              onClick={() => setActiveStage(stage.key)}
              type="button"
            >
              <div className="text-sm font-semibold">{stage.label}</div>
              <div className="mt-1 text-[11px]">{stage.desc}</div>
            </button>
          ))}
        </div>
      </section>

      {submitError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
          方案生成失败：{submitError}。如果使用公网演示，Render 后端首次唤醒可能需要等待几十秒后重试。
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <div className="min-w-0">
          {activeStage === "target" ? (
            <TargetStage
              customDemand={customDemand}
              customProductType={customProductType}
              onDemandChange={setCustomDemand}
              onProductTypeChange={setCustomProductType}
              onQuickExample={runAgentRecommendation}
              onTargetToggle={toggleTarget}
              targetTags={targetTags}
            />
          ) : null}

          {activeStage === "formula" ? (
            <FormulaStage
              normalizedRatios={normalizedRatios}
              onProductToggle={toggleProduct}
              onRatioChange={(id, value) => setRatios((current) => ({ ...current, [id]: value }))}
              products={products}
              ratios={ratios}
              selectedIds={selectedIds}
              selectedProducts={selectedProducts}
            />
          ) : null}

          {activeStage === "evidence" ? (
            <EvidenceStage
              advantages={advantages}
              agentReason={agentReason}
              liveResult={liveResult}
              selectedProducts={selectedProducts}
              targetTags={targetTags}
            />
          ) : null}

          {activeStage === "submit" ? (
            <SubmitStage
              customDemand={customDemand}
              customProductType={customProductType}
              isSubmitting={isSubmitting}
              onBack={() => setActiveStage("evidence")}
              onProjectNameChange={setProjectName}
              onSubmit={submitFormula}
              projectName={projectName}
              selectedProducts={selectedProducts}
              targetTags={targetTags}
            />
          ) : null}
        </div>

        <SummaryPanel
          activeStage={activeStage}
          customProductType={customProductType}
          liveResult={liveResult}
          normalizedRatios={normalizedRatios}
          projectName={projectName}
          selectedProducts={selectedProducts}
          targetTags={targetTags}
        />
      </div>
    </div>
  );
}

function TargetStage({
  customDemand,
  customProductType,
  onDemandChange,
  onProductTypeChange,
  onQuickExample,
  onTargetToggle,
  targetTags,
}: {
  customDemand: string;
  customProductType: string;
  onDemandChange: (value: string) => void;
  onProductTypeChange: (value: string) => void;
  onQuickExample: (value: string) => void;
  onTargetToggle: (value: string) => void;
  targetTags: string[];
}) {
  return (
    <Card className="min-h-[560px]">
      <CardTitle>目标商品输入</CardTitle>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <div className="space-y-4">
          <label className="block">
            <span className="text-xs font-medium">目标商品类型</span>
            <input
              className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm"
              onChange={(event) => onProductTypeChange(event.target.value)}
              value={customProductType}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium">客户需求与限制</span>
            <textarea
              className="mt-1 min-h-36 w-full rounded-md border border-border px-3 py-2 text-sm leading-6"
              onChange={(event) => onDemandChange(event.target.value)}
              value={customDemand}
            />
          </label>
          <div>
            <div className="text-xs font-medium">卖点标签</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {targetOptions.map((tag) => (
                <button
                  className={`rounded-full border px-3 py-1.5 text-xs ${targetTags.includes(tag) ? "border-primary bg-emerald-50 text-primary" : "border-border bg-white text-slate-600"}`}
                  key={tag}
                  onClick={() => onTargetToggle(tag)}
                  type="button"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div>
          <div className="text-xs font-medium">快速示例</div>
          <div className="mt-2 space-y-2">
            {quickExamples.map((example) => (
              <button
                className="block w-full rounded-lg border border-border bg-white px-3 py-3 text-left text-xs leading-5 hover:bg-emerald-50"
                key={example}
                onClick={() => onQuickExample(example)}
                type="button"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

function FormulaStage({
  normalizedRatios,
  onProductToggle,
  onRatioChange,
  products,
  ratios,
  selectedIds,
  selectedProducts,
}: {
  normalizedRatios: RatioMap;
  onProductToggle: (product: AkkProduct) => void;
  onRatioChange: (id: string, value: number) => void;
  products: AkkProduct[];
  ratios: RatioMap;
  selectedIds: string[];
  selectedProducts: AkkProduct[];
}) {
  return (
    <Card className="min-h-[560px]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CardTitle>AKK 原料配比</CardTitle>
        <Badge tone="success">{selectedProducts.length} 项已选</Badge>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[220px_1fr]">
        <div>
          <RatioDonut products={selectedProducts} ratios={normalizedRatios} />
          <div className="mt-4 space-y-2">
            {selectedProducts.map((product, index) => (
              <div className="flex items-center gap-2 text-xs" key={product.productId}>
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: chartColors[index % chartColors.length] }} />
                <span className="flex-1 truncate">{product.productName}</span>
                <span className="font-semibold">{normalizedRatios[product.productId] || 0}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {products.map((product) => {
            const checked = selectedIds.includes(product.productId);
            const profile = getIngredientProfile(product.productCategory);
            return (
              <div className={`rounded-lg border p-3 ${checked ? "border-primary bg-emerald-50" : "border-border bg-white"}`} key={product.productId}>
                <div className="flex items-start justify-between gap-2">
                  <label className="flex min-w-0 items-start gap-2">
                    <input checked={checked} className="mt-1" onChange={() => onProductToggle(product)} type="checkbox" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold">{product.productName}</span>
                      <span className="mt-1 block text-xs leading-5 text-muted-foreground">{profile.component}</span>
                    </span>
                  </label>
                  <Badge>{formatCategory(product.productCategory)}</Badge>
                </div>
                <div className="mt-2 grid gap-2 text-[11px] text-slate-600 md:grid-cols-3">
                  <span className="rounded bg-white px-2 py-1">风险：{formatRisk(product.riskLevel)}</span>
                  <span className="rounded bg-white px-2 py-1">证据：{product.evidenceLevel}</span>
                  <span className="rounded bg-white px-2 py-1">建议：{profile.usageRange}</span>
                </div>
                {checked ? (
                  <div className="mt-3 flex items-center gap-2">
                    <input
                      className="w-24 rounded-md border border-border bg-white px-2 py-1 text-sm"
                      min={0}
                      onChange={(event) => onRatioChange(product.productId, Number(event.target.value))}
                      type="number"
                      value={ratios[product.productId] ?? 0}
                    />
                    <span className="text-xs text-muted-foreground">份额，折算 {normalizedRatios[product.productId] || 0}%</span>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

function EvidenceStage({
  advantages,
  agentReason,
  liveResult,
  selectedProducts,
  targetTags,
}: {
  advantages: string[];
  agentReason: string;
  liveResult: { fit: number; cost: number; risk: number; stability: number; readiness: number };
  selectedProducts: AkkProduct[];
  targetTags: string[];
}) {
  const requiredChecks = Array.from(
    new Set(selectedProducts.flatMap((product) => product.validationMetrics.map((metric) => metric.metricName)).concat(["证据与合规复核", "感官接受度"])),
  ).slice(0, 6);

  return (
    <Card className="min-h-[560px]">
      <CardTitle>证据、风险与验证规划</CardTitle>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <Metric label="匹配" value={liveResult.fit} />
        <Metric label="准备" value={liveResult.readiness} />
        <Metric label="成本" value={liveResult.cost} />
        <Metric label="风险" value={liveResult.risk} />
      </div>

      <div className="mt-5 rounded-lg border border-emerald-100 bg-emerald-50 p-4">
        <div className="text-sm font-semibold text-emerald-950">推荐逻辑</div>
        <p className="mt-2 text-sm leading-6 text-emerald-950">{agentReason}</p>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-white p-4">
          <div className="text-sm font-semibold">产品优势摘要</div>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            {advantages.map((advantage) => (
              <li key={advantage}>- {advantage}</li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-border bg-white p-4">
          <div className="text-sm font-semibold">必需验证项目</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {requiredChecks.map((check) => (
              <Badge key={check} tone="warning">{check}</Badge>
            ))}
          </div>
          <div className="mt-4 text-sm leading-6 text-muted-foreground">
            生成报告时，后端会继续检索论文正文片段，并把引用材料、配比理由、风险边界和实验建议写入方案建议书。
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-border bg-slate-50 p-4">
        <div className="text-sm font-semibold">当前卖点</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {targetTags.map((tag) => (
            <Badge key={tag} tone="success">{tag}</Badge>
          ))}
        </div>
      </div>
    </Card>
  );
}

function SubmitStage({
  customDemand,
  customProductType,
  isSubmitting,
  onBack,
  onProjectNameChange,
  onSubmit,
  projectName,
  selectedProducts,
  targetTags,
}: {
  customDemand: string;
  customProductType: string;
  isSubmitting: boolean;
  onBack: () => void;
  onProjectNameChange: (value: string) => void;
  onSubmit: () => void;
  projectName: string;
  selectedProducts: AkkProduct[];
  targetTags: string[];
}) {
  return (
    <Card className="min-h-[560px]">
      <CardTitle>生成商品方案建议书</CardTitle>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.8fr]">
        <div className="space-y-4">
          <label className="block">
            <span className="text-xs font-medium">方案名称</span>
            <input
              className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm"
              onChange={(event) => onProjectNameChange(event.target.value)}
              value={projectName}
            />
          </label>
          <div className="rounded-lg border border-border bg-slate-50 p-4">
            <div className="text-sm font-semibold">生成内容</div>
            <div className="mt-3 grid gap-2 text-sm leading-6 text-slate-700">
              <div>目标商品：{customProductType}</div>
              <div>客户需求：{customDemand}</div>
              <div>AKK 原料：{selectedProducts.map((product) => product.productName).join("、")}</div>
              <div>卖点标签：{targetTags.join("、")}</div>
            </div>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
            输出仍为内部研发实验建议，不能作为可直接上市配方。正式推进前需要完成稳定性、感官、标志物和合规审核。
          </div>
        </div>

        <div className="rounded-lg border border-border bg-white p-4">
          <div className="text-sm font-semibold">将调用的能力</div>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <div className="rounded-md bg-slate-50 px-3 py-2">知识库正文片段检索</div>
            <div className="rounded-md bg-slate-50 px-3 py-2">本地 Ollama RAG 补充理由</div>
            <div className="rounded-md bg-slate-50 px-3 py-2">风险预测与验证项目组装</div>
            <div className="rounded-md bg-slate-50 px-3 py-2">生成后自动进入方案库</div>
          </div>
          <div className="mt-5 flex gap-2">
            <Button onClick={onBack} variant="secondary">返回检查</Button>
            <Button disabled={isSubmitting} onClick={onSubmit}>
              {isSubmitting ? "生成中..." : "生成建议书"}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

function SummaryPanel({
  activeStage,
  customProductType,
  liveResult,
  normalizedRatios,
  projectName,
  selectedProducts,
  targetTags,
}: {
  activeStage: StageKey;
  customProductType: string;
  liveResult: { fit: number; cost: number; risk: number; stability: number; readiness: number };
  normalizedRatios: RatioMap;
  projectName: string;
  selectedProducts: AkkProduct[];
  targetTags: string[];
}) {
  const stageLabel = stages.find((stage) => stage.key === activeStage)?.label ?? "";
  return (
    <aside className="space-y-4">
      <Card>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>方案摘要</CardTitle>
          <Badge>{stageLabel}</Badge>
        </div>
        <div className="mt-4 text-sm font-semibold text-slate-950">{projectName}</div>
        <div className="mt-1 text-xs text-muted-foreground">{customProductType}</div>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <Metric label="匹配" value={liveResult.fit} />
          <Metric label="风险" value={liveResult.risk} />
        </div>
        <div className="mt-4">
          <div className="text-xs font-medium">当前配比</div>
          <div className="mt-2 space-y-2">
            {selectedProducts.map((product, index) => (
              <div className="flex items-center gap-2 text-xs" key={product.productId}>
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: chartColors[index % chartColors.length] }} />
                <span className="flex-1 truncate">{product.productName}</span>
                <span className="font-semibold">{normalizedRatios[product.productId] || 0}%</span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>卖点标签</CardTitle>
        <div className="mt-3 flex flex-wrap gap-2">
          {targetTags.map((tag) => (
            <Badge key={tag} tone="success">{tag}</Badge>
          ))}
        </div>
        <p className="mt-4 text-xs leading-5 text-muted-foreground">
          当前判断：{scoreText(liveResult.readiness)}。建议先完成证据风险检查，再生成建议书。
        </p>
      </Card>
    </aside>
  );
}

function RatioDonut({ products, ratios }: { products: AkkProduct[]; ratios: RatioMap }) {
  let start = 0;
  const segments = products.map((product, index) => {
    const value = ratios[product.productId] || 0;
    const end = start + value;
    const segment = `${chartColors[index % chartColors.length]} ${start}% ${end}%`;
    start = end;
    return segment;
  });
  const gradient = segments.length ? `conic-gradient(${segments.join(", ")})` : "#e2e8f0";

  return (
    <div className="flex justify-center">
      <div className="relative h-40 w-40 rounded-full" style={{ background: gradient }}>
        <div className="absolute inset-6 rounded-full bg-white" />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-[11px] text-muted-foreground">配比</div>
          <div className="text-lg font-semibold">{products.length} 项</div>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-white p-3">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}
