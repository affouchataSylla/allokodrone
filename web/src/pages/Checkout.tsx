import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { api, ApiError } from "../api";
import { resolveSlot, setCollect, slotDetail, useCollect } from "../collect";
import type { CheckoutPayload, PickupSlot } from "../types";
import { Alert, btn, field, input, Pending, useTitle } from "../ui";

type Draft = {
  nom: string;
  email: string;
  telephone: string;
  mode: "" | "pickup" | "delivery";
  pointId: string;
  slotId: string;
  zoneId: string;
  rue: string;
  codePostal: string;
  ville: string;
  paiement: string;
  conditions: boolean;
};

function Star() {
  return (
    <>
      <span className="text-terracotta" aria-hidden="true"> *</span>
      <span className="sr-only"> obligatoire</span>
    </>
  );
}

function FieldMessage({ message, onNight = false }: { message?: string; onNight?: boolean }) {
  if (!message) return null;
  return <p className={onNight ? "text-sm text-saffron" : "text-sm text-terracotta-deep"} role="alert">{message}</p>;
}

function CardPicture() {
  return (
    <svg className="h-16 w-24 shrink-0" viewBox="0 0 96 64" role="img" aria-label="Carte bancaire">
      <rect width="96" height="64" rx="6" fill="#2b2422" />
      <rect x="10" y="14" width="16" height="12" rx="2" fill="#f8b658" />
      <path d="M10 18h16M14 14v12M18 14v12" stroke="#2b2422" strokeWidth="0.6" />
      <circle cx="70" cy="40" r="8" fill="#d26e36" />
      <circle cx="80" cy="40" r="8" fill="#f8b658" />
      <text x="10" y="52" fill="#faf0dc" fontSize="7" letterSpacing="1.4">CARTE</text>
    </svg>
  );
}

function CardBrands() {
  return (
    <span className="mt-2 flex items-center gap-1.5" aria-hidden="true">
      <svg className="h-5 w-8" viewBox="0 0 32 20">
        <rect width="32" height="20" rx="2" fill="#1a1f71" />
        <text x="16" y="14" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="700">VISA</text>
      </svg>
      <svg className="h-5 w-8" viewBox="0 0 32 20">
        <rect width="32" height="20" rx="2" fill="#fff" stroke="#e4cda8" />
        <circle cx="13" cy="10" r="6" fill="#eb001b" />
        <circle cx="19" cy="10" r="6" fill="#f79e1b" />
      </svg>
      <svg className="h-5 w-8" viewBox="0 0 32 20">
        <rect width="32" height="20" rx="2" fill="#0b6b4f" />
        <text x="16" y="14" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="700">CB</text>
      </svg>
    </span>
  );
}

const empty: Draft = {
  nom: "",
  email: "",
  telephone: "",
  mode: "",
  pointId: "",
  slotId: "",
  zoneId: "",
  rue: "",
  codePostal: "",
  ville: "",
  paiement: "",
  conditions: false,
};

