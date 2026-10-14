"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { generateFormula } from "@/lib/api";
import { formatApplication, formatCategory, formatRisk, getProductRole } from "@/lib/display";
import { AkkProduct, LlmStatus } from "@/lib/schemas";

type RatioMap = Record<string, number>;
type StageKey = "target" | "formula" | "evidence" | "submit";

type ProductPlan = {
  name: string;
  reason: string;
  ids: string[];
  ratios: RatioMap;
  tags: string[];
};

const stages: { key: StageKey; label: string; desc: string }[] = [
  { key: "target", label: "01 目标产品", desc: "产品形态与客户需求" },
  { key: "formula", label: "02 产物组合", desc: "底物、产物与比例调整" },
  { key: "evidence", label: "03 证据风险", desc: "模型解释与验证指标" },
  { key: "submit", label: "04 生成建议书", desc: "输出内部研发方案" },
];

const targetOptions = ["低糖", "肠道健康", "后生元概念", "清洁标签", "轻负担", "饱腹感", "即饮化", "儿童友好", "银发营养", "海藻基质", "包埋保护", "低腥味"];

const quickExamples = [
  "低糖肠道健康果冻，面向年轻女性，口感清爽，不要破坏果冻凝胶体系",
  "功能果冻或爆爆珠，需要突出海藻源包埋和 AKK 后生元概念",
  "低腥味海藻鱼丸，目标是改善口感并保留红藻多糖发酵潜力",
  "中试厌氧发酵平台，目标是提高 AKK 有效成分与短链脂肪酸表现",
  "银发营养粉，强调肠道舒适、复水快、蛋白和膳食纤维",
];

const chartColors = ["#0d6b61", "#f2b84b", "#3d6fb6", "#8a63d2", "#d96c6c", "#14b8a6"];

function includesAny(text: string, keywords: string[]) {
  return keywords.some((keyword) => text.includes(keyword.toLowerCase()));
}

function normalizeRatios(productIds: string[], ratios: RatioMap) {
  const total = productIds.reduce((sum, id) => sum + (ratios[id] || 0), 0);
  if (!total) return {};
  return productIds.reduce<RatioMap>((acc, id) => {
    acc[id] = Number((((ratios[id] || 0) / total) * 100).toFixed(1));
    return acc;
  }, {});
}

function findById(products: AkkProduct[], productId: string) {
  return products.find((product) => product.productId === productId);
}

function firstAvailable(products: AkkProduct[], productIds: string[]) {
  return productIds.map((id) => findById(products, id)).filter(Boolean) as AkkProduct[];
}

function extractTargetProduct(text: string) {
  return text.split(/[，,。；;]/)[0]?.trim() || text.trim();
}

function inferTags(text: string) {
  const tags = new Set<string>();
  const pairs: [string, string[]][] = [
    ["低糖", ["低糖", "控糖", "无糖", "减糖"]],
    ["肠道健康", ["肠道", "消化", "akk", "菌", "后生元"]],
    ["后生元概念", ["后生元", "灭活", "postbiotic"]],
    ["清洁标签", ["清洁", "配料表", "clean label"]],
    ["轻负担", ["轻", "低负担", "清爽"]],
    ["饱腹感", ["饱腹", "代餐", "体重"]],
    ["即饮化", ["饮料", "即饮", "水相", "beverage", "drink"]],
    ["儿童友好", ["儿童", "孩子", "软糖", "糖果"]],
    ["银发营养", ["银发", "老人", "老年"]],
    ["海藻基质", ["海藻", "红藻", "鱼丸", "紫菜", "岩藻"]],
    ["包埋保护", ["包埋", "颗粒", "爆爆珠", "释放"]],
    ["低腥味", ["脱腥", "腥味", "低腥"]],
  ];
  pairs.forEach(([tag, keywords]) => {
    if (includesAny(text, keywords)) tags.add(tag);
  });
  return Array.from(tags).slice(0, 6);
}

