import type { ReactNode } from "react";

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="terminal-shell">
      <a className="focus-ring sr-only focus:not-sr-only" href="#main-content">跳转到主内容</a>
      <aside className="terminal-sidebar">
        <a className="terminal-brand" href="/decision">
          <span>启</span>
          <div><strong>菌藻启元</strong><small>智能产线控制终端</small></div>
        </a>
        <nav aria-label="主导航">
          <a className="active" href="/decision"><span>01</span>生产决策</a>
          <a href="/experiments"><span>02</span>实验资产</a>
          <a href="/runs"><span>03</span>运行记录</a>
          <a href="/knowledge-assets"><span>04</span>知识资产</a>
          <a href="/model-assets"><span>05</span>模型资产</a>
          <a href="/human-actions"><span>06</span>人工确认</a>
        </nav>
        <div className="terminal-account">
          <span>系统在线</span><strong>管理员</strong><small>菌藻启元研发中心</small>
        </div>
      </aside>
      <main className="terminal-main" id="main-content">{children}</main>
    </div>
  );
}
