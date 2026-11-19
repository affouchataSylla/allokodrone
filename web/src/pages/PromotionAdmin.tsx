import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import { ApiError, api, apiUpload } from "../api";
import { apiUrl } from "../base";
import {
  loadPromoFonts,
  PromotionCard,
  type PopupPromotion,
} from "../components/PromotionPopup";
import { useSession } from "../session";

type PromotionStatus = "active" | "scheduled" | "expired" | "inactive";

type AdminPromotion = PopupPromotion & {
  date_debut: string;
  actif: boolean;
  priorite: number;
  pages_cibles: string[];
  statut: PromotionStatus;
  impressions: number;
  clicks: number;
  closes: number;
  click_rate: number;
  unique_clickers: number;
  orders_after_click: number;
};

type PromotionClicker = {
  visitor: string;
  clicked_at: string | null;
  event_day: string;
  has_order: boolean | null;
  order_count: number;
};

type PromotionDraft = {
  titre: string;
  prix: string;
  ancien_prix: string;
  badge_texte: string;
  afficher_pastille_reduction: boolean;
  description: string;
  image_url: string;
  cta_texte: string;
  cta_lien: string;
  mention_legale: string;
  date_debut: string;
  date_fin: string;
  actif: boolean;
  priorite: string;
  pages_cibles: string[];
  frequence: PopupPromotion["frequence"];
  delai_affichage: string;
  intention_de_sortie: boolean;
  couleur_fond: string;
  couleur_accent: string;
  theme: PopupPromotion["theme"];
};

const IMAGE_LIMIT = 2 * 1024 * 1024;
const TARGETS = [
  ["accueil", "Accueil"],
  ["menu", "Menu"],
  ["toutes", "Toutes les pages"],
] as const;