function buildPlan(input: string, products: AkkProduct[]): ProductPlan {
  const text = input.toLowerCase();
  const tags = inferTags(text);

  if (includesAny(text, ["巧克力", "可可", "黑巧", "白巧", "巧克力棒", "chocolate", "cocoa"])) {
    const selected = firstAvailable(products, [
      "akk-postbiotic-powder",
      "akk-encapsulated-particles",
      "bfp-polysaccharide",
      "akk-metabolite-blend",
    ]);
    return {
      name: "巧克力低糖包埋方案",
      reason: "识别为巧克力或可可基产品。推荐以 AKK 后生元作为核心概念，配合海藻源包埋颗粒降低加工和脂相体系对标志物的影响，BFP 作为论文底物证据，代谢物组合低比例参与风味和功能线索验证。",
      ids: selected.map((product) => product.productId),
      ratios: Object.fromEntries(selected.map((product, index) => [product.productId, [34, 30, 22, 14][index] ?? 10])),
      tags: Array.from(new Set(["低糖", "肠道健康", "后生元概念", "包埋保护", "轻负担", ...tags])).slice(0, 6),
    };
  }

  if (includesAny(text, ["果冻", "凝胶", "软糖", "gummy", "jelly"])) {
    const selected = firstAvailable(products, [
      "akk-postbiotic-powder",
      "iota-carrageenan-gel",
      "bfp-polysaccharide",
      "akk-encapsulated-particles",
    ]);
    return {
      name: "果冻凝胶平衡方案",
      reason: "识别为果冻或凝胶产品。优先用 AKK 后生元承担功能表达，用 ι-卡拉胶控制凝胶结构，用红毛藻多糖提供 AKK 底物证据，必要时加入包埋颗粒提高加工稳定性。",
      ids: selected.map((product) => product.productId),
      ratios: Object.fromEntries(selected.map((product, index) => [product.productId, [38, 26, 24, 12][index] ?? 10])),
      tags: Array.from(new Set(["低糖", "肠道健康", "海藻基质", ...tags])).slice(0, 6),
    };
  }

  if (includesAny(text, ["爆爆珠", "包埋", "颗粒", "释放"])) {
    const selected = firstAvailable(products, [
      "akk-encapsulated-particles",
      "fucoidan-akk-popping-bead",
      "fucoidan-substrate",
      "akk-postbiotic-powder",
    ]);
    return {
      name: "包埋释放原型方案",
      reason: "识别为包埋或爆珠产品。优先关注粒径、包埋率、泄漏率和模拟消化释放曲线，避免把展示样品误写成最终配方。",
      ids: selected.map((product) => product.productId),
      ratios: Object.fromEntries(selected.map((product, index) => [product.productId, [36, 28, 20, 16][index] ?? 10])),
      tags: Array.from(new Set(["包埋保护", "肠道健康", "产品原型", ...tags])).slice(0, 6),
    };
  }

  if (includesAny(text, ["鱼丸", "海藻", "红藻", "脱腥", "紫菜", "腥味"])) {
    const selected = firstAvailable(products, [
      "red-algae-fish-ball-matrix",
      "seaweed-fermented-fiber",
      "porphyra-glycoprotein",
      "bfp-polysaccharide",
    ]);
    return {
      name: "海藻食品基质方案",
      reason: "识别为海藻食品或鱼丸基质。推荐把口感、腥味、体外消化和结肠发酵放在同一轮验证，不能只按 AKK 增殖单目标优化。",
      ids: selected.map((product) => product.productId),
      ratios: Object.fromEntries(selected.map((product, index) => [product.productId, [34, 30, 20, 16][index] ?? 10])),
      tags: Array.from(new Set(["海藻基质", "低腥味", "食品基质", ...tags])).slice(0, 6),
    };
  }

  if (includesAny(text, ["发酵", "培养", "厌氧", "产线", "短链脂肪酸", "amuc"])) {
    const selected = firstAvailable(products, [
      "bfp-polysaccharide",
      "ubfp-polysaccharide",
      "lambda-carrageenan-amuc",
      "php-platycodon-polysaccharide",
    ]);
    return {
      name: "AKK 培养底物筛选方案",
      reason: "识别为培养或产线参数任务。推荐以 BFP 为核心锚点，加入 UBFP 和 λ-卡拉胶做结构改性与 Amuc-1260 方向对照，并保留 PHP 作为非海藻多糖对照。",
      ids: selected.map((product) => product.productId),
      ratios: Object.fromEntries(selected.map((product, index) => [product.productId, [42, 24, 20, 14][index] ?? 10])),
      tags: Array.from(new Set(["肠道健康", "短链脂肪酸", "机制验证", ...tags])).slice(0, 6),
    };
  }

  if (includesAny(text, ["营养粉", "粉", "银发", "老人", "代餐", "奶昔", "meal"])) {
    const selected = firstAvailable(products, [
      "akk-fiber-complex",
      "akk-postbiotic-powder",
      "bfp-polysaccharide",
      "akk-metabolite-blend",
    ]);
    return {
      name: "营养粉肠道健康方案",
      reason: "识别为营养粉或代餐方向。纤维复配物承担粉体结构和饱腹感，AKK 后生元承担核心概念，BFP 提供底物证据，代谢物组合低比例补充风味与功能线索。",
      ids: selected.map((product) => product.productId),
      ratios: Object.fromEntries(selected.map((product, index) => [product.productId, [42, 30, 18, 10][index] ?? 10])),
      tags: Array.from(new Set(["银发营养", "饱腹感", "肠道健康", ...tags])).slice(0, 6),
    };
  }

  const selected = firstAvailable(products, [
    "akk-postbiotic-powder",
    "bfp-polysaccharide",
    "akk-fiber-complex",
    "akk-metabolite-blend",
  ]);
  return {
    name: "通用 AKK 产品探索方案",
    reason: "未识别到强产品形态，采用后生元、BFP、纤维复配和代谢物组合的通用探索结构，适合先做首轮内部小试。",
    ids: selected.map((product) => product.productId),
    ratios: Object.fromEntries(selected.map((product, index) => [product.productId, [40, 26, 22, 12][index] ?? 10])),
    tags: tags.length ? tags : ["肠道健康", "后生元概念", "内部小试"],
  };
}

