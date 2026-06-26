import Link from "next/link";
import { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

const navItems = [
  { href: "/", label: "平台首页", desc: "入口与总览" },
  { href: "/formula/new", label: "配方设计台", desc: "自定义商品生成" },
  { href: "/products", label: "AKK 原料库", desc: "原料性质与风险" },
  { href: "/knowledge", label: "文献知识库", desc: "论文证据检索" },
  { href: "/experiments", label: "实验平台", desc: "打样验证数据" },
  { href: "/formula/results", label: "商品方案库", desc: "历史方案归档" },
  { href: "/demo", label: "项目介绍", desc: "路演说明" },
];

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f4f7f5] text-slate-950">
      <aside className="fixed left-0 top-0 hidden h-screen w-72 border-r border-emerald-100 bg-white/95 px-5 py-6 shadow-sm md:block">
        <Link className="block rounded-2xl bg-[#0d6b61] p-4 text-white transition hover:bg-[#09594f]" href="/">
          <div className="text-lg font-semibold">AKK 商品方案平台</div>
          <div className="mt-2 text-xs leading-5 text-emerald-50">
            面向中游 AKK 原料供应商与下游品牌方的商品共创工作台。
          </div>
        </Link>

        <nav className="mt-7 space-y-1">
          {navItems.map((item) => (
            <Link
              className="focus-ring group block rounded-xl px-3 py-3 text-sm text-slate-700 hover:bg-emerald-50 hover:text-primary"
              href={item.href}
              key={item.href}
            >
              <div className="font-medium">{item.label}</div>
              <div className="mt-0.5 text-[11px] text-slate-400 group-hover:text-emerald-700">{item.desc}</div>
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-6 left-5 right-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <Badge tone="success">内部方案设计版</Badge>
          <p className="mt-3 text-xs leading-5 text-emerald-950">
            输出用于商品概念、打样沟通和实验计划，不作为上市最终配方。
          </p>
        </div>
      </aside>

      <header className="border-b border-emerald-100 bg-white px-4 py-4 md:hidden">
        <Link className="font-semibold text-primary" href="/">AKK 商品方案平台</Link>
        <nav className="mt-3 flex gap-2 overflow-x-auto text-sm">
          {navItems.map((item) => (
            <Link className="shrink-0 rounded-md border border-border px-3 py-2" href={item.href} key={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="px-4 py-6 md:ml-72 md:px-8">
        {children}
        <footer className="mt-8 border-t border-emerald-100 pt-4 text-xs text-muted-foreground">
          本平台用于中游 AKK 原料供应商与下游品牌方的商品方案共创。所有结果仍需通过打样、稳定性、感官和合规审核确认。
        </footer>
      </main>
    </div>
  );
}
