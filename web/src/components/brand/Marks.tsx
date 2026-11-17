/** Pictos partagés contact / footer (trait orange ou cream selon parent). */

const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function PinMark({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path {...stroke} d="M12 21s-6-5.4-6-10a6 6 0 1 1 12 0c0 4.6-6 10-6 10z" />
      <circle {...stroke} cx="12" cy="11" r="2.2" />
    </svg>
  );
}

export function CalendarMark({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <rect {...stroke} x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path {...stroke} d="M8 3.5v3M16 3.5v3M3.5 10h17" />
    </svg>
  );
}

export function BagMark({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path {...stroke} d="M6 8h12l-1 12H7L6 8z" />
      <path {...stroke} d="M9 8V6.5a3 3 0 0 1 6 0V8" />
    </svg>
  );
}

export function ArrowMark({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path {...stroke} d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export function InstagramMark({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <rect {...stroke} x="3.5" y="3.5" width="17" height="17" rx="4.5" />
      <circle {...stroke} cx="12" cy="12" r="4" />
      <circle fill="currentColor" stroke="none" cx="17.2" cy="6.8" r="1.1" />
    </svg>
  );
}

export function InfoMark({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <circle {...stroke} cx="12" cy="12" r="8.5" />
      <path {...stroke} d="M12 11v5.5M12 8h.01" />
    </svg>
  );
}

export function PlaneMark({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path {...stroke} d="M21 3 10.5 13.5M21 3l-6.5 18-4-7.5L3 9.5 21 3z" />
    </svg>
  );
}
