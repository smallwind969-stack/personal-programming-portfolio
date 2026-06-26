import { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`rounded-lg border border-border bg-white p-4 shadow-sm ${className}`}>{children}</section>;
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-sm font-semibold text-slate-950">{children}</h2>;
}
