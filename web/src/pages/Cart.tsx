import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api, ApiError } from "../api";
import { useCollect } from "../collect";
import { useSession } from "../session";
import type { Cart as CartData } from "../types";
import { TrackCards } from "../Tracking";
import { Alert, btn, Empty, input, Pending, Quantity, useTitle } from "../ui";

export function Cart() {
  useTitle("Panier");
  const { setCartCount } = useSession();
  const collect = useCollect();
  const [cart, setCart] = useState<CartData | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(0);

  async function load() {
    const data = await api<CartData>("/api/panier");
    setCart(data);
    setCode(data.promo);
    setCartCount(data.cartCount);
  }

  useEffect(() => {
    let cancel = false;
    api<CartData>("/api/panier")
      .then((data) => {
        if (cancel) return;
        setCart(data);
        setCode(data.promo);
        setCartCount(data.cartCount);
      })
      .catch((error: unknown) => {
        if (!cancel) setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, [setCartCount]);

  async function run(task: () => Promise<void>) {
    setErrors([]);
    try {
      await task();
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
      await load().catch(() => undefined);
    }
  }

  if (!cart && !errors.length) return <div className="mx-auto max-w-6xl px-4"><Pending label="Chargement du panier" /></div>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 lg:py-8">
    <div className={cart && cart.lines.length > 0 ? "lg:grid lg:grid-cols-[1fr_20rem] lg:gap-8" : ""}>
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Panier</p>
        <h1 className="mt-3 font-display text-5xl leading-none">Votre commande</h1>
        <div className="mt-6">
          <Alert errors={errors} />
          {cart?.promoError ? <Alert errors={[cart.promoError]} /> : null}
        </div>
        {!cart || cart.lines.length === 0 ? (
          <Empty title="Le panier est vide" text="Les plats ajoutés depuis la carte apparaîtront ici, avec leurs options." to="/carte" label="Voir la carte" />
        ) : (
          <ul className="mt-4 border-t border-line">
            {cart.lines.map((line) => (
              <li key={line.id} className="grid gap-4 border-b border-line py-5 sm:grid-cols-[5rem_1fr]">
                {line.image ? <img className="h-20 w-20 object-cover" src={line.image} alt="" /> : <span />}
                <div>
                  <div className="flex items-baseline justify-between gap-4">
                    <h2 className="font-display text-2xl">
                      <Link className="hover:text-terracotta" to={`/produit/${line.slug}`}>{line.name}</Link>
                    </h2>
                    <span className="tabular-nums">{line.lineLabel}</span>
                  </div>
                  {line.summary ? <p className="mt-1 text-sm text-ink-soft">{line.summary}</p> : null}
                  {line.notes ? <p className="mt-1 text-sm text-ink-soft">{line.notes}</p> : null}
                  <Alert errors={line.issues} />
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <Quantity
                      value={line.quantity}
                      disabled={busy === line.id}
                      onChange={(quantity) => {
                        setBusy(line.id);
                        void run(async () => {
                          const next = await api<CartData>("/api/panier/modifier", {
                            method: "POST",
                            body: { article: line.id, quantite: quantity },
                          });
                          setCart(next);
                          setCartCount(next.cartCount);
                        }).finally(() => setBusy(0));
                      }}
                    />
                    <button
                      className="min-h-12 text-sm underline decoration-line underline-offset-4"
                      type="button"
                      onClick={() => {
                        setBusy(line.id);
                        void run(async () => {
                          const next = await api<CartData>("/api/panier/supprimer", {
                            method: "POST",
                            body: { article: line.id },
                          });
                          setCart(next);
                          setCartCount(next.cartCount);
                        }).finally(() => setBusy(0));
                      }}
                    >
                      Retirer
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      {cart && cart.lines.length > 0 ? (
        <aside className="mt-6 h-fit lg:mt-12">
            <div className="border border-line bg-cream p-5">
              {cart.priced ? (
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between"><dt>Sous-total</dt><dd>{cart.subtotalLabel}</dd></div>
                  <div className="flex justify-between"><dt>Réduction</dt><dd>{cart.discountLabel}</dd></div>
                  <div className="flex justify-between border-t border-line pt-2 font-medium"><dt>Avant livraison</dt><dd>{cart.beforeDeliveryLabel}</dd></div>
                  {collect.mode === "delivery" && collect.feeLabel ? (
                    <div className="flex justify-between"><dt>Livraison</dt><dd>{collect.feeLabel}</dd></div>
                  ) : null}
                </dl>
              ) : (
                <p className="text-sm text-terracotta-deep">Total indisponible : des prix ou des options restent à valider.</p>
              )}
              <form
                className="mt-5 flex gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  void run(async () => {
                    const next = await api<CartData>("/api/panier/code", { method: "POST", body: { code } });
                    setCart(next);
                  });
                }}
              >
                <label className="min-w-0 flex-1 text-sm">
                  Code promotionnel
                  <input className={`${input} mt-1`} value={code} autoComplete="off" onChange={(event) => setCode(event.target.value)} />
                </label>
                <button className="mt-6 inline-flex min-h-12 items-center rounded-xl border border-line px-3 text-sm" type="submit">Appliquer</button>
              </form>
              <Link className={`${btn} mt-5 w-full`} to="/commander">Continuer</Link>
            </div>
        </aside>
      ) : null}
    </div>
    {cart ? <TrackCards orders={cart.suivi ?? []} /> : null}
    </div>
  );
}
