import { getKnowledgeChunks, getKnowledgeItems } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";

const evidenceTone = {
  A: "success",
  B: "warning",
  C: "default",
  D: "default",
} as const;

const typeLabel: Record<string, string> = {
  regulatory: "法规/备案",
  human_clinical: "人体临床",
  toxicology_safety: "毒理安全",
  patent: "专利",
  food_application: "食品应用",
  strain_culture: "菌株/培养",
  mechanism_or_basic_research: "机制研究",
  review: "综述",
};

export default async function KnowledgePage({
  searchParams,
}: {
  searchParams?: Promise<{ query?: string }>;
}) {
  const params = await searchParams;
  const query = params?.query?.trim() || "低糖酸奶 AKK";
  const [items, chunks] = await Promise.all([getKnowledgeItems(query), getKnowledgeChunks(query)]);
  const total = items.length;
  const highEvidence = items.filter((item) => ["A", "B"].includes(item.evidenceLevel)).length;
  const safetyItems = items.filter((item) => item.topics.includes("safety") || item.topics.includes("regulatory")).length;
  const foodItems = items.filter((item) => item.topics.includes("food_application") || item.topics.includes("dairy_matrix")).length;

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs font-medium text-primary">论文知识库 + 混合检索 + 引用依据</div>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">AKK 文献知识库</h1>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          当前知识库来自本地收集的 AKK 安全性、临床、法规、专利、产品案例、食品应用、培养条件和代谢产物资料。
          检索会综合语义向量、关键词、食品基质、证据等级、年份、安全法规优先级和业务边界，供配方生成时引用。
        </p>
      </div>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="召回证据卡片" value={total} />
        <Metric label="A/B 级证据" value={highEvidence} />
        <Metric label="安全/法规资料" value={safetyItems} />
        <Metric label="食品应用资料" value={foodItems} />
      </section>

      <Card>
        <CardTitle>检索示例</CardTitle>
        <div className="mt-3 flex flex-wrap gap-2">
          {["低糖酸奶", "AKK 复配牛奶", "儿童软糖安全", "银发营养粉", "膳食纤维 多糖", "法规 NDI", "毒理安全"].map((example) => (
            <a className="rounded-md border border-border bg-white px-3 py-2 text-xs hover:bg-emerald-50" href={`/knowledge?query=${encodeURIComponent(example)}`} key={example}>
              {example}
            </a>
          ))}
        </div>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardTitle>高相关论文片段</CardTitle>
          <div className="mt-3 space-y-3">
            {chunks.map((chunk) => (
              <div className="rounded-lg border border-border bg-slate-50 p-3" key={chunk.chunkId}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold text-slate-950">{chunk.title}</div>
                  <Badge tone={evidenceTone[chunk.evidenceLevel as keyof typeof evidenceTone] ?? "default"}>
                    {chunk.evidenceLevel} / {chunk.retrievalScore?.toFixed(1)}
                  </Badge>
                </div>
                <p className="mt-2 line-clamp-4 text-xs leading-5 text-slate-700">{chunk.text}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {chunk.matchReasons.slice(0, 3).map((reason) => (
                    <Badge key={reason}>{reason}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          {items.slice(0, 10).map((item) => (
            <Card key={item.knowledgeId}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <CardTitle>{item.title}</CardTitle>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {item.sourceName}
                    {item.year ? ` · ${item.year}` : ""}
                    {item.evidenceType ? ` · ${typeLabel[item.evidenceType] ?? item.evidenceType}` : ""}
                  </p>
                </div>
                <Badge tone={evidenceTone[item.evidenceLevel as keyof typeof evidenceTone] ?? "default"}>
                  证据等级 {item.evidenceLevel}
                </Badge>
              </div>

              <div className="mt-3 rounded-lg bg-slate-50 p-3">
                <div className="text-xs font-semibold text-slate-800">检索得分 {item.retrievalScore?.toFixed(1) ?? "-"}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {item.matchReasons.slice(0, 5).map((reason) => (
                    <Badge key={reason}>{reason}</Badge>
                  ))}
                </div>
              </div>

              <p className="mt-3 text-sm leading-6 text-slate-700">{item.summary}</p>

              {item.keyPassages.length ? (
                <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50 p-3">
                  <div className="text-xs font-semibold text-emerald-800">可引用片段</div>
                  <p className="mt-2 text-xs leading-5 text-slate-700">{item.keyPassages[0]}</p>
                </div>
              ) : null}

              <div className="mt-3 flex flex-wrap gap-2">
                {item.topics.slice(0, 6).map((topic) => (
                  <Badge key={topic}>{topic}</Badge>
                ))}
                {item.foodMatrix.map((matrix) => (
                  <Badge tone="success" key={matrix}>{matrix}</Badge>
                ))}
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <InfoBlock title="支持的配方判断" tone="green" items={item.usableInsights.slice(0, 3)} />
                <InfoBlock title="风险与边界" tone="amber" items={item.riskNotes.slice(0, 3)} />
              </div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-white p-4 shadow-sm">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function InfoBlock({ title, items, tone }: { title: string; items: string[]; tone: "green" | "amber" }) {
  const styles = tone === "green" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800";
  return (
    <div className={`rounded-lg p-3 ${styles}`}>
      <div className="text-xs font-semibold">{title}</div>
      <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
        {items.map((item) => (
          <li key={item}>· {item}</li>
        ))}
      </ul>
    </div>
  );
}
