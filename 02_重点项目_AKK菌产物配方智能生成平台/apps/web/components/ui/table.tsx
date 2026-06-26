import { ReactNode } from "react";

export function DataTable({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-white">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">{children}</table>
    </div>
  );
}

export function Th({ children }: { children: ReactNode }) {
  return <th className="border-b border-border bg-muted px-4 py-3 text-xs font-semibold uppercase text-muted-foreground">{children}</th>;
}

export function Td({ children }: { children: ReactNode }) {
  return <td className="border-b border-border px-4 py-4 align-top text-slate-700">{children}</td>;
}
