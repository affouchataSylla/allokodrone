import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, ApiError } from "../api";
import { useSession } from "../session";
import type { ProductPayload } from "../types";
import { Alert, btn, field, input, money, Pending, Quantity, useTitle } from "../ui";

export function Product() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const { setCartCount } = useSession();
  const [data, setData] = useState<ProductPayload | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [missing, setMissing] = useState(false);
  const [selected, setSelected] = useState<Record<number, number>>({});
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");
  const [pending, setPending] = useState(false);

  useTitle(data?.product.name ?? "Produit");

  useEffect(() => {
    let cancel = false;
    setData(null);
    setMissing(false);
    setErrors([]);
    setSelected({});
    setQuantity(1);
    api<ProductPayload>(`/api/produit/${slug}`)
      .then((payload) => {
        if (!cancel) setData(payload);
      })
      .catch((error: unknown) => {
        if (cancel) return;
        if (error instanceof ApiError && error.status === 404) setMissing(true);
        else setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, [slug]);

  const price = useMemo(() => {
    if (!data) return "";
    const product = data.product;
    if (!product.priceConfirmed || product.priceCents == null) return "Prix à valider";
    let total = product.priceCents;
    for (const group of data.groups) {
      const choiceId = selected[group.id];
      if (!choiceId) continue;
      const choice = group.choices.find((item) => item.id === choiceId);
      if (!choice || !choice.deltaConfirmed || choice.deltaCents == null) return "Prix à valider";
      total += choice.deltaCents;
    }
    return money(total * quantity);
  }, [data, selected, quantity]);

  if (missing) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="font-display text-4xl">Produit introuvable</h1>
        <Link className={`${btn} mt-6`} to="/carte">Retour à la carte</Link>
      </div>
    );
  }
  if (!data && !errors.length) return <div className="mx-auto max-w-6xl px-4"><Pending /></div>;
  if (!data) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-7">
        <Alert errors={errors} />
      </div>
    );
  }

  const product = data.product;
  const canCompose = product.available && product.orderable;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!data) return;
    const local: string[] = [];
    for (const group of data.groups) {
      if (group.required && !selected[group.id]) local.push(`Choix obligatoire : ${group.name}.`);
    }
    if (local.length) {
      setErrors(local);
      return;
    }
    setPending(true);
    setErrors([]);
    try {
      const result = await api<{ cartCount: number }>("/api/panier/ajouter", {
        method: "POST",
        body: {
          produit: product.id,
          quantite: quantity,
          choix: Object.values(selected),
          notes,
        },
      });
      setCartCount(result.cartCount);
      navigate("/panier");
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <Link
        className="inline-flex h-12 w-12 items-center justify-center rounded-xl border border-line text-xl hover:border-ink"
        to={`/carte?categorie=${product.categorySlug}`}
        aria-label="Retour"
      >
        ←
      </Link>
      <article className="motion-rise mt-5 grid gap-6 lg:grid-cols-2 lg:items-start">
        {(() => {
          const fallbacks: Record<string, string> = {
            burgers: "/images/burger.jpg",
            bowls: "/images/bowl.jpg",
            sides: "/images/wings.jpg",
            plats: "/images/bowl.jpg",
            boissons: "/images/alloko.jpg",
            desserts: "/images/alloko.jpg",
            midi: "/images/bowl.jpg",
          };
          const image = product.image || fallbacks[product.categorySlug] || null;
          const crop = product.slug === "bowl" || product.categorySlug === "bowls" || product.categorySlug === "plats" || product.categorySlug === "midi"
            ? "object-[center_22%]"
            : "object-center";
          return image ? (
            <img
              className={`aspect-[4/3] w-full max-w-full rounded-2xl object-cover sm:aspect-square ${crop}`}
              src={image}
              alt={product.name}
              decoding="async"
            />
          ) : (
            <span className="flex aspect-[4/3] w-full items-center justify-center rounded-2xl bg-paper-2 font-display text-5xl text-terracotta/80 sm:aspect-square" aria-hidden="true">
              {product.name.trim().charAt(0)}
            </span>
          );
        })()}
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-terracotta">{product.categoryName}</p>
          <h1 className="mt-3 font-display text-4xl leading-[0.95] sm:text-5xl">{product.name}</h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-ink-soft">{product.description}</p>
          <div className="mt-5">
            <Alert errors={errors} />
            {product.availability ? <p className="text-sm text-terracotta-deep">{product.availability}</p> : null}
          </div>
          <form className="mt-6" onSubmit={(event) => void submit(event)}>
            <p className="font-display text-4xl">{price}</p>
            {data.groups.map((group) => (
              <fieldset key={group.id} className="mt-5 border border-line p-4">
                <legend className="px-1 font-display text-2xl">
                  {group.name}
                  {group.required ? " *" : ""}
                </legend>
                <div className="mt-3 space-y-2">
                  {group.choices.map((choice) => (
                    <label key={choice.id} className="flex min-h-12 items-center gap-3 border border-line px-3 text-sm transition-colors duration-300 has-checked:border-ink has-checked:bg-paper-2">
                      <input
                        type="radio"
                        name={`groupe-${group.id}`}
                        value={choice.id}
                        disabled={!choice.available || !canCompose}
                        checked={selected[group.id] === choice.id}
                        onChange={() => setSelected((current) => ({ ...current, [group.id]: choice.id }))}
                      />
                      <span>
                        {choice.name} <span className="text-ink-soft">— {choice.extra}</span>
                        {!choice.available ? " · indisponible" : ""}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            {canCompose ? (
              <>
                <div className="mt-6">
                  <p className="mb-2 text-sm">Quantité</p>
                  <Quantity value={quantity} onChange={setQuantity} disabled={pending} />
                </div>
                {data.allowNotes ? (
                  <label className={field}>
                    <span>Instructions</span>
                    <textarea className={input} name="notes" maxLength={280} value={notes} onChange={(event) => setNotes(event.target.value)} />
                  </label>
                ) : null}
                <div className="mt-6">
                  <button className={btn} type="submit" disabled={pending}>
                    {pending ? "Ajout…" : "Ajouter au panier"}
                  </button>
                </div>
                {!product.priceConfirmed ? (
                  <p className="mt-3 text-sm text-ink-soft">Le restaurant confirme ce prix avant de pouvoir le commander.</p>
                ) : null}
              </>
            ) : null}
          </form>
        </div>
      </article>
    </div>
  );
}
