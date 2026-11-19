import { TriangleMark } from "./icons";

export type ConceptValue = {
  title: string;
  body: string;
};

export function ValueGrid({ values }: { values: readonly ConceptValue[] }) {
  return (
    <section className="mx-auto max-w-[78rem] px-4 pb-6 sm:px-6 sm:pb-8 lg:px-8 lg:pb-10">
      <ul className="divide-y divide-line border-y border-line sm:grid sm:grid-cols-3 sm:gap-6 sm:divide-y-0 sm:border-0 lg:gap-8">
        {values.map((value) => (
          <li key={value.title} className="flex gap-3 py-4 first:pt-4 last:pb-4 sm:py-0">
            <TriangleMark />
            <div className="min-w-0">
              <h2 className="font-display text-[1.2rem] font-semibold leading-tight tracking-[-0.02em] text-ink sm:text-[1.45rem]">
                {value.title}
              </h2>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-soft sm:mt-2.5 sm:text-[0.95rem] sm:leading-[1.6]">
                {value.body}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