function buildProjectName(productType: string, plan: ProductPlan) {
  const clean = productType.trim() || "自定义产品";
  return `AKK ${clean}${plan.name}`;
}

export function FormulaDesignWorkbench({ llmStatus, products }: { llmStatus?: LlmStatus; products: AkkProduct[] }) {
  const router = useRouter();
  const initialPlan = buildPlan("低糖肠道健康果冻", products);
  const [activeStage, setActiveStage] = useState<StageKey>("target");
  const [targetProduct, setTargetProduct] = useState("低糖肠道健康果冻");
  const [customerDemand, setCustomerDemand] = useState("面向中国境内年轻女性，口感清爽，低糖，不破坏果冻凝胶体系。");
  const [targetTags, setTargetTags] = useState<string[]>(initialPlan.tags);
  const [selectedIds, setSelectedIds] = useState<string[]>(initialPlan.ids);
  const [ratios, setRatios] = useState<RatioMap>(initialPlan.ratios);
  const [projectName, setProjectName] = useState(buildProjectName("低糖肠道健康果冻", initialPlan));
  const [agentReason, setAgentReason] = useState(initialPlan.reason);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const selectedProducts = products.filter((product) => selectedIds.includes(product.productId));
  const normalizedRatios = normalizeRatios(selectedIds, ratios);

  const liveResult = useMemo(() => {
    const evidenceScore = selectedProducts.reduce((sum, product) => {
      const ratio = normalizedRatios[product.productId] || 0;
      const base = product.evidenceLevel === "A" ? 90 : product.evidenceLevel === "B" ? 78 : 62;
      return sum + (base * ratio) / 100;
    }, 0);
    const riskScore = selectedProducts.reduce((sum, product) => {
      const ratio = normalizedRatios[product.productId] || 0;
      const base = product.riskLevel === "high" ? 78 : product.riskLevel === "medium" ? 54 : 28;
      return sum + (base * ratio) / 100;
    }, 0);
    const roleCoverage = new Set(selectedProducts.map((product) => getProductRole(product.productCategory))).size;
    const fit = Math.min(96, Math.round(evidenceScore * 0.55 + (100 - riskScore) * 0.25 + roleCoverage * 6 + targetTags.length * 2));
    const readiness = Math.min(95, Math.round((fit + evidenceScore + (100 - riskScore)) / 3));
    return {
      fit,
      evidence: Math.round(evidenceScore),
      risk: Math.round(riskScore),
      readiness,
      coverage: roleCoverage,
    };
  }, [normalizedRatios, selectedProducts, targetTags.length]);

  function applyPlan(input?: string, options: { navigate?: boolean } = { navigate: true }) {
    const nextTarget = input ? extractTargetProduct(input) : targetProduct;
    const nextDemand = input ?? customerDemand;
    const text = `${nextTarget} ${nextDemand}`;
    const plan = buildPlan(text, products);
    setTargetProduct(nextTarget);
    if (input) {
      setCustomerDemand(nextDemand);
    }
    setTargetTags(plan.tags);
    setSelectedIds(plan.ids);
    setRatios(plan.ratios);
    setProjectName(buildProjectName(nextTarget, plan));
    setAgentReason(plan.reason);
    if (options.navigate) {
      setActiveStage("formula");
    }
  }

  useEffect(() => {
    if (!targetProduct.trim()) {
      return;
    }
    const timer = window.setTimeout(() => {
      applyPlan(undefined, { navigate: false });
    }, 420);
    return () => window.clearTimeout(timer);
  }, [targetProduct, customerDemand, products]);

  function toggleProduct(product: AkkProduct) {
    setSelectedIds((current) => {
      if (current.includes(product.productId)) {
        const next = current.filter((id) => id !== product.productId);
        return next.length ? next : current;
      }
      setRatios((ratioMap) => ({ ...ratioMap, [product.productId]: 12 }));
      return [...current, product.productId];
    });
  }

  function toggleTag(tag: string) {
    setTargetTags((current) => (current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag]));
  }

  async function submitFormula() {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const constraints = [
        ...selectedIds.map((id) => `custom_ratio:${id}:${normalizedRatios[id] || 0}`),
        `project_name:${projectName}`,
        `custom_application:${targetProduct}`,
        `customer_demand:${customerDemand}`,
        "llm_agent_mode:formula_workbench",
        "research_use_only:true",
      ];
      const result = await generateFormula({
        applicationTargetId: "custom",
        targetProperties: [...targetTags, targetProduct, customerDemand].filter(Boolean),
        constraints,
        preferredProductIds: selectedIds,
        excludedProductIds: [],
        maxIngredientCount: selectedIds.length,
        notes: `目标产品：${targetProduct}；客户需求：${customerDemand}`,
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
      <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={llmStatus?.enabled && llmStatus.available ? "success" : "warning"}>
                {llmStatus?.enabled && llmStatus.available ? "本地推理增强可用" : "规则模型可用"}
              </Badge>
              <Badge>内部研发实验建议</Badge>
              <Badge>{products.length} 个产物与底物</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">AKK 产品方案生成工作台</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              从目标产品出发，自动匹配论文底物、AKK 产物、食品基质和验证指标。每一步都可以回改，比例变化会实时更新评分。
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => applyPlan()} variant="secondary">智能推荐组合</Button>
            <Button onClick={() => setActiveStage("submit")}>准备生成</Button>
          </div>
        </div>

        <div className="mt-5 grid gap-2 md:grid-cols-4">
          {stages.map((stage) => (
            <button
              className={`rounded-lg border px-3 py-3 text-left transition ${
                activeStage === stage.key ? "border-primary bg-emerald-50 text-primary" : "border-border bg-white text-slate-600 hover:bg-slate-50"
              }`}
              key={stage.key}
              onClick={() => setActiveStage(stage.key)}
              type="button"
            >
              <div className="text-sm font-semibold">{stage.label}</div>
              <div className="mt-1 text-xs">{stage.desc}</div>
            </button>
          ))}
        </div>
      </section>

      {submitError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
          方案生成失败：{submitError}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <main className="min-w-0">
          {activeStage === "target" ? (
            <TargetStage
              customerDemand={customerDemand}
              onDemandChange={setCustomerDemand}
              onQuickExample={applyPlan}
              onTagToggle={toggleTag}
              onTargetChange={setTargetProduct}
              targetProduct={targetProduct}
              targetTags={targetTags}
            />
          ) : null}

          {activeStage === "formula" ? (
            <FormulaStage
              liveResult={liveResult}
              normalizedRatios={normalizedRatios}
              onProductToggle={toggleProduct}
              onRatioChange={(id, value) => setRatios((current) => ({ ...current, [id]: value }))}
              products={products}
              ratios={ratios}
              selectedIds={selectedIds}
            />
          ) : null}

          {activeStage === "evidence" ? (
            <EvidenceStage
              agentReason={agentReason}
              liveResult={liveResult}
              selectedProducts={selectedProducts}
              targetTags={targetTags}
            />
          ) : null}

          {activeStage === "submit" ? (
            <SubmitStage
              customerDemand={customerDemand}
              isSubmitting={isSubmitting}
              normalizedRatios={normalizedRatios}
              onBack={() => setActiveStage("evidence")}
              onProjectNameChange={setProjectName}
              onSubmit={submitFormula}
              projectName={projectName}
              selectedProducts={selectedProducts}
              targetProduct={targetProduct}
              targetTags={targetTags}
            />
          ) : null}
        </main>

        <SummaryPanel
          activeStage={activeStage}
          liveResult={liveResult}
          normalizedRatios={normalizedRatios}
          projectName={projectName}
          selectedProducts={selectedProducts}
          targetProduct={targetProduct}
          targetTags={targetTags}
        />
      </div>
    </div>
  );
}

function TargetStage({
  customerDemand,
  onDemandChange,
  onQuickExample,
  onTagToggle,
  onTargetChange,
  targetProduct,
  targetTags,
}: {
  customerDemand: string;
  onDemandChange: (value: string) => void;
  onQuickExample: (value: string) => void;
  onTagToggle: (value: string) => void;
  onTargetChange: (value: string) => void;
  targetProduct: string;
  targetTags: string[];
}) {
  return (
    <Card className="min-h-[560px]">
      <CardTitle>目标产品输入</CardTitle>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <div className="space-y-4">
          <label className="block">
            <span className="text-xs font-medium">我要做的终端产品</span>
            <input
              className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm"
              onChange={(event) => onTargetChange(event.target.value)}
              value={targetProduct}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium">客户需求、产品限制和目标效果</span>
            <textarea
              className="mt-1 min-h-36 w-full rounded-md border border-border px-3 py-2 text-sm leading-6"
              onChange={(event) => onDemandChange(event.target.value)}
              value={customerDemand}
            />
          </label>
          <div>
            <div className="text-xs font-medium">目标标签</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {targetOptions.map((tag) => (
                <button
                  className={`rounded-full border px-3 py-1.5 text-xs ${targetTags.includes(tag) ? "border-primary bg-emerald-50 text-primary" : "border-border bg-white text-slate-600"}`}
                  key={tag}
                  onClick={() => onTagToggle(tag)}
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
  liveResult,
  normalizedRatios,
  onProductToggle,
  onRatioChange,
  products,
  ratios,
  selectedIds,
}: {
  liveResult: { fit: number; evidence: number; risk: number; readiness: number; coverage: number };
  normalizedRatios: RatioMap;
  onProductToggle: (product: AkkProduct) => void;
  onRatioChange: (id: string, value: number) => void;
  products: AkkProduct[];
  ratios: RatioMap;
  selectedIds: string[];
}) {
  const selectedProducts = products.filter((product) => selectedIds.includes(product.productId));
  const grouped = selectedProducts.map((product) => getProductRole(product.productCategory));

  return (
    <Card className="min-h-[560px]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CardTitle>产物组合与比例调整</CardTitle>
        <Badge tone="success">{selectedProducts.length} 个已选对象</Badge>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[230px_1fr]">
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
          <div className="mt-4 rounded-lg border border-border bg-slate-50 p-3 text-xs leading-5 text-muted-foreground">
            当前覆盖 {new Set(grouped).size} 类研发角色。建议至少同时覆盖功能产物和论文底物，食品基质类任务还应加入基质或原型对象。
          </div>
          <ScoreSurface liveResult={liveResult} products={selectedProducts} ratios={normalizedRatios} />
        </div>

        <div className="space-y-3">
          {products.map((product) => {
            const checked = selectedIds.includes(product.productId);
            return (
              <div className={`rounded-lg border p-3 ${checked ? "border-primary bg-emerald-50" : "border-border bg-white"}`} key={product.productId}>
                <div className="flex items-start justify-between gap-2">
                  <label className="flex min-w-0 items-start gap-2">
                    <input checked={checked} className="mt-1" onChange={() => onProductToggle(product)} type="checkbox" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold">{product.productName}</span>
                      <span className="mt-1 block text-xs leading-5 text-muted-foreground">{product.description}</span>
                    </span>
                  </label>
                  <Badge>{formatCategory(product.productCategory)}</Badge>
                </div>
                <div className="mt-2 grid gap-2 text-xs text-slate-600 md:grid-cols-3">
                  <span className="rounded bg-white px-2 py-1">角色：{getProductRole(product.productCategory)}</span>
                  <span className="rounded bg-white px-2 py-1">风险：{formatRisk(product.riskLevel)}</span>
                  <span className="rounded bg-white px-2 py-1">证据：{product.evidenceLevel}</span>
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
  agentReason,
  liveResult,
  selectedProducts,
  targetTags,
}: {
  agentReason: string;
  liveResult: { fit: number; evidence: number; risk: number; readiness: number; coverage: number };
  selectedProducts: AkkProduct[];
  targetTags: string[];
}) {
  const requiredChecks = Array.from(
    new Set(selectedProducts.flatMap((product) => product.validationMetrics.map((metric) => metric.metricName)).concat(["感官接受度", "证据与合规复核"])),
  ).slice(0, 8);
  const highRiskProducts = selectedProducts.filter((product) => product.riskLevel === "high");

  return (
    <Card className="min-h-[560px]">
      <CardTitle>证据、风险与模型解释</CardTitle>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <Metric label="方案匹配" value={liveResult.fit} />
        <Metric label="证据强度" value={liveResult.evidence} />
        <Metric label="风险压力" value={liveResult.risk} />
        <Metric label="推进准备" value={liveResult.readiness} />
      </div>

      <div className="mt-5 rounded-lg border border-emerald-100 bg-emerald-50 p-4">
        <div className="text-sm font-semibold text-emerald-950">推荐逻辑</div>
        <p className="mt-2 text-sm leading-6 text-emerald-950">{agentReason}</p>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-white p-4">
          <div className="text-sm font-semibold">必须验证项目</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {requiredChecks.map((check) => (
              <Badge key={check} tone="warning">{check}</Badge>
            ))}
          </div>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            这些指标来自已选产物档案。后续接入真实实验数据后，可以把每个指标转成模型训练标签和批次回填字段。
          </p>
        </div>

        <div className="rounded-lg border border-border bg-white p-4">
          <div className="text-sm font-semibold">风险提示</div>
          <div className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            {highRiskProducts.length ? highRiskProducts.map((product) => (
              <div className="rounded-md bg-red-50 px-3 py-2 text-red-900" key={product.productId}>
                {product.productName} 为高风险对象，需要先做边界验证。
              </div>
            )) : <div className="rounded-md bg-slate-50 px-3 py-2">当前组合没有高风险对象，但仍需完成小试验证。</div>}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-border bg-slate-50 p-4">
        <div className="text-sm font-semibold">当前目标标签</div>
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
  customerDemand,
  isSubmitting,
  normalizedRatios,
  onBack,
  onProjectNameChange,
  onSubmit,
  projectName,
  selectedProducts,
  targetProduct,
  targetTags,
}: {
  customerDemand: string;
  isSubmitting: boolean;
  normalizedRatios: RatioMap;
  onBack: () => void;
  onProjectNameChange: (value: string) => void;
  onSubmit: () => void;
  projectName: string;
  selectedProducts: AkkProduct[];
  targetProduct: string;
  targetTags: string[];
}) {
  return (
    <Card className="min-h-[560px]">
      <CardTitle>生成内部研发建议书</CardTitle>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.8fr]">
        <div className="space-y-4">
          <label className="block">
            <span className="text-xs font-medium">建议书名称</span>
            <input
              className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm"
              onChange={(event) => onProjectNameChange(event.target.value)}
              value={projectName}
            />
          </label>
          <div className="rounded-lg border border-border bg-slate-50 p-4">
            <div className="text-sm font-semibold">即将写入建议书的内容</div>
            <div className="mt-3 grid gap-2 text-sm leading-6 text-slate-700">
              <div>目标产品：{targetProduct}</div>
              <div>客户需求：{customerDemand}</div>
              <div>研发对象：{selectedProducts.map((product) => `${product.productName} ${normalizedRatios[product.productId] || 0}%`).join("、")}</div>
              <div>目标标签：{targetTags.join("、")}</div>
            </div>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
            输出仍为内部研发实验建议，不是最终食品配方，也不是生产指令。正式推进前需要完成小试、中试、检测复核和人工审核。
          </div>
        </div>

        <div className="rounded-lg border border-border bg-white p-4">
          <div className="text-sm font-semibold">生成过程</div>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <div className="rounded-md bg-slate-50 px-3 py-2">读取已选产物档案</div>
            <div className="rounded-md bg-slate-50 px-3 py-2">整理比例、风险和验证指标</div>
            <div className="rounded-md bg-slate-50 px-3 py-2">检索知识库证据片段</div>
            <div className="rounded-md bg-slate-50 px-3 py-2">生成可回填的建议书记录</div>
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
  liveResult,
  normalizedRatios,
  projectName,
  selectedProducts,
  targetProduct,
  targetTags,
}: {
  activeStage: StageKey;
  liveResult: { fit: number; evidence: number; risk: number; readiness: number; coverage: number };
  normalizedRatios: RatioMap;
  projectName: string;
  selectedProducts: AkkProduct[];
  targetProduct: string;
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
        <div className="mt-1 text-xs text-muted-foreground">{targetProduct}</div>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <Metric label="匹配" value={liveResult.fit} />
          <Metric label="风险" value={liveResult.risk} />
        </div>
        <div className="mt-4">
          <div className="text-xs font-medium">当前组合</div>
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
        <CardTitle>目标标签</CardTitle>
        <div className="mt-3 flex flex-wrap gap-2">
          {targetTags.map((tag) => (
            <Badge key={tag} tone="success">{tag}</Badge>
          ))}
        </div>
        <p className="mt-4 text-xs leading-5 text-muted-foreground">
          当前推进准备度 {liveResult.readiness}/100。建议先检查证据风险，再生成建议书。
        </p>
      </Card>

      <Card>
        <CardTitle>适配场景</CardTitle>
        <div className="mt-3 flex flex-wrap gap-2">
          {Array.from(new Set(selectedProducts.flatMap((product) => product.recommendedApplications))).slice(0, 8).map((application) => (
            <span className="rounded-md bg-muted px-2 py-1 text-xs" key={application}>{formatApplication(application)}</span>
          ))}
        </div>
      </Card>
    </aside>
  );
}

function categoryShare(products: AkkProduct[], ratios: RatioMap, categories: string[]) {
  return products.reduce((sum, product) => {
    if (!categories.includes(product.productCategory)) return sum;
    return sum + (ratios[product.productId] || 0);
  }, 0);
}

function ScoreSurface({
  liveResult,
  products,
  ratios,
}: {
  liveResult: { fit: number; evidence: number; risk: number; readiness: number; coverage: number };
  products: AkkProduct[];
  ratios: RatioMap;
}) {
  const functionShare = categoryShare(products, ratios, ["postbiotic", "metabolite_blend", "fiber_complex"]);
  const substrateShare = categoryShare(products, ratios, [
    "algae_polysaccharide",
    "modified_algae_polysaccharide",
    "carrageenan_substrate",
    "algae_glycoprotein",
    "polysaccharide_control",
  ]);
  const protectionShare = categoryShare(products, ratios, ["encapsulation", "food_matrix", "prototype_product", "fermented_fiber"]);
  const x = Math.min(92, Math.max(8, functionShare + protectionShare * 0.35));
  const y = Math.min(88, Math.max(12, substrateShare + protectionShare * 0.45));
  const bestX = Math.min(82, Math.max(38, 52 + (liveResult.evidence - 75) * 0.4));
  const bestY = Math.min(78, Math.max(34, 48 + (liveResult.readiness - 78) * 0.35));
  const heatX = Math.min(72, Math.max(36, bestX));
  const heatY = Math.min(70, Math.max(30, bestY));
  const riskWidth = Math.min(34, Math.max(12, liveResult.risk * 0.28));

  return (
    <div className="mt-4 rounded-lg bg-slate-950 p-3 text-white">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">方案评分曲线</div>
          <div className="mt-1 text-[11px] leading-4 text-slate-300">
            横轴为功能对象占比，纵轴为底物与包埋支撑。比例变化会实时更新评分点位。
          </div>
        </div>
        <div className="rounded-md border border-white/15 px-2 py-1 text-xs font-semibold">{liveResult.fit}/100</div>
      </div>

      <div
        className="relative mt-3 aspect-[1.25] overflow-hidden rounded-md border border-white/10"
        style={{
          background: `
            radial-gradient(circle at ${heatX}% ${100 - heatY}%, rgba(250, 204, 21, 0.92) 0 8%, rgba(45, 212, 191, 0.72) 16%, rgba(15, 118, 110, 0.5) 34%, rgba(30, 64, 175, 0.58) 62%, rgba(15, 23, 42, 0.96) 100%),
            linear-gradient(90deg, rgba(148, 163, 184, 0.12) 1px, transparent 1px),
            linear-gradient(0deg, rgba(148, 163, 184, 0.12) 1px, transparent 1px)
          `,
          backgroundSize: "100% 100%, 20% 20%, 20% 20%",
        }}
      >
        <div
          className="absolute inset-y-0 right-0 opacity-40"
          style={{
            width: `${riskWidth}%`,
            background: "repeating-linear-gradient(45deg, rgba(248,113,113,0.85) 0 8px, rgba(248,113,113,0.25) 8px 16px)",
          }}
        />
        <Point label="理论高分区" tone="best" x={bestX} y={bestY} />
        <Point label="当前方案" tone="current" x={x} y={y} />
        <div className="absolute bottom-2 left-2 rounded bg-slate-950/70 px-2 py-1 text-[10px] text-slate-200">低支撑</div>
        <div className="absolute right-2 top-2 rounded bg-slate-950/70 px-2 py-1 text-[10px] text-slate-200">风险升高区</div>
      </div>

      <div className="mt-2 grid grid-cols-3 gap-2 text-[11px] text-slate-300">
        <div>功能对象 {Math.round(functionShare)}%</div>
        <div>底物证据 {Math.round(substrateShare)}%</div>
        <div>包埋支撑 {Math.round(protectionShare)}%</div>
      </div>
    </div>
  );
}

function Point({ label, tone, x, y }: { label: string; tone: "best" | "current"; x: number; y: number }) {
  const color = tone === "best" ? "bg-yellow-300 ring-yellow-100" : "bg-emerald-300 ring-white";
  return (
    <div className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${x}%`, top: `${100 - y}%` }}>
      <div className={`h-3.5 w-3.5 rounded-full ${color} ring-4 shadow-lg`} />
      <div className="mt-1 whitespace-nowrap rounded bg-slate-950/75 px-1.5 py-0.5 text-[10px] text-white">{label}</div>
    </div>
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
          <div className="text-xs text-muted-foreground">配比对象</div>
          <div className="text-lg font-semibold">{products.length} 个</div>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-white p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}
