import type { ReactNode } from "react";

export function QuoteBand({ children }: { children: ReactNode }) {
  return (
    <section className="bg-paper px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
      <div className="mx-auto max-w-[68rem] rounded-2xl bg-night px-5 py-4 text-cream sm:rounded-3xl sm:px-7 sm:py-5 lg:px-8 lg:py-6">
        <div className="flex items-start gap-3 sm:gap-5">
          <span
            className="shrink-0 font-display text-[2.35rem] leading-none text-terracotta sm:text-[3rem]"
            aria-hidden="true"
          >
            “
          </span>
          <p className="min-w-0 pt-1 text-[0.98rem] font-medium leading-[1.55] tracking-[-0.01em] text-cream sm:text-[1.1rem] sm:leading-[1.5] lg:text-[1.2rem]">
            {children}
          </p>
        </div>
      </div>
    </section>
  );
}
