import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { api, ApiError } from "../api";
import { useSession } from "../session";
import type { HomePayload, Product } from "../types";
import { DishCard } from "../DishCard";
import { Alert, btn, btnLine, field, input, Pending, useTitle } from "../ui";

export { Concept } from "./Concept";

const steps = [
  ["01", "Choisir", "Parcourez la carte : burgers, bowls, sides, boissons et desserts."],
  ["02", "Personnaliser", "Le bowl se compose : base, viande, sauce, accompagnement. Riz Jollof : +1 €."],
  ["03", "Retirer", "La commande se récupère au comptoir."],
];

export function Signature() {
  useTitle("Signature");
  const [products, setProducts] = useState<Product[] | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    let cancel = false;
    api<HomePayload>("/api/accueil")
      .then((payload) => {
        if (!cancel) setProducts(payload.featured);
      })
      .catch((error: unknown) => {
        if (!cancel) setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  return (
    <article className="mx-auto max-w-6xl px-4 py-7">
      <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Notre signature</p>
      <h1 className="mt-3 font-display text-5xl leading-none">Des recettes qui font <span className="italic text-terracotta">voyager</span></h1>
      <Alert errors={errors} />
      {!products && !errors.length ? <Pending /> : null}
      <ul className="mt-7 grid grid-cols-1 gap-4 min-[460px]:grid-cols-2 lg:grid-cols-3">
        {(products ?? []).map((product) => (
          <li key={product.slug} className="min-w-0">
            <DishCard product={product} badge={false} />
          </li>
        ))}
      </ul>
    </article>
  );
}

type SiteReview = {
  id: number;
  author: string;
  initials: string;
  stars: number;
  body: string;
  dateLabel: string;
  verified: boolean;
  usefulCount: number;
  votedUseful: boolean;
  canEdit: boolean;
  photoUrl: string | null;
  foodStars: number | null;
  deliveryStars: number | null;
  serviceStars: number | null;
  reply: { body: string; dateLabel: string } | null;
};

type ReviewBoard = {
  google: { quote: string; author: string; place: string; source: string };
  reviews: SiteReview[];
  average: number | null;
  count: number;
  filteredCount: number;
  histogram: { stars: number; count: number }[];
  page: number;
  pages: number;
  sort: string;
  note: number | null;
};

type ReviewEligibility = {
  canReview: boolean;
  reason?: string;
  orderRef?: string | null;
  customerName?: string;
  mode?: string;
};

function StarMark({ filled, size = "h-5 w-5" }: { filled: boolean; size?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={`${size} transition-colors duration-200 ${filled ? "text-terracotta" : "text-line"}`} aria-hidden="true">
      <path fill="currentColor" d="M12 2.6 14.6 8.7l6.6.6-5 4.3 1.5 6.4L12 16.8 6.3 20l1.5-6.4-5-4.3 6.6-.6L12 2.6z" />
    </svg>
  );
}

function Stars({ value, label, size }: { value: number; label: string; size?: string }) {
  return (
    <span className="inline-flex gap-1.5" role="img" aria-label={label}>
      {[1, 2, 3, 4, 5].map((star) => <StarMark key={star} filled={star <= value} size={size} />)}
    </span>
  );
}

function StarPicker({ value, onChange, name, label }: { value: number; onChange: (n: number) => void; name: string; label: string }) {
  return (
    <fieldset>
      <legend className="text-sm">{label}</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {[1, 2, 3, 4, 5].map((star) => (
          <label key={star} className="inline-flex cursor-pointer p-0.5">
            <input className="sr-only" type="radio" name={name} value={star} checked={value === star} onChange={() => onChange(star)} />
            <span className="sr-only">{star} sur 5</span>
            <StarMark filled={star <= value} size="h-6 w-6" />
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function fmtNote(value: number | null | undefined) {
  if (value == null) return "—";
  return String(value).replace(".", ",");
}

export function Avis() {
  useTitle("Avis");
  const { session } = useSession();
  const restaurant = session?.restaurant;
  const review = restaurant?.review;
  const [params, setParams] = useSearchParams();
  const filterNote = params.get("note");
  const sort = params.get("tri") || "date";
  const page = Math.max(1, Number(params.get("page") || 1) || 1);
  const orderFromUrl = params.get("commande") || "";
  const [board, setBoard] = useState<ReviewBoard | null>(null);
  const [eligible, setEligible] = useState<ReviewEligibility | null>(null);
  const [commande, setCommande] = useState(orderFromUrl);
  const [note, setNote] = useState(0);
  const [foodNote, setFoodNote] = useState(0);
  const [deliveryNote, setDeliveryNote] = useState(0);
  const [serviceNote, setServiceNote] = useState(0);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [sent, setSent] = useState(false);
  const [openFaq, setOpenFaq] = useState(0);
  const [reportId, setReportId] = useState<number | null>(null);
  const [reportReason, setReportReason] = useState("");
  const [editId, setEditId] = useState<number | null>(null);
  const [editNote, setEditNote] = useState(0);
  const [editName, setEditName] = useState("");
  const [editMessage, setEditMessage] = useState("");
  const [moreOptions, setMoreOptions] = useState(false);

  const query = useMemo(() => {
    const search = new URLSearchParams();
    if (filterNote) search.set("note", filterNote);
    if (sort && sort !== "date") search.set("tri", sort);
    if (page > 1) search.set("page", String(page));
    const qs = search.toString();
    return qs ? `/api/avis?${qs}` : "/api/avis";
  }, [filterNote, sort, page]);

  useEffect(() => {
    let cancel = false;
    api<ReviewBoard>(query)
      .then((payload) => {
        if (!cancel) setBoard(payload);
      })
      .catch((error: unknown) => {
        if (!cancel) setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, [query]);

  useEffect(() => {
    if (orderFromUrl) setCommande(orderFromUrl);
  }, [orderFromUrl]);

  useEffect(() => {
    const ref = commande.trim().toUpperCase();
    if (!ref.startsWith("AK-") || ref.length < 6) {
      setEligible(null);
      return;
    }
    let cancel = false;
    const timer = window.setTimeout(() => {
      api<ReviewEligibility>(`/api/avis/eligibilite?ref=${encodeURIComponent(ref)}`)
        .then((payload) => {
          if (cancel) return;
          setEligible(payload);
          if (payload.customerName) {
            setName((current) => current || payload.customerName!.split(" ")[0] || payload.customerName!);
          }
        })
        .catch(() => {
          if (!cancel) setEligible({ canReview: false, reason: "Commande introuvable." });
        });
    }, 350);
    return () => {
      cancel = true;
      window.clearTimeout(timer);
    };
  }, [commande]);

  if (!restaurant || !review) return <div className="mx-auto max-w-3xl px-4"><Pending /></div>;

  const hours = restaurant.hoursLines ?? [restaurant.hoursLabel];
  const offer = restaurant.offer.trim();
  const offerLine = /[.!?]$/.test(offer) ? offer : `${offer}.`;
  const questions: { q: string; a: string[] }[] = [
    { q: "Où retire-t-on la commande ?", a: [`Au comptoir, ${restaurant.address}.`] },
    { q: "Quels sont les horaires ?", a: hours },
    { q: "La livraison est-elle ouverte ?", a: [restaurant.deliveryOpen ? "Oui." : "Non. Le retrait au comptoir reste possible."] },
    { q: "L'offre est-elle déduite automatiquement ?", a: ["Non.", offerLine] },
    { q: "Comment se compose le bowl ?", a: ["Base, viande, sauce et accompagnement. Le riz blanc est compris. Le riz Jollof est à +1 €."] },
    { q: "Comment règle-t-on ?", a: ["Le moyen de règlement se choisit à la commande, parmi ceux activés par le restaurant."] },
    { q: "Comment laisser un avis ?", a: ["Après une commande terminée, ouvrez la page de confirmation puis « Laisser un avis ». Un seul avis par commande."] },
    { q: "Où suivre une commande ?", a: ["Le suivi est sur la page de la commande, et dans le panier sous le récapitulatif."] },
  ];

  const reviews = board?.reviews ?? [];
  const average = board?.average;
  const count = board?.count ?? 0;
  const histMax = Math.max(1, ...(board?.histogram ?? []).map((item) => item.count));

  function setFilter(next: { note?: string | null; tri?: string; page?: number }) {
    const copy = new URLSearchParams(params);
    if (next.note === null) copy.delete("note");
    else if (next.note !== undefined) copy.set("note", next.note);
    if (next.tri !== undefined) {
      if (next.tri === "date") copy.delete("tri");
      else copy.set("tri", next.tri);
    }
    if (next.page !== undefined) {
      if (next.page <= 1) copy.delete("page");
      else copy.set("page", String(next.page));
    }
    setParams(copy, { replace: true });
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    const orderRef = commande.trim().toUpperCase();
    if (!orderRef) {
      setErrors(["Indiquez le numéro de commande."]);
      return;
    }
    setPending(true);
    setErrors([]);
    setSent(false);
    try {
      const payload = await api<ReviewBoard & { ok: boolean }>("/api/avis", {
        method: "POST",
        body: {
          orderRef,
          nom: name,
          note,
          message,
          notePlats: foodNote || undefined,
          noteLivraison: deliveryNote || undefined,
          noteService: serviceNote || undefined,
          photo: photo || undefined,
        },
      });
      setBoard(payload);
      setMessage("");
      setNote(0);
      setFoodNote(0);
      setDeliveryNote(0);
      setServiceNote(0);
      setPhoto(null);
      setSent(true);
      setEligible({ canReview: false, reason: "Un avis existe déjà pour cette commande." });
      const copy = new URLSearchParams(params);
      copy.delete("commande");
      setParams(copy, { replace: true });
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
    } finally {
      setPending(false);
    }
  }

  async function onPhoto(file: File | null) {
    if (!file) {
      setPhoto(null);
      return;
    }
    if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size > 2_000_000) {
      setErrors(["Photo JPEG, PNG ou WebP, 2 Mo maximum."]);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setPhoto(typeof reader.result === "string" ? reader.result : null);
    reader.readAsDataURL(file);
  }

  async function voteUseful(id: number) {
    try {
      const result = await api<{ usefulCount: number; votedUseful: boolean }>("/api/avis/" + id + "/utile", { method: "POST", body: {} });
      setBoard((current) =>
        current
          ? {
              ...current,
              reviews: current.reviews.map((item) =>
                item.id === id ? { ...item, usefulCount: result.usefulCount, votedUseful: result.votedUseful } : item,
              ),
            }
          : current,
      );
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
    }
  }

  async function sendReport(event: FormEvent) {
    event.preventDefault();
    if (reportId == null) return;
    try {
      await api("/api/avis/" + reportId + "/signaler", { method: "POST", body: { motif: reportReason } });
      setReportId(null);
      setReportReason("");
      setSent(true);
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
    }
  }

  async function removeOwn(id: number) {
    if (!window.confirm("Supprimer votre avis ?")) return;
    try {
      await api("/api/avis/" + id, { method: "DELETE", body: {} });
      const payload = await api<ReviewBoard>(query);
      setBoard(payload);
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
    }
  }

  function startEdit(item: SiteReview) {
    setEditId(item.id);
    setEditNote(item.stars);
    setEditName(item.author);
    setEditMessage(item.body);
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault();
    if (editId == null) return;
    try {
      await api("/api/avis/" + editId, {
        method: "PATCH",
        body: { nom: editName, note: editNote, message: editMessage },
      });
      setEditId(null);
      const payload = await api<ReviewBoard>(query);
      setBoard(payload);
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
    }
  }

  return (
    <article className="bg-paper-2">
    <div className="mx-auto max-w-6xl px-4 py-7 lg:py-10">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-terracotta">Avis</p>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
        <div className="max-w-2xl">
          <h1 className="font-display text-[clamp(2.1rem,8vw,3.75rem)] leading-[0.92] text-ink">
            Ils ont goûté, <span className="italic text-terracotta">ils témoignent</span>
          </h1>
        </div>
        {average != null && count > 0 ? (
          <div className="rounded-xl border border-line bg-cream px-5 py-4">
            <p className="font-display text-4xl leading-none text-ink">{fmtNote(average)}</p>
            <Stars value={Math.round(average)} label={`${fmtNote(average)} sur 5`} size="h-5 w-5" />
            <p className="mt-2 text-sm text-ink-soft">{count} avis</p>
          </div>
        ) : null}
      </div>

      <Alert errors={errors} />

      <div className="mt-7 grid items-start gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <figure className="rounded-xl border border-line bg-cream px-6 py-8 sm:px-8">
          <p className="text-xs uppercase tracking-[0.16em] text-terracotta">{review.source}</p>
          <blockquote className="mt-4 border-l-2 border-terracotta pl-5">
            <p className="font-display text-lg leading-relaxed text-ink sm:text-xl">« {review.quote} »</p>
          </blockquote>
          <figcaption className="mt-8 flex flex-wrap items-baseline justify-between gap-3 border-t border-line pt-5 text-sm">
            <span className="font-medium text-ink">{review.author}</span>
            <span className="text-ink-soft">{review.place}</span>
          </figcaption>
        </figure>

        <section className="rounded-xl border border-line bg-cream px-6 py-8 sm:px-8" aria-label="Répartition des notes">
          <h2 className="font-display text-3xl leading-none text-ink">Répartition</h2>
          <ul className="mt-6 space-y-3">
            {(board?.histogram ?? [5, 4, 3, 2, 1].map((stars) => ({ stars, count: 0 }))).map((item) => (
              <li key={item.stars}>
                <button
                  type="button"
                  className="group flex w-full items-center gap-3 text-left"
                  onClick={() => setFilter({ note: filterNote === String(item.stars) ? null : String(item.stars), page: 1 })}
                >
                  <span className="w-8 shrink-0 text-sm tabular-nums">{item.stars}★</span>
                  <span className="h-2 flex-1 overflow-hidden bg-paper-2">
                    <span
                      className="block h-full bg-terracotta transition-[width] duration-500 ease-out group-hover:bg-terracotta-deep"
                      style={{ width: `${Math.max(item.count ? 8 : 0, (item.count / histMax) * 100)}%` }}
                    />
                  </span>
                  <span className="w-8 shrink-0 text-right text-sm text-ink-soft tabular-nums">{item.count}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <section className="scroll-mt-24 rounded-xl border border-line bg-cream px-5 py-5 sm:px-6" id="laisser-un-avis">
          <h2 className="font-display text-2xl leading-none text-ink sm:text-3xl">Laisser un avis</h2>
          {eligible && !eligible.canReview ? (
            <p className="mt-2 text-sm text-ink-soft" role="status">{eligible.reason}</p>
          ) : null}
          <form className="mt-4 space-y-3" onSubmit={(event) => void send(event)}>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={field}>
                N° de commande
                <input
                  className={input}
                  name="commande"
                  value={commande}
                  placeholder="AK-…"
                  autoComplete="off"
                  maxLength={20}
                  onChange={(event) => setCommande(event.target.value.toUpperCase())}
                  required
                />
              </label>
              <label className={field}>
                Prénom
                <input className={input} name="nom" value={name} maxLength={40} autoComplete="given-name" onChange={(event) => setName(event.target.value)} required />
              </label>
            </div>
            <StarPicker value={note} onChange={setNote} name="note" label="Note" />
            <label className={field}>
              Votre avis
              <textarea className={`${input} min-h-20 py-2.5`} name="message" value={message} maxLength={800} onChange={(event) => setMessage(event.target.value)} required />
            </label>
            <button
              type="button"
              className="text-sm text-ink-soft underline decoration-line underline-offset-4 hover:text-ink hover:decoration-terracotta"
              onClick={() => setMoreOptions((open) => !open)}
            >
              {moreOptions ? "Moins d'options" : "Plus d'options"}
            </button>
            {moreOptions ? (
              <div className="space-y-3 border-t border-line pt-3">
                <label className={field}>
                  Photo
                  <input
                    className={input}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(event) => void onPhoto(event.target.files?.[0] ?? null)}
                  />
                </label>
                <div className="grid gap-3 sm:grid-cols-3">
                  <StarPicker value={foodNote} onChange={setFoodNote} name="notePlats" label="Plats" />
                  <StarPicker value={deliveryNote} onChange={setDeliveryNote} name="noteLivraison" label="Livraison" />
                  <StarPicker value={serviceNote} onChange={setServiceNote} name="noteService" label="Service" />
                </div>
              </div>
            ) : null}
            <button className={`${btn} w-full sm:w-auto`} type="submit" disabled={pending || (eligible != null && !eligible.canReview)}>
              {pending ? "Publication…" : "Publier"}
            </button>
            {sent ? <p className="text-sm text-ink-soft" role="status">Avis publié.</p> : null}
          </form>
        </section>

        <section className="rounded-xl border border-line bg-cream px-5 py-6 sm:px-6 sm:py-7" aria-label="Avis clients">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="font-display text-3xl leading-none text-ink">Sur le site</h2>
            <div className="flex flex-wrap gap-2">
              {[
                ["date", "Plus récents"],
                ["pertinence", "Pertinence"],
                ["note", "Meilleures notes"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={`min-h-9 rounded-xl border px-2.5 text-sm transition-colors duration-200 ${sort === value ? "border-ink bg-cream" : "border-line bg-cream/60 text-ink-soft hover:border-ink hover:text-ink"}`}
                  onClick={() => setFilter({ tri: value, page: 1 })}
                >
                  {label}
                </button>
              ))}
              {filterNote ? (
                <button type="button" className={`${btnLine} !min-h-9 bg-cream`} onClick={() => setFilter({ note: null, page: 1 })}>
                  Note {filterNote}★ · Effacer
                </button>
              ) : null}
            </div>
          </div>

          {!board ? <Pending /> : null}
          {board && !reviews.length ? (
            <p className="mt-6 text-sm text-ink-soft">Aucun avis pour ces filtres.</p>
          ) : null}

          <ul className="mt-6 grid gap-3">
            {reviews.map((item) => (
              <li key={item.id} className="min-w-0">
                <article className="flex h-full flex-col rounded-xl border border-line bg-paper px-4 py-4 transition-[border-color,transform] duration-300 hover:-translate-y-0.5 hover:border-terracotta/40">
                  <header className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="grid h-10 w-10 place-items-center rounded-xl bg-paper-2 font-display text-sm text-terracotta" aria-hidden="true">
                        {item.initials}
                      </span>
                      <div>
                        <p className="font-medium">{item.author}</p>
                        <p className="text-xs text-ink-soft">{item.dateLabel}</p>
                      </div>
                    </div>
                    <Stars value={item.stars} label={`${item.stars} sur 5`} />
                  </header>
                  {item.verified ? (
                    <p className="mt-3 inline-flex w-fit items-center border border-line px-2 py-1 text-[0.65rem] uppercase tracking-[0.14em] text-ink-soft">
                      Achat vérifié
                    </p>
                  ) : null}
                  <p className="mt-3 flex-1 text-sm leading-relaxed">« {item.body} »</p>
                  {item.photoUrl ? (
                    <img className="mt-3 max-h-40 w-full object-cover" src={item.photoUrl} alt="" loading="lazy" />
                  ) : null}
                  {(item.foodStars || item.deliveryStars || item.serviceStars) ? (
                    <dl className="mt-3 grid grid-cols-3 gap-2 text-xs text-ink-soft">
                      {item.foodStars ? <div><dt>Plats</dt><dd>{item.foodStars}/5</dd></div> : null}
                      {item.deliveryStars ? <div><dt>Livraison</dt><dd>{item.deliveryStars}/5</dd></div> : null}
                      {item.serviceStars ? <div><dt>Service</dt><dd>{item.serviceStars}/5</dd></div> : null}
                    </dl>
                  ) : null}
                  {item.reply ? (
                    <div className="mt-4 border-l-2 border-saffron bg-paper px-3 py-2.5">
                      <p className="text-xs uppercase tracking-[0.14em] text-terracotta">Réponse Allokodrone</p>
                      <p className="mt-1.5 text-sm leading-relaxed">{item.reply.body}</p>
                    </div>
                  ) : null}
                  <footer className="mt-4 flex flex-wrap gap-2 border-t border-line pt-3">
                    <button
                      type="button"
                      className={`min-h-9 rounded-xl border px-3 text-sm transition-colors duration-200 ${item.votedUseful ? "border-ink bg-cream" : "border-line hover:border-ink"}`}
                      onClick={() => void voteUseful(item.id)}
                    >
                      Utile · {item.usefulCount}
                    </button>
                    <button
                      type="button"
                      className="min-h-9 rounded-xl border border-line px-3 text-sm text-ink-soft transition-colors duration-200 hover:border-ink hover:text-ink"
                      onClick={() => setReportId(item.id)}
                    >
                      Signaler
                    </button>
                    {item.canEdit ? (
                      <>
                        <button
                          type="button"
                          className="min-h-9 rounded-xl border border-line px-3 text-sm transition-colors duration-200 hover:border-ink"
                          onClick={() => startEdit(item)}
                        >
                          Modifier
                        </button>
                        <button
                          type="button"
                          className="min-h-9 rounded-xl border border-line px-3 text-sm text-terracotta-deep transition-colors duration-200 hover:border-ink"
                          onClick={() => void removeOwn(item.id)}
                        >
                          Supprimer
                        </button>
                      </>
                    ) : null}
                  </footer>
                  {editId === item.id ? (
                    <form className="mt-3 border-t border-line pt-3" onSubmit={(event) => void saveEdit(event)}>
                      <StarPicker value={editNote} onChange={setEditNote} name={`edit-note-${item.id}`} label="Note" />
                      <label className={field}>
                        Prénom
                        <input className={input} value={editName} maxLength={40} onChange={(event) => setEditName(event.target.value)} />
                      </label>
                      <label className={field}>
                        Avis
                        <textarea className={`${input} min-h-20 py-3`} value={editMessage} maxLength={800} onChange={(event) => setEditMessage(event.target.value)} />
                      </label>
                      <div className="mt-3 flex gap-2">
                        <button className={btn} type="submit">Enregistrer</button>
                        <button className={btnLine} type="button" onClick={() => setEditId(null)}>Annuler</button>
                      </div>
                    </form>
                  ) : null}
                </article>
              </li>
            ))}
          </ul>

          {board && board.pages > 1 ? (
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <button type="button" className={btnLine} disabled={page <= 1} onClick={() => setFilter({ page: page - 1 })}>
                Précédent
              </button>
              <p className="text-sm text-ink-soft">
                Page {board.page} / {board.pages}
              </p>
              <button type="button" className={btnLine} disabled={page >= board.pages} onClick={() => setFilter({ page: page + 1 })}>
                Suivant
              </button>
            </div>
          ) : null}
        </section>
      </div>

      {reportId != null ? (
        <form className="fixed inset-x-4 bottom-4 z-40 mx-auto max-w-md border border-line bg-cream p-5 shadow-lg sm:inset-x-auto" onSubmit={(event) => void sendReport(event)}>
          <h3 className="font-display text-2xl">Signaler un avis</h3>
          <label className={field}>
            Motif
            <textarea className={`${input} min-h-20 py-3`} value={reportReason} maxLength={240} onChange={(event) => setReportReason(event.target.value)} required />
          </label>
          <div className="mt-4 flex gap-2">
            <button className={btn} type="submit">Envoyer</button>
            <button className={btnLine} type="button" onClick={() => setReportId(null)}>Annuler</button>
          </div>
        </form>
      ) : null}

      <section className="mt-8 scroll-mt-24 border-t border-line pt-7" aria-labelledby="faq-titre">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-terracotta">FAQ</p>
        <h2 id="faq-titre" className="mt-2 font-display text-3xl leading-none text-ink">Questions fréquentes</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {questions.map((item, index) => {
            const open = openFaq === index;
            const panelId = `faq-reponse-${index}`;
            return (
              <div key={item.q} className="rounded-xl border border-line bg-cream">
                <h3>
                  <button
                    type="button"
                    className={`flex w-full items-center justify-between gap-3 px-4 text-left font-display text-base leading-snug text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-terracotta ${open ? "pb-2 pt-3.5" : "py-3.5"}`}
                    aria-expanded={open}
                    aria-controls={panelId}
                    onClick={() => setOpenFaq(open ? -1 : index)}
                  >
                    <span className="min-w-0">{item.q}</span>
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-line text-sm leading-none text-terracotta" aria-hidden="true">{open ? "–" : "+"}</span>
                  </button>
                </h3>
                <div id={panelId} role="region" hidden={!open} className="px-4 pb-3.5">
                  {item.a.map((line) => (
                    <p key={line} className="text-sm leading-relaxed text-ink-soft [&+&]:mt-1.5">{line}</p>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
    </article>
  );
}

export function Guide() {
  useTitle("Commander");
  const { session } = useSession();
  const restaurant = session?.restaurant;

  return (
    <article className="mx-auto max-w-6xl px-4 py-7">
      <p className="text-xs uppercase tracking-[0.16em] text-terracotta">Commander</p>
      <h1 className="mt-3 font-display text-5xl leading-none">Trois étapes</h1>
      <div className="mt-7 grid gap-6 md:grid-cols-3">
        {steps.map(([number, title, text]) => (
          <section key={number}>
            <p className="font-display text-4xl text-terracotta">{number}</p>
            <h2 className="mt-3 font-display text-3xl">{title}</h2>
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">{text}</p>
          </section>
        ))}
      </div>
      {restaurant ? <p className="mt-7 text-sm text-ink-soft">{restaurant.offer}</p> : null}
      <Link className={`${btn} mt-6`} to="/carte">Voir la carte</Link>
    </article>
  );
}
