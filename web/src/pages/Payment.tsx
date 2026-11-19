import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { api, ApiError } from "../api";
import { useSession } from "../session";
import type { OrderPayload } from "../types";
import { btn, Pending, useTitle } from "../ui";

function useOrder(ref: string) {
  const [order, setOrder] = useState<OrderPayload | null>(null);
  useEffect(() => {
    if (!ref) return;
    let cancel = false;
    api<OrderPayload>(`/api/commande/${encodeURIComponent(ref)}`)
      .then((payload) => {
        if (!cancel) setOrder(payload);
      })
      .catch(() => {
        if (!cancel) setOrder(null);
      });
    return () => {
      cancel = true;
    };
  }, [ref]);
  return order;
}

function Summary({ order }: { order: OrderPayload | null }) {
  if (!order) return null;
  return (
    <aside className="mt-6 border border-line p-5">
      <h2 className="font-display text-2xl">Récapitulatif {order.ref}</h2>
      <ul className="mt-4 border-t border-line">
        {order.lines.map((line) => (
          <li key={`${line.name}-${line.options}`} className="border-b border-line py-3 text-sm">
            <strong>{line.name}</strong> × {line.quantity} — {line.lineLabel}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm">Total {order.totalLabel}</p>
      <p className="mt-2 text-sm text-ink-soft">{order.paymentLabel}</p>
      <Link className="mt-4 inline-block text-sm underline" to={`/commande/${order.ref}`}>Voir la commande</Link>
    </aside>
  );
}

export function PaymentSuccess() {
  useTitle("Paiement");
  const [params] = useSearchParams();
  const ref = params.get("ref") || "";
  const sessionId = params.get("session_id") || "";
  const { session } = useSession();
  const order = useOrder(ref);
  const [state, setState] = useState<"loading" | "paid" | "pending" | "refused">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!ref || !session?.csrf) return;
    let cancel = false;
    setState("loading");
    api<OrderPayload>("/api/paiement/verifier", { method: "POST", body: { ref, sessionId } })
      .then((payload) => {
        if (cancel) return;
        if (payload.paymentStatus === "paid" && payload.confirmedByProvider) setState("paid");
        else if (payload.paymentStatus === "failed" || payload.paymentStatus === "cancelled") setState("refused");
        else setState("pending");
      })
      .catch((reason: unknown) => {
        if (cancel) return;
        setState("refused");
        setMessage(reason instanceof ApiError ? reason.message : "La confirmation du paiement a échoué.");
      });
    return () => {
      cancel = true;
    };
  }, [ref, sessionId, session?.csrf]);

  return (
    <article className="mx-auto max-w-3xl px-4 py-8">
      {state === "loading" ? <Pending /> : null}
      {state === "paid" ? (
        <>
          <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Paiement confirmé</p>
          <h1 className="mt-3 font-display text-5xl leading-none">Commande encaissée</h1>
          <p className="mt-4 text-sm">Stripe a confirmé le montant. La commande {ref} est enregistrée comme payée.</p>
        </>
      ) : null}
      {state === "pending" ? (
        <>
          <p className="text-xs uppercase tracking-[0.16em] text-terracotta">En attente</p>
          <h1 className="mt-3 font-display text-5xl leading-none">Paiement non confirmé</h1>
          <p className="mt-4 text-sm">Le retour sur cette page ne prouve pas l'encaissement. La commande reste en attente tant que Stripe n'a pas validé le montant.</p>
        </>
      ) : null}
      {state === "refused" ? (
        <>
          <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Paiement non encaissé</p>
          <h1 className="mt-3 font-display text-5xl leading-none">Le paiement n'est pas confirmé</h1>
          <p className="mt-4 text-sm" role="alert">{message || "Stripe n'a pas validé ce paiement."}</p>
          <Link className={`${btn} mt-6`} to={`/paiement/echec?ref=${encodeURIComponent(ref)}`}>Réessayer</Link>
        </>
      ) : null}
      <Summary order={order} />
    </article>
  );
}

export function PaymentFailure() {
  useTitle("Paiement interrompu");
  const [params] = useSearchParams();
  const ref = params.get("ref") || "";
  const order = useOrder(ref);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ref) return;
    api("/api/paiement/annuler", { method: "POST", body: { ref } }).catch(() => undefined);
  }, [ref]);

  function retry() {
    setPending(true);
    setError("");
    api<{ checkoutUrl: string }>("/api/paiement/reessayer", { method: "POST", body: { ref } })
      .then((result) => window.location.assign(result.checkoutUrl))
      .catch((reason: unknown) => {
        setPending(false);
        setError(reason instanceof ApiError ? reason.message : "Connexion interrompue. Réessayez.");
      });
  }

  return (
    <article className="mx-auto max-w-3xl px-4 py-8">
      <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Paiement interrompu</p>
      <h1 className="mt-3 font-display text-5xl leading-none">Le paiement n'a pas abouti</h1>
      <p className="mt-4 text-sm">Aucun encaissement n'a été confirmé. Vous pouvez relancer le paiement de la même commande.</p>
      {error ? <p className="mt-4 text-sm" role="alert">{error}</p> : null}
      <button className={`${btn} mt-6`} type="button" disabled={pending || !ref} onClick={retry}>
        {pending ? "Paiement en cours…" : "Réessayer le paiement"}
      </button>
      <Summary order={order} />
    </article>
  );
}
