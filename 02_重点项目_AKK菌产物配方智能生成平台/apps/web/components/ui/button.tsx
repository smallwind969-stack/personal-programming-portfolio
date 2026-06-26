import Link from "next/link";
import { ButtonHTMLAttributes, ReactNode } from "react";

const variantClass = {
  primary: "bg-primary text-primary-foreground hover:bg-[#1f665f]",
  secondary: "border border-border bg-white text-slate-800 hover:bg-muted",
};

export function Button({
  children,
  className = "",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: keyof typeof variantClass;
}) {
  return (
    <button
      className={`focus-ring rounded-md px-4 py-2 text-sm font-medium disabled:opacity-60 ${variantClass[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function ButtonLink({
  children,
  className = "",
  href,
  variant = "primary",
}: {
  children: ReactNode;
  className?: string;
  href: string;
  variant?: keyof typeof variantClass;
}) {
  return (
    <Link
      className={`focus-ring inline-flex rounded-md px-4 py-2 text-sm font-medium ${variantClass[variant]} ${className}`}
      href={href}
    >
      {children}
    </Link>
  );
}
