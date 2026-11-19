import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api, ApiError } from "../api";
import type { OrderPayload } from "../types";
import { TrackSteps } from "../Tracking";
import { btn, btnLine, Pending, useTitle } from "../ui";

export function Order() {
  const { ref = "" } = useParams();
  const [order, setOrder] = useState<OrderPayload | null>(null);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  useTitle(order ? `Commande ${order.ref}` : "Commande");

  useEffect(() => {
    let cancel = false;
    api<OrderPayload>(`/api/commande/${ref}`)
      .then((payload) => {
        if (!cancel) setOrder(payload);
      })
      .catch((reason: unknown) => {
        if (cancel) return;
        if (reason instanceof ApiError && reason.status === 404) setMissing(true);
        else setError(reason instanceof ApiError ? reason.message : "Connexion interrompue. Réessayez.");
      });
    return () => {
      cancel = true;
    };
  }, [ref]);

  if (missing) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="font-display text-4xl">Commande introuvable</h1>
        <Link className={`${btn} mt-6`} to="/compte">Voir le compte</Link>
      </div>
    );
  }
  if (!order) return <div className="mx-auto max-w-3xl px-4">{error ? <p className="py-7 text-sm" role="alert">{error}</p> : <Pending />}</div>;

  return (
    <article className="mx-auto max-w-3xl px-4 py-7">
      <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Confirmation</p>
      <h1 className="mt-3 font-display text-5xl leading-none">Commande {order.ref}</h1>
      <p className="mt-5 border-l-2 border-saffron bg-paper-2 px-4 py-3 text-sm">
        {order.confirmedByProvider
          ? `${order.paymentLabel}. Stripe a confirmé l'encaissement de cette commande.`
          : order.paymentStatus === "refunded"
            ? `${order.paymentLabel}. Stripe a confirmé le remboursement.`
          : order.paymentStatus === "paid"
            ? `${order.paymentLabel}. Le restaurant a enregistré l'encaissement. Aucun paiement en ligne n'a été utilisé.`
          : order.paymentStatus === "pending"
            ? `${order.paymentLabel}. L'arrivée sur une page ne confirme pas le paiement.`
            : order.paymentStatus === "failed" || order.paymentStatus === "cancelled"
              ? `${order.paymentLabel}. ${order.paymentMethodLabel || "Paiement en ligne"}.`
              : `${order.paymentLabel}. Mode prévu : ${order.paymentMethodLabel || order.paymentMethod}. Aucun prestataire de paiement n'a confirmé d'encaissement.`}
      </p>
      {order.canRetry ? (
        <button
          className={`${btn} mt-4`}
          type="button"
          disabled={pending}
          onClick={() => {
            setPending(true);
            setError("");
            api<{ checkoutUrl: string }>("/api/paiement/reessayer", { method: "POST", body: { ref: order.ref } })
              .then((result) => window.location.assign(result.checkoutUrl))
              .catch((reason: unknown) => {
                setPending(false);
                setError(reason instanceof ApiError ? reason.message : "Connexion interrompue. Réessayez.");
              });
          }}
        >
          {pending ? "Paiement en cours…" : "Réessayer le paiement"}
        </button>
      ) : null}
      {error ? <p className="mt-3 text-sm" role="alert">{error}</p> : null}
      <ul className="mt-6 border-t border-line">
        {order.lines.map((line) => (
          <li key={`${line.name}-${line.options}`} className="border-b border-line py-3">
            <strong>{line.name}</strong> × {line.quantity} — {line.lineLabel}
            {line.options ? <span className="mt-1 block text-sm text-ink-soft">{line.options}</span> : null}
          </li>
        ))}
      </ul>
      <h2 className="mt-6 font-display text-2xl">Récapitulatif</h2>
      <dl className="mt-3 border-y border-line text-sm">
        <div className="flex justify-between py-2"><dt>Sous-total</dt><dd>{order.subtotalLabel}</dd></div>
        <div className="flex justify-between py-2"><dt>Livraison</dt><dd>{order.deliveryLabel}</dd></div>
        <div className="flex justify-between py-2"><dt>Réduction</dt><dd>{order.discountLabel}</dd></div>
        <div className="flex justify-between py-3 font-medium"><dt>Total</dt><dd>{order.totalLabel}</dd></div>
      </dl>
      <section className="mt-6 border border-line bg-cream p-5" aria-label="Suivi">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-display text-2xl">Suivi</h2>
          <span className="shrink-0 bg-terracotta px-2 py-1 text-xs font-medium uppercase tracking-[0.12em] text-cream">{order.statusLabel}</span>
        </div>
        <TrackSteps events={order.events} />
      </section>
      {order.canReview ? (
        <section className="mt-6 border border-line bg-cream p-5" aria-label="Avis">
          <Link className={btn} to={`/avis?commande=${encodeURIComponent(order.ref)}#laisser-un-avis`}>
            Laisser un avis
          </Link>
        </section>
      ) : order.reviewId ? (
        <p className="mt-6 text-sm text-ink-soft">
          <Link className="underline decoration-line underline-offset-4 hover:decoration-terracotta" to="/avis">Voir les avis</Link>
        </p>
      ) : null}
      <div className="mt-6 flex flex-wrap gap-3">
        <a className={btnLine} href={`/api/commande/${encodeURIComponent(order.ref)}/pdf`}>Télécharger le PDF</a>
        <Link className={btn} to="/carte">Commander autre chose</Link>
      </div>
    </article>
  );
}
