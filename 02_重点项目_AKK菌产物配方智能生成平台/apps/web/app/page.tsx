import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { getAkkProducts, getFormulaResults, getKnowledgeItems, getLlmStatus } from "@/lib/api";

const quickStarts = [
  {
    title: "新建商品配方",
    desc: "输入目标商品类型，由知识库和本地 LLM 生成 AKK 配比、理由、风险和实验建议。",
    href: "/formula/new",
    cta: "进入配方设计台",
    tone: "primary",
  },
  {
    title: "查看文献知识库",
    desc: "检索 AKK 安全性、法规、乳基应用、后生元和机制证据，查看引用片段。",
    href: "/knowledge",
    cta: "检索知识库",
    tone: "plain",
  },
  {
    title: "管理打样实验",
    desc: "查看方案生成后的稳定性、感官、标志物和风险验证数据。",
    href: "/experiments",
    cta: "查看实验平台",
    tone: "plain",
  },
  {
    title: "复用历史方案",
    desc: "从已生成方案中找配方、建议书和审核状态，便于后续共创升级。",
    href: "/formula/results",
    cta: "打开方案库",
    tone: "plain",
  },
];

export default async function HomePage() {
  const [products, results, knowledgeItems, llmStatus] = await Promise.all([
    getAkkProducts(),
    getFormulaResults().catch(() => []),
    getKnowledgeItems("AKK 后生元 安全 酸奶").catch(() => []),
    getLlmStatus().catch(() => undefined),
  ]);

  const highEvidence = knowledgeItems.filter((item) => ["A", "B"].includes(item.evidenceLevel)).length;
  const pendingResults = results.filter((result) =>
    result.candidates.some((candidate) => candidate.approvalStatus === "pending_research_review"),
  ).length;
  const latest = results.slice(0, 4);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <section className="rounded-2xl border border-emerald-100 bg-white p-6 shadow-sm">
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="success">内部研发版</Badge>
              <Badge tone={llmStatus?.available ? "success" : "warning"}>
                {llmStatus?.available ? `本地模型已连接：${llmStatus.model}` : "规则模板模式"}
              </Badge>
            </div>
            <h1 className="mt-4 text-3xl font-semibold tracking-normal text-slate-950">AKK 商品方案共创平台</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              为下游食品品牌提供 AKK 原料选型、商品概念设计、论文证据引用、预测风险和实验验证建议。
              首页只保留入口和状态，复杂操作放在独立页面中完成。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <ButtonLink href="/formula/new">开始设计配方</ButtonLink>
              <ButtonLink href="/formula/results" variant="secondary">查看方案库</ButtonLink>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Metric label="AKK 原料" value={products.length} helper="可参与配方设计" />
            <Metric label="知识证据" value={knowledgeItems.length} helper={`${highEvidence} 条 A/B 级`} />
            <Metric label="已生成方案" value={results.length} helper="含本地归档" />
            <Metric label="待验证方案" value={pendingResults} helper="需打样复核" />
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        {quickStarts.map((item) => (
          <Card className={item.tone === "primary" ? "border-emerald-200 bg-emerald-50" : ""} key={item.href}>
            <CardTitle>{item.title}</CardTitle>
            <p className="mt-3 min-h-20 text-xs leading-6 text-muted-foreground">{item.desc}</p>
            <ButtonLink className="mt-4 w-full justify-center" href={item.href} variant={item.tone === "primary" ? "primary" : "secondary"}>
              {item.cta}
            </ButtonLink>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>推荐体验路径</CardTitle>
            <Badge>3 步</Badge>
          </div>
          <div className="mt-4 space-y-3">
            <Step index="01" title="输入目标商品" desc="例如低糖肠道健康酸奶、儿童软糖、银发营养粉或运动即饮饮料。" />
            <Step index="02" title="智能推荐配比" desc="系统根据商品形态、客户需求、AKK 原料属性和知识库证据给出初始比例。" />
            <Step index="03" title="生成建议书" desc="输出配比理由、知识库引用、风险预测、实验验证项目和升级建议。" />
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>最近方案</CardTitle>
            <Link className="text-xs font-medium text-primary" href="/formula/results">查看全部</Link>
          </div>
          <div className="mt-4 divide-y divide-border overflow-hidden rounded-lg border border-border">
            {latest.length ? (
              latest.map((result) => {
                const candidate = result.candidates[0];
                return (
                  <Link
                    className="block bg-white px-4 py-3 text-sm hover:bg-emerald-50"
                    href={`/formula/results/${result.resultId}`}
                    key={result.resultId}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium text-slate-950">{candidate?.candidateName ?? result.applicationName}</span>
                      <Badge>{candidate?.approvalStatus ?? "pending"}</Badge>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">{result.applicationName} · {new Date(result.createdAt).toLocaleString("zh-CN")}</div>
                  </Link>
                );
              })
            ) : (
              <div className="px-4 py-8 text-sm text-muted-foreground">还没有生成方案，先进入配方设计台创建第一个方案。</div>
            )}
          </div>
        </Card>
      </section>
    </div>
  );
}

function Metric({ label, value, helper }: { label: string; value: number; helper: string }) {
  return (
    <div className="rounded-xl border border-border bg-slate-50 p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-slate-950">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{helper}</div>
    </div>
  );
}

function Step({ index, title, desc }: { index: string; title: string; desc: string }) {
  return (
    <div className="grid grid-cols-[44px_1fr] gap-3 rounded-lg border border-border bg-white p-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-xs font-semibold text-primary">{index}</div>
      <div>
        <div className="text-sm font-semibold text-slate-950">{title}</div>
        <div className="mt-1 text-xs leading-5 text-muted-foreground">{desc}</div>
      </div>
    </div>
  );
}
