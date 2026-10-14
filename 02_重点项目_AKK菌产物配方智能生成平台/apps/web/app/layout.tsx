import type { Metadata } from "next";

import { AppLayout } from "@/components/layout/app-layout";
import "./globals.css";

export const metadata: Metadata = {
  title: "菌藻启元｜智能产线控制终端",
  description: "自然语言需求驱动的菌藻产线智能决策与仿真优化平台",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body suppressHydrationWarning><AppLayout>{children}</AppLayout></body>
    </html>
  );
}