function localDateTime(date: Date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function clickDate(clicker: PromotionClicker) {
  if (!clicker.clicked_at) return `Date précise non enregistrée (${clicker.event_day})`;
  const date = new Date(clicker.clicked_at);
  return Number.isNaN(date.getTime())
    ? clicker.clicked_at
    : date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function createDraft(): PromotionDraft {
  const start = new Date(Date.now() + 5 * 60000);
  const end = new Date(start.getTime() + 14 * 86400000);
  return {
    titre: "",
    prix: "",
    ancien_prix: "",
    badge_texte: "",
    afficher_pastille_reduction: true,
    description: "",
    image_url: "",
    cta_texte: "COMMANDER MAINTENANT",
    cta_lien: "/carte",
    mention_legale: "",
    date_debut: localDateTime(start),
    date_fin: localDateTime(end),
    actif: false,
    priorite: "0",
    pages_cibles: ["accueil"],
    frequence: "session",
    delai_affichage: "6",
    intention_de_sortie: false,
    couleur_fond: "#F6EBD9",
    couleur_accent: "#FF6A13",
    theme: "beige",
  };
}

function toDraft(promo: AdminPromotion): PromotionDraft {
  const theme = promo.theme || "beige";
  return {
    titre: promo.titre,
    prix: String(promo.prix),
    ancien_prix: promo.ancien_prix === null ? "" : String(promo.ancien_prix),
    badge_texte: promo.badge_texte,
    afficher_pastille_reduction: promo.afficher_pastille_reduction,
    description: promo.description,
    image_url: promo.image_url,
    cta_texte: promo.cta_texte,
    cta_lien: promo.cta_lien,
    mention_legale: promo.mention_legale,
    date_debut: promo.date_debut.slice(0, 16),
    date_fin: promo.date_fin.slice(0, 16),
    actif: promo.actif,
    priorite: String(promo.priorite),
    pages_cibles: promo.pages_cibles,
    frequence: promo.frequence,
    delai_affichage: String(promo.delai_affichage),
    intention_de_sortie: promo.intention_de_sortie,
    couleur_fond:
      theme === "beige" && promo.couleur_fond.toUpperCase() === "#1E0F08"
        ? "#F6EBD9"
        : promo.couleur_fond,
    couleur_accent: promo.couleur_accent,
    theme,
  };
}

function errorText(error: unknown) {
  return error instanceof ApiError ? error.message : "Une erreur est survenue. Réessayez.";
}

function statusLabel(status: PromotionStatus) {
  return {
    active: "Active",
    scheduled: "Programmée",
    expired: "Expirée",
    inactive: "Désactivée",
  }[status];
}

async function compressImage(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file);
  try {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Compression d’image indisponible.");

    let scale = Math.min(1, 2400 / Math.max(bitmap.width, bitmap.height));
    while (scale >= 0.2) {
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      for (const mime of ["image/webp", "image/jpeg"]) {
        for (const quality of [0.86, 0.76, 0.66, 0.56]) {
          const blob = await new Promise<Blob | null>((resolve) =>
            canvas.toBlob(resolve, mime, quality),
          );
          if (blob && blob.type === mime && blob.size <= IMAGE_LIMIT) return blob;
        }
      }
      scale *= 0.78;
    }
    throw new Error("L’image compressée dépasse encore 2 Mo.");
  } finally {
    bitmap.close();
  }
}

function previewPromotion(draft: PromotionDraft, id: number): PopupPromotion {
  return {
    id,
    titre: draft.titre || "Titre de la promotion",
    prix: draft.prix || "9.90",
    ancien_prix: draft.ancien_prix || null,
    badge_texte: draft.badge_texte,
    afficher_pastille_reduction: draft.afficher_pastille_reduction,
    description: draft.description,
    image_url: draft.image_url,
    cta_texte: draft.cta_texte,
    cta_lien: draft.cta_lien,
    mention_legale: draft.mention_legale,
    date_fin: draft.date_fin,
    frequence: draft.frequence,
    delai_affichage: Number(draft.delai_affichage || 6),
    intention_de_sortie: draft.intention_de_sortie,
    couleur_fond: draft.couleur_fond,
    couleur_accent: draft.couleur_accent,
    theme: draft.theme,
    updated_at: "",
  };
}

export function PromotionAdmin() {
  const { session, error: sessionError, refresh } = useSession();
  const [promotions, setPromotions] = useState<AdminPromotion[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<PromotionDraft>(createDraft);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [expandedClickersId, setExpandedClickersId] = useState<number | null>(null);
  const [clickersByPromotion, setClickersByPromotion] = useState<Record<number, PromotionClicker[]>>({});
  const [loadingClickersId, setLoadingClickersId] = useState<number | null>(null);

  const isAdmin = session?.user?.role === "admin";
  const selected = promotions.find((promo) => promo.id === selectedId) ?? null;
  const preview = useMemo(() => previewPromotion(draft, selectedId ?? 0), [draft, selectedId]);

  const loadPromotions = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api<{ promotions: AdminPromotion[] }>("/api/admin/promotions");
      setPromotions(result.promotions);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPromoFonts();
  }, []);

  useEffect(() => {
    if (isAdmin) void loadPromotions();
  }, [isAdmin, loadPromotions]);

  function update<K extends keyof PromotionDraft>(key: K, value: PromotionDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function updateTheme(theme: PopupPromotion["theme"]) {
    setDraft((current) => ({
      ...current,
      theme,
      couleur_fond: theme === "premium" ? "#1E0F08" : "#F6EBD9",
    }));
  }

  function startNew() {
    setSelectedId(null);
    setDraft(createDraft());
    setError("");
    setNotice("");
  }

  function edit(promo: AdminPromotion) {
    setSelectedId(promo.id);
    setDraft(toDraft(promo));
    setError("");
    setNotice("");
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api<{ promotion: AdminPromotion }>(
        selectedId === null
          ? "/api/admin/promotions"
          : `/api/admin/promotions/${selectedId}`,
        {
          method: "POST",
          body: {
            ...draft,
            ancien_prix: draft.ancien_prix || null,
            priorite: Number(draft.priorite),
            delai_affichage: Number(draft.delai_affichage),
          },
        },
      );
      await loadPromotions();
      edit(result.promotion);
      setNotice("Promotion enregistrée.");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  async function toggle(promo: AdminPromotion) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/promotions/${promo.id}/toggle`, {
        method: "POST",
        body: { actif: !promo.actif },
      });
      await loadPromotions();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  async function duplicate(promo: AdminPromotion) {
    setBusy(true);
    setError("");
    try {
      const result = await api<{ promotion: AdminPromotion }>(
        `/api/admin/promotions/${promo.id}/duplicate`,
        { method: "POST", body: {} },
      );
      await loadPromotions();
      edit(result.promotion);
      setNotice("Copie créée. Vérifiez ses dates avant de l’activer.");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  async function remove(promo: AdminPromotion) {
    if (!window.confirm(`Supprimer la promotion « ${promo.titre} » ?`)) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/promotions/${promo.id}/delete`, {
        method: "POST",
        body: {},
      });
      if (selectedId === promo.id) startNew();
      await loadPromotions();
      setNotice("Promotion supprimée.");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  async function toggleClickers(promoId: number) {
    if (expandedClickersId === promoId) {
      setExpandedClickersId(null);
      return;
    }
    setExpandedClickersId(promoId);
    if (clickersByPromotion[promoId]) return;

    setLoadingClickersId(promoId);
    setError("");
    try {
      const result = await api<{ clickers: PromotionClicker[] }>(
        `/api/admin/promotions/${promoId}/clickers`,
      );
      setClickersByPromotion((current) => ({ ...current, [promoId]: result.clickers }));
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoadingClickersId(null);
    }
  }

  async function uploadImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Choisissez une image JPG, PNG ou WebP.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const compressed = await compressImage(file);
      const formData = new FormData();
      formData.append("image", compressed, `promotion.${compressed.type === "image/webp" ? "webp" : "jpg"}`);
      const result = await apiUpload<{ url: string }>("/api/admin/promotions/upload", formData);
      update("image_url", result.url);
      setNotice("Image compressée et téléversée.");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  function updateTarget(target: string, checked: boolean) {
    if (target === "toutes") {
      update("pages_cibles", checked ? ["toutes"] : ["accueil"]);
      return;
    }
    const targets = draft.pages_cibles.filter((item) => item !== "toutes");
    const next = checked ? [...targets, target] : targets.filter((item) => item !== target);
    update("pages_cibles", next.length ? next : ["accueil"]);
  }

  if (!session) {
    return (
      <div className="promo-admin">
        <div className="promo-admin__shell promo-admin__panel">
          <h1>Promotions</h1>
          {sessionError ? (
            <>
              <p role="alert">{sessionError}</p>
              <button className="promo-admin__button" type="button" onClick={() => void refresh()}>
                Réessayer
              </button>
            </>
          ) : (
            <p>Vérification de votre accès…</p>
          )}
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="promo-admin">
        <div className="promo-admin__shell promo-admin__panel">
          <h1>Accès réservé à l’administration</h1>
          <a className="promo-admin__button" href="/admin/connexion">
            Se connecter
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="promo-admin">
      <div className="promo-admin__shell">
        <header className="promo-admin__header">
          <div>
            <h1 className="text-2xl font-bold">Pop-ups promotionnels</h1>
            <p className="mt-1 text-sm">Créez et programmez les offres affichées sur le site.</p>
          </div>
          <div className="promo-admin__actions">
            <button className="promo-admin__button promo-admin__button--primary" type="button" onClick={startNew}>
              Nouvelle promotion
            </button>
          </div>
        </header>

        <nav className="promo-admin__tabs" aria-label="Gestion des promotions">
          <a className="promo-admin__tab" href="/admin/codes-promo">Codes promo</a>
          <a className="promo-admin__tab promo-admin__tab--active" href="/admin/promotions" aria-current="page">
            Pop-ups promotionnels
          </a>
        </nav>

        {error ? <p className="promo-admin__error" role="alert">{error}</p> : null}
        {notice ? <p className="mb-3 text-sm font-semibold" role="status">{notice}</p> : null}

        <div className="promo-admin__grid">
          <section className="promo-admin__panel" aria-labelledby="promo-list-title">
            <h2 id="promo-list-title" className="mb-3 text-lg font-bold">Promotions</h2>
            {loading ? <p>Chargement…</p> : null}
            {!loading && promotions.length === 0 ? <p>Aucune promotion pour le moment.</p> : null}
            <ul className="promo-admin__list">
              {promotions.map((promo) => (
                <li className="promo-admin__promo" key={promo.id}>
                  <button
                    className="block w-full text-left"
                    type="button"
                    onClick={() => edit(promo)}
                    aria-current={selectedId === promo.id ? "true" : undefined}
                  >
                    <span className="block font-semibold">{promo.titre}</span>
                    <span className="text-xs">
                      {statusLabel(promo.statut)} · {promo.prix} € ·{" "}
                      {promo.theme === "premium" ? "Premium Afro-Food" : "Beige"}
                    </span>
                  </button>
                  <div className="mt-2 text-xs">
                    Affichages {promo.impressions} · Clics {promo.clicks} · Fermetures {promo.closes}
                    <span className="ml-1 font-semibold">· CTR {promo.click_rate}%</span>
                  </div>
                  <div className="mt-1 text-xs">
                    Visiteurs ayant cliqué {promo.unique_clickers} · Commandes après clic {promo.orders_after_click}
                  </div>
                  <button
                    className="promo-admin__button mt-2"
                    type="button"
                    disabled={loadingClickersId === promo.id}
                    onClick={() => void toggleClickers(promo.id)}
                    aria-expanded={expandedClickersId === promo.id}
                  >
                    {expandedClickersId === promo.id ? "Masquer les clics" : "Voir les clics"}
                  </button>
                  {expandedClickersId === promo.id ? (
                    <div className="mt-2 border-t pt-2 text-xs">
                      <p className="mb-2">
                        Visiteurs anonymisés. Une commande est associée si elle a été créée après le clic dans la même session.
                      </p>
                      {loadingClickersId === promo.id ? <p>Chargement des clics…</p> : null}
                      {!loadingClickersId && clickersByPromotion[promo.id]?.length === 0 ? (
                        <p>Aucun clic enregistré.</p>
                      ) : null}
                      <ul className="space-y-1">
                        {clickersByPromotion[promo.id]?.map((clicker) => (
                          <li key={clicker.visitor}>
                            <span className="font-semibold">{clicker.visitor}</span>
                            {" · "}{clickDate(clicker)}
                            {" · "}
                            {clicker.has_order === null
                              ? "Historique antérieur, commande non attribuable"
                              : clicker.has_order
                                ? `Commande passée (${clicker.order_count})`
                                : "Aucune commande après le clic"}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <div className="promo-admin__actions mt-2">
                    <button className="promo-admin__button" type="button" disabled={busy} onClick={() => void toggle(promo)}>
                      {promo.actif ? "Désactiver" : "Activer"}
                    </button>
                    <button className="promo-admin__button" type="button" disabled={busy} onClick={() => void duplicate(promo)}>
                      Dupliquer
                    </button>
                    <button className="promo-admin__button" type="button" disabled={busy} onClick={() => void remove(promo)}>
                      Supprimer
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="promo-admin__panel" aria-labelledby="promo-editor-title">
            <h2 id="promo-editor-title" className="mb-3 text-lg font-bold">
              {selected ? `Modifier : ${selected.titre}` : "Créer une promotion"}
            </h2>
            <form className="promo-admin__form" onSubmit={(event) => void save(event)}>
              <label className="promo-admin__field">
                Design du pop-up
                <select value={draft.theme} onChange={(event) => updateTheme(event.target.value === "premium" ? "premium" : "beige")}>
                  <option value="beige">Beige — photo à droite</option>
                  <option value="premium">Premium Afro-Food — fond brun</option>
                </select>
              </label>
              <label className="promo-admin__field">
                Titre du plat ou menu
                <input required maxLength={120} value={draft.titre} onChange={(event) => update("titre", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Prix promotionnel (€)
                <input required type="number" min="0.01" max="9999.99" step="0.01" value={draft.prix} onChange={(event) => update("prix", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Ancien prix (€)
                <input type="number" min="0.01" max="9999.99" step="0.01" value={draft.ancien_prix} onChange={(event) => update("ancien_prix", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Badge
                <input maxLength={80} value={draft.badge_texte} onChange={(event) => update("badge_texte", event.target.value)} />
              </label>
              <label className="promo-admin__field promo-admin__field--wide">
                Description (masquée sur mobile)
                <textarea maxLength={280} value={draft.description} onChange={(event) => update("description", event.target.value)} />
              </label>
              <label className="promo-admin__field promo-admin__field--wide">
                Photo du plat (JPG, PNG ou WebP, compressée à 2 Mo max)
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void uploadImage(event)} />
              </label>
              {draft.image_url ? (
                <div className="promo-admin__field promo-admin__field--wide">
                  <span>Repères de cadrage 4:5 (desktop) et 16:10 (mobile)</span>
                  <div className="promo-admin__preview-crops">
                    <div className="promo-admin__crop promo-admin__crop--desktop"><img src={draft.image_url.startsWith("/api/") ? apiUrl(draft.image_url) : draft.image_url} alt="Recadrage desktop" /></div>
                    <div className="promo-admin__crop promo-admin__crop--mobile"><img src={draft.image_url.startsWith("/api/") ? apiUrl(draft.image_url) : draft.image_url} alt="Recadrage mobile" /></div>
                  </div>
                </div>
              ) : null}
              <label className="promo-admin__field">
                Texte du bouton
                <input required maxLength={60} value={draft.cta_texte} onChange={(event) => update("cta_texte", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Lien du bouton
                <input required maxLength={2048} value={draft.cta_lien} onChange={(event) => update("cta_lien", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Début
                <input required type="datetime-local" value={draft.date_debut} onChange={(event) => update("date_debut", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Fin
                <input required type="datetime-local" value={draft.date_fin} onChange={(event) => update("date_fin", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Pages cibles
                <span className="flex flex-wrap gap-3">
                  {TARGETS.map(([value, label]) => (
                    <label className="inline-flex items-center gap-1" key={value}>
                      <input
                        type="checkbox"
                        checked={draft.pages_cibles.includes(value)}
                        onChange={(event) => updateTarget(value, event.target.checked)}
                      />
                      {label}
                    </label>
                  ))}
                </span>
              </label>
              <label className="promo-admin__field">
                Fréquence d’affichage
                <select value={draft.frequence} onChange={(event) => update("frequence", event.target.value as PromotionDraft["frequence"])}>
                  <option value="session">Une fois par session</option>
                  <option value="day">Une fois par jour</option>
                  <option value="visit">À chaque visite</option>
                </select>
              </label>
              <label className="promo-admin__field">
                Délai (secondes)
                <input type="number" min="0" max="120" value={draft.delai_affichage} onChange={(event) => update("delai_affichage", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Priorité
                <input type="number" min="-10000" max="10000" value={draft.priorite} onChange={(event) => update("priorite", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                Couleur de fond
                <input type="color" value={draft.couleur_fond} onChange={(event) => update("couleur_fond", event.target.value.toUpperCase())} />
              </label>
              <label className="promo-admin__field">
                Couleur d’accent
                <input type="color" value={draft.couleur_accent} onChange={(event) => update("couleur_accent", event.target.value.toUpperCase())} />
              </label>
              <label className="promo-admin__field promo-admin__field--wide">
                Mention légale
                <textarea maxLength={500} value={draft.mention_legale} onChange={(event) => update("mention_legale", event.target.value)} />
              </label>
              <label className="promo-admin__field">
                <span className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={draft.afficher_pastille_reduction} onChange={(event) => update("afficher_pastille_reduction", event.target.checked)} />
                  Afficher la pastille de réduction
                </span>
              </label>
              <label className="promo-admin__field">
                <span className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={draft.intention_de_sortie} onChange={(event) => update("intention_de_sortie", event.target.checked)} />
                  Déclencher à l’intention de sortie (ordinateur)
                </span>
              </label>
              <label className="promo-admin__field promo-admin__field--wide">
                <span className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={draft.actif} onChange={(event) => update("actif", event.target.checked)} />
                  Promotion activée (dans ses dates de validité)
                </span>
              </label>
              <div className="promo-admin__actions promo-admin__field--wide">
                <button className="promo-admin__button promo-admin__button--primary" type="submit" disabled={busy}>
                  {busy ? "Enregistrement…" : "Enregistrer"}
                </button>
                <button className="promo-admin__button" type="button" onClick={startNew}>
                  Annuler
                </button>
              </div>
            </form>

            <section className="mt-5" aria-labelledby="preview-title">
              <h3 id="preview-title" className="mb-2 font-bold">Aperçu en direct</h3>
              <div className="promo-preview-grid">
                <div className="promo-preview-desktop">
                  <p className="mb-2 text-xs">Ordinateur</p>
                  <PromotionCard promotion={preview} titleId="preview-desktop-title" onClose={() => undefined} preview />
                </div>
                <div className="promo-preview-mobile">
                  <p className="mb-2 text-xs">Mobile</p>
                  <PromotionCard promotion={preview} titleId="preview-mobile-title" onClose={() => undefined} mobilePreview preview />
                </div>
              </div>
            </section>
          </section>
        </div>
      </div>
    </div>
  );
}
