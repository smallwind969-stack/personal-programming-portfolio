import type { Metadata } from "next";

import { AppLayout } from "@/components/layout/app-layout";
import "./globals.css";

export const metadata: Metadata = {
  title: "AKK 商品方案平台",
  description: "面向下游食品品牌方的 AKK 原料商品设计工作台",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  );
}
