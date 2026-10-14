import Link from "next/link";

export function BrandHeader() {
  return (
    <header className="border-b border-[#dde4df] bg-white">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center px-5 lg:px-8">
        <Link
          className="focus-ring flex items-center gap-3 rounded-lg"
          href="/"
        >
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#173e32] font-semibold text-white shadow-[0_7px_18px_rgba(23,62,50,0.18)]">
            启
          </span>
          <span className="font-semibold tracking-[-0.01em] text-[#173e32]">
            菌藻启元
          </span>
        </Link>
        <span aria-hidden className="mx-5 h-6 w-px bg-slate-200" />
        <span className="text-lg font-semibold tracking-[-0.02em] text-slate-900">
          智能产线控制终端
        </span>
      </div>
    </header>
  );
}
