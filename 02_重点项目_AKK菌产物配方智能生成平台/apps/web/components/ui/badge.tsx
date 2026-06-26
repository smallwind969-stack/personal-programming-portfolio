import { ReactNode } from "react";

const toneClass = {
  default: "border-slate-200 bg-white text-slate-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-red-200 bg-red-50 text-red-800",
};

export function Badge({
  children,
  className = "",
  tone = "default",
}: {
  children: ReactNode;
  className?: string;
  tone?: keyof typeof toneClass;
}) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${toneClass[tone]} ${className}`}>
      {children}
    </span>
  );
}
