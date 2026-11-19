import { Link } from "react-router";
import type { TrackedOrder } from "./types";
import { btnLine } from "./ui";

function when(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    timeZone: "Europe/Paris",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function TrackSteps({ events }: { events: { status: string; label?: string; at: string }[] }) {
  if (!events.length) return null;
  return (
    <ol className="mt-4">
      {events.map((event, index) => {
        const current = index === events.length - 1;
        return (
          <li key={`${event.at}-${index}`} className="grid grid-cols-[0.75rem_minmax(0,1fr)] gap-3">
            <span className="flex flex-col items-center">
              <span className={`mt-1.5 h-2 w-2 shrink-0 ${current ? "bg-terracotta" : "bg-saffron"}`} />
              {current ? null : <span className="mt-1 w-px flex-1 bg-line" />}
            </span>
            <span className={`flex items-baseline justify-between gap-3 pb-3 text-sm ${current ? "font-medium text-ink" : "text-ink-soft"}`}>
              <span>{event.label || event.status}</span>
              <time className="shrink-0 text-xs tabular-nums" dateTime={event.at}>{when(event.at)}</time>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function TrackCards({ orders }: { orders: TrackedOrder[] }) {
  if (!orders.length) return null;
  return (
    <section className="mt-8" aria-label="Suivi">
      <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Suivi</p>
      <div className={orders.length > 1 ? "mt-4 grid items-start gap-4 md:grid-cols-2" : "mt-4"}>
        {orders.map((order) => (
          <article key={order.ref} className="border border-line bg-cream p-5">
            <div className="flex items-start justify-between gap-3">
              <h2 className="font-display text-2xl leading-none">
                <Link className="hover:text-terracotta" to={`/commande/${order.ref}`}>{order.ref}</Link>
              </h2>
              <span className="shrink-0 bg-terracotta px-2 py-1 text-xs font-medium uppercase tracking-[0.12em] text-cream">{order.statusLabel}</span>
            </div>
            <ul className="mt-4 border-t border-line text-sm">
              {order.lines.map((line) => (
                <li key={`${order.ref}-${line.name}`} className="flex items-baseline justify-between gap-3 border-b border-line py-2">
                  <span>{line.name} × {line.quantity}</span>
                  <span className="shrink-0 tabular-nums">{line.lineLabel}</span>
                </li>
              ))}
            </ul>
            <dl className="mt-3 text-sm text-ink-soft">
              <div className="flex justify-between py-0.5"><dt>Sous-total</dt><dd className="tabular-nums">{order.subtotalLabel}</dd></div>
              <div className="flex justify-between py-0.5"><dt>Livraison</dt><dd className="tabular-nums">{order.deliveryLabel}</dd></div>
              <div className="flex justify-between py-0.5"><dt>Réduction</dt><dd className="tabular-nums">{order.discountLabel}</dd></div>
              <div className="mt-2 flex justify-between border-t border-line pt-2 font-medium text-ink"><dt>Total</dt><dd className="tabular-nums text-terracotta">{order.totalLabel}</dd></div>
            </dl>
            <TrackSteps events={order.events} />
            <div className="mt-4">
              <a className={`${btnLine} w-full`} href={`/api/commande/${encodeURIComponent(order.ref)}/pdf`}>Télécharger le PDF</a>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