export function Checkout() {
  useTitle("Valider");
  const navigate = useNavigate();
  const collect = useCollect();
  const collectRef = useRef(collect);
  collectRef.current = collect;
  const [data, setData] = useState<CheckoutPayload | null>(null);
  const [draft, setDraft] = useState<Draft>(() => ({ ...empty, mode: collect.mode }));
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof Draft, string>>>({});
  const [pending, setPending] = useState(false);
  const [quote, setQuote] = useState<{ feeLabel: string; meters: number } | null>(null);
  const [quoteError, setQuoteError] = useState("");
  const [quoting, setQuoting] = useState(false);

  useEffect(() => {
    if (!errors.length) return;
    const invalid = document.querySelector<HTMLElement>("[aria-invalid='true']");
    if (invalid) {
      invalid.scrollIntoView({ block: "center" });
      invalid.focus({ preventScroll: true });
      return;
    }
    document.getElementById("erreurs-commande")?.scrollIntoView({ block: "center" });
  }, [errors]);

  useEffect(() => {
    let cancel = false;
    api<CheckoutPayload>("/api/commander")
      .then((payload) => {
        if (cancel) return;
        setData(payload);
        setDraft((current) => ({
          ...current,
          nom: payload.customer.nom,
          email: payload.customer.email,
          telephone: payload.customer.telephone,
          pointId: payload.points.length === 1 ? String(payload.points[0].id) : current.pointId,
        }));
      })
      .catch((error: unknown) => {
        if (!cancel) setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (!data) return;
    setDraft((current) => ({
      ...current,
      mode: collect.mode,
      slotId: String(resolveSlot(data.slots, collect)?.id ?? ""),
      rue: collect.rue || current.rue,
      codePostal: collect.codePostal || current.codePostal,
      ville: collect.ville || current.ville,
      paiement: collect.mode === "pickup"
        ? (data.payments.some((method) => method.code === "stripe") ? "stripe" : "")
        : (current.paiement === "pay_at_pickup" || current.paiement === "stripe" ? "" : current.paiement),
    }));
  }, [collect, data]);

  useEffect(() => {
    if (!data || draft.mode !== "delivery" || data.deliveryMode === "distance") return;
    const code = draft.codePostal.replace(/\s/g, "");
    const match = code.length >= 5
      ? data.zones.find((zone) => zone.name.replace(/\s/g, "").includes(code))
      : undefined;
    const chosen = match ?? (data.zones.length === 1 ? data.zones[0] : undefined);
    if (chosen && draft.zoneId !== String(chosen.id)) set("zoneId", String(chosen.id));
  }, [data, draft.mode, draft.codePostal, draft.zoneId]);

  useEffect(() => {
    if (!data || draft.mode !== "delivery" || data.deliveryMode !== "distance") {
      setQuote(null);
      setQuoteError("");
      setQuoting(false);
      return;
    }
    if (draft.rue.trim().length < 4 || draft.codePostal.trim().length < 4 || draft.ville.trim().length < 2) {
      setQuote(null);
      setQuoteError("");
      return;
    }
    let cancel = false;
    const timer = window.setTimeout(() => {
      setQuoting(true);
      api<{ feeLabel: string; meters: number }>("/api/livraison/estimer", {
        method: "POST",
        body: { rue: draft.rue, codePostal: draft.codePostal, ville: draft.ville },
      })
        .then((result) => {
          if (cancel) return;
          setQuote(result);
          setQuoteError("");
          setCollect({
            ...collectRef.current,
            mode: "delivery",
            rue: draft.rue.trim(),
            codePostal: draft.codePostal.trim(),
            ville: draft.ville.trim(),
            feeLabel: result.feeLabel,
          });
        })
        .catch((error: unknown) => {
          if (cancel) return;
          setQuote(null);
          setQuoteError(error instanceof ApiError ? error.message : "Le tarif n'a pas pu être calculé.");
        })
        .finally(() => {
          if (!cancel) setQuoting(false);
        });
    }, 500);
    return () => {
      cancel = true;
      window.clearTimeout(timer);
    };
  }, [data, draft.mode, draft.rue, draft.codePostal, draft.ville]);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  function validate(payload: CheckoutPayload, form: Draft) {
    const fields: Partial<Record<keyof Draft, string>> = {};
    const next: string[] = [];
    const add = (key: keyof Draft, message: string) => {
      fields[key] = message;
      next.push(message);
    };
    if (form.nom.trim().length < 2) add("nom", form.nom.trim() ? "Le nom est trop court." : "Indiquez votre nom.");
    if (!form.email.trim()) add("email", "Indiquez votre adresse e-mail.");
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) add("email", "Indiquez une adresse e-mail valide.");
    const digits = form.telephone.replace(/\D/g, "");
    if (!form.telephone.trim()) add("telephone", "Indiquez votre numéro de téléphone.");
    else if (digits.length < 8 || digits.length > 15) add("telephone", "Le numéro de téléphone est incomplet.");
    if (form.mode !== "pickup" && form.mode !== "delivery") add("mode", "Choisissez le retrait ou la livraison.");
    if (form.mode === "pickup") {
      if (payload.points.length > 1 && !form.pointId) add("pointId", "Choisissez un point de retrait.");
      if (!payload.slots.length) next.push("Aucun créneau de retrait n'est ouvert.");
      else if (!form.slotId) add("slotId", "Choisissez un créneau.");
    }
    if (form.mode === "delivery") {
      const byDistance = (payload.deliveryMode || "zones") === "distance";
      if (!byDistance && !payload.zones.length) next.push("Aucune zone de livraison n'est configurée.");
      else if (!byDistance && !form.zoneId) add("zoneId", "Choisissez une zone de livraison.");
      if (!form.rue.trim()) add("rue", "Indiquez la rue.");
      else if (form.rue.trim().length < 4) add("rue", "La rue est trop courte.");
      if (!form.codePostal.trim()) add("codePostal", "Indiquez le code postal.");
      else if (form.codePostal.trim().length < 4) add("codePostal", "Le code postal est incomplet.");
      if (form.ville.trim().length < 2) add("ville", "Indiquez la ville.");
    }
    const offered = form.mode === "pickup"
      ? payload.payments.filter((method) => method.code === "stripe")
      : payload.payments.filter((method) => method.code !== "pay_at_pickup");
    if (form.mode === "pickup" && !offered.length) {
      next.push(payload.stripeMessage || "Le Click & Collect se règle par carte. Le paiement en ligne n'est pas encore branché.");
    } else if (!offered.length) {
      next.push("Aucun moyen de règlement n'est activé.");
    } else if (!form.paiement || !offered.some((method) => method.code === form.paiement)) {
      add("paiement", form.mode === "pickup" ? "Le Click & Collect se règle par carte." : "Choisissez un moyen de règlement.");
    }
    if (payload.terms && !form.conditions) add("conditions", "Acceptez les conditions publiées par le restaurant.");
    if (!payload.cart.priced) next.push("Le total ne peut pas être calculé tant que des prix restent à valider.");
    return { fields, next };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!data || pending) return;
    const local = validate(data, draft);
    if (local.next.length) {
      setFieldErrors(local.fields);
      setErrors(local.next);
      return;
    }
    setFieldErrors({});
    setPending(true);
    setErrors([]);
    try {
      const result = await api<{ ref: string; checkoutUrl?: string }>("/api/commander", {
        method: "POST",
        body: {
          idempotencyKey: data.idempotencyKey,
          nom: draft.nom,
          email: draft.email,
          telephone: draft.telephone,
          mode: draft.mode,
          pointId: draft.pointId,
          slotId: draft.slotId,
          zoneId: draft.zoneId,
          rue: draft.rue,
          codePostal: draft.codePostal,
          ville: draft.ville,
          paiement: draft.paiement,
          conditions: draft.conditions,
        },
      });
      if (result.checkoutUrl) {
        window.location.assign(result.checkoutUrl);
        return;
      }
      navigate(`/commande/${result.ref}`);
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
      setPending(false);
    }
  }

  if (!data && !errors.length) return <div className="mx-auto max-w-6xl px-4"><Pending /></div>;
  if (data && data.cart.lines.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="font-display text-5xl">Votre panier est vide</h1>
        <Link className={`${btn} mt-6`} to="/carte">Voir la carte</Link>
      </div>
    );
  }

  return (
    <form className="mx-auto max-w-6xl px-4 py-6 lg:py-8" noValidate onSubmit={(event) => void submit(event)}>
      <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Commande</p>
      <h1 className="mt-3 font-display text-[clamp(1.85rem,7vw,3.25rem)] leading-none">Retrait ou livraison</h1>
      {data ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <fieldset>
              <legend className="mb-3 text-sm">Mode<Star /></legend>
              <div className="grid gap-2.5 sm:grid-cols-2 sm:gap-4">
                <label className={`flex min-h-[4.5rem] cursor-pointer flex-col justify-between rounded-xl border px-3.5 py-3 sm:min-h-28 sm:p-5 ${draft.mode === "pickup" ? "border-ink bg-cream" : "border-line bg-cream"}`}>
                  <span className="flex items-center justify-between gap-3">
                    <span className="font-display text-xl leading-none sm:text-3xl">Click &amp; Collect</span>
                    <input type="radio" name="mode" checked={draft.mode === "pickup"} onChange={() => { set("mode", "pickup"); setCollect({ ...collect, mode: "pickup" }); }} />
                  </span>
                  <span className="mt-1.5 text-xs text-ink-soft sm:mt-3 sm:text-sm">Je retire au restaurant</span>
                </label>
                <label className={`flex min-h-[4.5rem] cursor-pointer flex-col justify-between rounded-xl px-3.5 py-3 text-cream sm:min-h-28 sm:p-5 ${draft.mode === "delivery" ? "bg-night ring-2 ring-saffron" : "bg-night"}`}>
                  <span className="flex items-center justify-between gap-3">
                    <span className="font-display text-xl leading-none sm:text-3xl">Livraison</span>
                    <input type="radio" name="mode" checked={draft.mode === "delivery"} onChange={() => { set("mode", "delivery"); setCollect({ ...collect, mode: "delivery" }); }} />
                  </span>
                  <span className="mt-1.5 text-xs text-cream/75 sm:mt-3 sm:text-sm">Je me fais livrer</span>
                </label>
              </div>
              <div className="mt-2"><FieldMessage message={fieldErrors.mode} /></div>
            </fieldset>
            {draft.mode === "pickup" ? (
            <section className="rounded-xl border border-line bg-cream p-4 sm:p-5">
              <h2 className="font-display text-2xl sm:text-3xl">Click &amp; Collect</h2>
              {data.points.length > 1 ? (
                <div className="mt-3 space-y-2">
                  <p className="text-sm">Point de retrait<Star /></p>
                  {data.points.map((point) => (
                    <label key={point.id} className="flex min-h-12 items-center gap-3 border border-line px-3 text-sm has-checked:border-ink">
                      <input type="radio" name="point" checked={draft.pointId === String(point.id)} onChange={() => set("pointId", String(point.id))} />
                      {point.name} — {point.address}
                    </label>
                  ))}
                  <FieldMessage message={fieldErrors.pointId} />
                </div>
              ) : data.points[0] ? (
                <p className="mt-3 text-sm">{data.points[0].name}<br />{data.points[0].address}</p>
              ) : (
                <p className="mt-3 text-sm text-terracotta-deep">Aucun point de retrait n'est actif.</p>
              )}
              <PickupWhen slots={data.slots} slotId={draft.slotId} message={fieldErrors.slotId} />
            </section>
            ) : null}
            {draft.mode === "delivery" ? (
            <section className="bg-night p-5 text-cream">
              <h2 className="font-display text-3xl">Livraison</h2>
              <fieldset className="mt-4">
                <legend className="font-display text-xl">Zone{data.deliveryMode === "distance" || !data.zones.length ? null : <Star />}</legend>
                {data.deliveryMode === "distance" ? (
                  <p className="mt-2 text-sm text-cream/80">Les frais se calculent à partir de l'adresse.</p>
                ) : data.zones.length ? (
                  <div className="mt-2 space-y-2">
                    {data.zones.map((zone) => (
                      <label key={zone.id} className="flex min-h-12 items-center gap-3 border border-cream/30 px-3 text-sm has-checked:border-saffron">
                        <input type="radio" name="zone" checked={draft.zoneId === String(zone.id)} onChange={() => set("zoneId", String(zone.id))} />
                        {zone.name} — {zone.feeLabel}
                      </label>
                    ))}
                    <FieldMessage message={fieldErrors.zoneId} onNight />
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-saffron">Aucune zone de livraison n'est ouverte.</p>
                )}
              </fieldset>
              <label className="mt-4 flex flex-col gap-1.5 text-sm">
                <span>Rue<Star /></span>
                <input className="min-h-12 border border-cream/30 bg-transparent px-3 text-cream" name="rue" required aria-required="true" aria-invalid={Boolean(fieldErrors.rue)} autoComplete="street-address" value={draft.rue} onChange={(event) => set("rue", event.target.value)} />
                <FieldMessage message={fieldErrors.rue} onNight />
              </label>
              <label className="mt-4 flex flex-col gap-1.5 text-sm">
                <span>Code postal<Star /></span>
                <input className="min-h-12 border border-cream/30 bg-transparent px-3 text-cream" name="code_postal" required aria-required="true" aria-invalid={Boolean(fieldErrors.codePostal)} autoComplete="postal-code" value={draft.codePostal} onChange={(event) => set("codePostal", event.target.value)} />
                <FieldMessage message={fieldErrors.codePostal} onNight />
              </label>
              <label className="mt-4 flex flex-col gap-1.5 text-sm">
                <span>Ville<Star /></span>
                <input className="min-h-12 border border-cream/30 bg-transparent px-3 text-cream" name="ville" required aria-required="true" aria-invalid={Boolean(fieldErrors.ville)} autoComplete="address-level2" value={draft.ville} onChange={(event) => set("ville", event.target.value)} />
                <FieldMessage message={fieldErrors.ville} onNight />
              </label>
              {data.deliveryMode === "distance" ? (
                <p className="mt-4 text-sm" role="status">
                  {quoting ? "Calcul du tarif…" : quote ? `Frais de livraison : ${quote.feeLabel} · ${(quote.meters / 1000).toFixed(1).replace(".", ",")} km` : quoteError || "Le tarif s'affiche dès que l'adresse est complète."}
                </p>
              ) : null}
              <div className="mt-4 text-cream">
                <PickupWhen slots={data.slots} slotId={draft.slotId} message={fieldErrors.slotId} />
              </div>
            </section>
            ) : null}
            <label className={field}>
              <span>Nom<Star /></span>
              <input className={input} required aria-required="true" aria-invalid={Boolean(fieldErrors.nom)} autoComplete="name" value={draft.nom} onChange={(event) => set("nom", event.target.value)} />
              <FieldMessage message={fieldErrors.nom} />
            </label>
            <label className={field}>
              <span>E-mail<Star /></span>
              <input className={input} type="email" required aria-required="true" aria-invalid={Boolean(fieldErrors.email)} autoComplete="email" value={draft.email} onChange={(event) => set("email", event.target.value)} />
              <FieldMessage message={fieldErrors.email} />
            </label>
            <label className={field}>
              <span>Téléphone<Star /></span>
              <input className={input} type="tel" required aria-required="true" aria-invalid={Boolean(fieldErrors.telephone)} autoComplete="tel" value={draft.telephone} onChange={(event) => set("telephone", event.target.value)} />
              <FieldMessage message={fieldErrors.telephone} />
            </label>
            <fieldset className="mt-6">
              <legend className="font-display text-2xl">Règlement</legend>
              {draft.mode === "pickup" ? (
                data.payments.some((method) => method.code === "stripe") ? (
                  <div className="mt-3 flex items-center gap-4 border border-ink bg-cream px-4 py-4">
                    <CardPicture />
                    <span>
                      <span className="block text-sm font-medium">Carte bancaire</span>
                      <CardBrands />
                    </span>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-terracotta-deep">{data.stripeMessage || "Le Click & Collect se règle par carte. Le paiement en ligne n'est pas encore branché."}</p>
                )
              ) : data.payments.some((method) => method.code !== "pay_at_pickup") ? (
                <div className="mt-3 space-y-2">
                  {data.payments.filter((method) => method.code !== "pay_at_pickup").map((method) => (
                    <label key={method.code} className="flex min-h-16 items-center gap-3 border border-line px-3 text-sm has-checked:border-ink">
                      <input type="radio" name="paiement" checked={draft.paiement === method.code} onChange={() => set("paiement", method.code)} />
                      {method.code === "stripe" ? <CardPicture /> : null}
                      <span>
                        {method.code === "stripe" ? "Carte bancaire" : method.label}
                        {method.code === "stripe" ? <CardBrands /> : null}
                      </span>
                    </label>
                  ))}
                  <FieldMessage message={fieldErrors.paiement} />
                </div>
              ) : (
                <p className="mt-3 text-sm text-terracotta-deep">Aucun moyen de règlement n'est activé.</p>
              )}
              {draft.mode === "pickup" ? <div className="mt-2"><FieldMessage message={fieldErrors.paiement} /></div> : null}
            </fieldset>
            {data.terms ? (
              <div className="mt-4">
                <label className="flex min-h-12 items-start gap-3 text-sm">
                  <input type="checkbox" required aria-required="true" aria-invalid={Boolean(fieldErrors.conditions)} checked={draft.conditions} onChange={(event) => set("conditions", event.target.checked)} />
                  <span>{data.terms}<Star /></span>
                </label>
                <FieldMessage message={fieldErrors.conditions} />
              </div>
            ) : (
              <p className="mt-4 text-sm text-ink-soft">Les conditions générales de vente ne sont pas encore publiées.</p>
            )}
            {draft.paiement === "stripe" ? (
              <p className="border-l-2 border-saffron bg-paper-2 px-4 py-3 text-sm">Le paiement se fait sur la page sécurisée de Stripe.</p>
            ) : null}
            <div id="erreurs-commande" className="empty:hidden"><Alert errors={errors} /></div>
            <button className={btn} type="submit" disabled={pending || !data.cart.priced || (draft.mode === "pickup" ? !data.payments.some((method) => method.code === "stripe") : !data.payments.some((method) => method.code !== "pay_at_pickup"))}>
              {pending ? "Paiement en cours…" : draft.mode === "pickup" || draft.paiement === "stripe" ? "Payer" : "Valider la commande"}
            </button>
          </div>
          <aside className="h-fit border border-line p-5">
            <h2 className="font-display text-2xl">Récapitulatif</h2>
            <ul className="mt-4 divide-y divide-line">
              {data.cart.lines.map((line) => (
                <li key={line.id} className="py-3 text-sm">
                  <span className="font-medium">{line.quantity} × {line.name}</span>
                  {line.summary ? <span className="mt-1 block text-ink-soft">{line.summary}</span> : null}
                  <span className="mt-1 block tabular-nums">{line.lineLabel}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm">
              {data.cart.priced ? `Avant livraison : ${data.cart.beforeDeliveryLabel}` : "Total indisponible tant que les prix ne sont pas confirmés."}
            </p>
            {draft.mode === "delivery" && quote ? <p className="mt-2 text-sm">Livraison calculée : {quote.feeLabel}</p> : null}
          </aside>
        </div>
      ) : (
        <div className="mt-6"><Alert errors={errors} /></div>
      )}
    </form>
  );
}

function PickupWhen({ slots, slotId, message }: { slots: PickupSlot[]; slotId: string; message?: string }) {
  const slot = slots.find((item) => String(item.id) === slotId);
  const soon = Boolean(slot) && String(slots[0]?.id) === slotId;
  return (
    <div className="mt-4">
      <p className="font-display text-xl">Créneau</p>
      {slot ? (
        <p className="mt-2 text-sm">{soon ? "Au plus tôt" : "Pour plus tard"} · {slotDetail(slot)}</p>
      ) : (
        <p className="mt-2 text-sm text-terracotta-deep">Aucun créneau n'est ouvert.</p>
      )}
      <div className="mt-2"><FieldMessage message={message} /></div>
    </div>
  );
}
