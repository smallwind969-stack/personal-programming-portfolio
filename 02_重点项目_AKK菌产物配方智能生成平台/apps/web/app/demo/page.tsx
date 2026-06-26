import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";

const highlights = [
  {
    title: "论文知识库驱动",
    text: "把本地收集的 AKK 安全性、临床、法规、专利和食品应用资料转化为证据卡片与可引用片段。",
  },
  {
    title: "混合检索增强",
    text: "结合语义向量、关键词、食品基质、证据等级、安全法规优先级和业务边界，提升命中率与可解释性。",
  },
  {
    title: "配方生成闭环",
    text: "从自定义商品需求出发，生成 AKK 原料比例、协同辅料、风险预测、验证指标和商品方案建议书。",
  },
  {
    title: "本地大模型可插拔",
    text: "支持 Ollama 本地模型作为 RAG 智能体增强；模型不可用时自动回退到规则模板，保证演示稳定。",
  },
];

const flow = [
  "输入目标商品类型与客户需求",
  "智能体识别食品场景与卖点标签",
  "检索 AKK 文献知识库和关键片段",
  "生成 AKK 原料比例与协同辅料建议",
  "输出风险提示、验证指标和研发方案报告",
  "方案归档到商品方案库，后续可继续升级",
];

export default function DemoPage() {
  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-emerald-100 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap gap-2">
          <Badge tone="success">大创项目展示版</Badge>
          <Badge>AKK 菌产物</Badge>
          <Badge>RAG 知识库</Badge>
          <Badge>食品研发共创</Badge>
        </div>
        <h1 className="mt-4 text-3xl font-semibold text-slate-950">AKK 菌产物智能配方与商品方案共创平台</h1>
        <p className="mt-3 max-w-4xl text-sm leading-7 text-muted-foreground">
          本项目面向中游 AKK 菌产物供应方和下游食品品牌，解决 AKK 相关论文、法规、产品案例和实验假设分散的问题。
          平台帮助研发人员快速完成商品概念设计、原料比例建议、知识库引用、风险预测和实验验证规划。
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <ButtonLink href="/" variant="primary">进入商品设计台</ButtonLink>
          <ButtonLink href="/knowledge" variant="secondary">查看文献知识库</ButtonLink>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        {highlights.map((item) => (
          <Card key={item.title}>
            <CardTitle>{item.title}</CardTitle>
            <p className="mt-3 text-sm leading-6 text-slate-700">{item.text}</p>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardTitle>项目背景与痛点</CardTitle>
          <div className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            <p>AKK 菌是肠道健康和代谢健康方向的重要研究对象，后生元、代谢产物和相关结构组分具备食品研发潜力。</p>
            <p>下游品牌在实际开发中会遇到三个问题：资料分散、配方试错成本高、合规和验证边界不清晰。</p>
            <p>本平台把论文资料、产品知识、配方规则和实验验证建议集中到一个可交互工作台中。</p>
          </div>
        </Card>

        <Card>
          <CardTitle>关键技术路线</CardTitle>
          <ol className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            {flow.map((item, index) => (
              <li className="flex gap-3" key={item}>
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-emerald-100 text-xs font-semibold text-emerald-800">
                  {index + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ol>
        </Card>
      </section>

      <Card>
        <CardTitle>评委演示建议</CardTitle>
        <div className="mt-3 grid gap-3 text-sm leading-6 text-slate-700 md:grid-cols-3">
          <div className="rounded-lg bg-slate-50 p-3">
            <div className="font-semibold text-slate-950">第一步：讲需求</div>
            <p className="mt-2">在商品设计台输入“低糖酸奶、儿童软糖、银发营养粉”等任意目标商品。</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <div className="font-semibold text-slate-950">第二步：看生成</div>
            <p className="mt-2">点击智能推荐配方，再生成商品方案，观察比例、风险和知识库引用。</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <div className="font-semibold text-slate-950">第三步：讲闭环</div>
            <p className="mt-2">进入方案报告和方案库，说明后续可接真实实验数据、审核流和客户共创数据库。</p>
          </div>
        </div>
      </Card>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-900">
        边界声明：当前平台用于内部研发和大创项目演示，所有结果均为研发实验建议，不是最终上市配方，不替代真实毒理、临床、法规和稳定性验证。
      </div>
    </div>
  );
}
