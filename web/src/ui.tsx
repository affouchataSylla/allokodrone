import { useEffect, type ReactNode } from "react";
import { Link } from "react-router";

export const btn =
  "inline-flex min-h-10 items-center justify-center rounded-xl border border-cream/80 bg-terracotta px-5 text-sm font-semibold tracking-wide text-cream transition-colors duration-300 hover:bg-terracotta-deep disabled:cursor-not-allowed disabled:opacity-40";
export const btnGhost =
  "inline-flex min-h-10 items-center justify-center rounded-xl border border-cream/75 bg-transparent px-5 text-sm font-semibold tracking-wide text-cream transition-colors duration-300 hover:border-cream hover:bg-cream/5 disabled:opacity-40";
export const btnLine =
  "inline-flex min-h-10 items-center justify-center rounded-xl border border-ink/30 bg-cream px-5 text-sm font-semibold tracking-wide text-ink transition-colors duration-300 hover:border-ink disabled:opacity-40";
export const input =
  "min-h-12 w-full rounded-xl border border-line bg-cream px-3 text-base text-ink outline-none";
export const field = "mt-4 flex flex-col gap-1.5 text-sm";

export function useTitle(title: string) {
  useEffect(() => {
    document.title = `${title} — ALLOKODRONE`;
  }, [title]);
}

export function money(cents: number) {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  return `${sign}${Math.floor(abs / 100)},${String(abs % 100).padStart(2, "0")} €`;
}

export function Pending({ label = "Chargement" }: { label?: string }) {
  return (
    <p className="py-8 text-sm text-ink-soft" role="status">
      {label}…
    </p>
  );
}

export function Alert({ errors }: { errors: string[] }) {
  if (!errors.length) return null;
  return (
    <div className="border-l-2 border-terracotta-deep bg-paper-2 px-4 py-3 text-sm" role="alert">
      <ul className="space-y-1">
        {errors.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
    </div>
  );
}

export function Quantity({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="inline-flex items-center overflow-hidden rounded-xl border border-line bg-cream">
      <button
        className="h-12 w-12 text-lg disabled:opacity-40"
        type="button"
        aria-label="Diminuer la quantité"
        disabled={disabled || value <= 1}
        onClick={() => onChange(value - 1)}
      >
        −
      </button>
      <input
        className="h-12 w-12 bg-transparent text-center text-base outline-none"
        inputMode="numeric"
        aria-label="Quantité"
        value={value}
        disabled={disabled}
        onChange={(event) => {
          const next = Number(event.target.value);
          if (Number.isFinite(next)) onChange(Math.min(20, Math.max(1, next)));
        }}
      />
      <button
        className="h-12 w-12 text-lg disabled:opacity-40"
        type="button"
        aria-label="Augmenter la quantité"
        disabled={disabled || value >= 20}
        onClick={() => onChange(value + 1)}
      >
        +
      </button>
    </div>
  );
}

export function Photo({ src, alt, className }: { src: string; alt: string; className?: string }) {
  return <img className={className} src={src} alt={alt} loading="lazy" />;
}

export function Reveal({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={`reveal ${className}`}>{children}</div>;
}

export function Empty({ title, text, to, label }: { title: string; text: string; to: string; label: string }) {
  return (
    <div className="border-t border-line py-7">
      <h2 className="font-display text-3xl">{title}</h2>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-soft">{text}</p>
      <Link className={`${btn} mt-4`} to={to}>
        {label}
      </Link>
    </div>
  );
}
