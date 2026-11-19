import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { useNavigate } from "react-router";
import { apiUrl, asset } from "../base";
import { api } from "../api";

export type PopupPromotion = {
  id: number;
  titre: string;
  prix: number | string;
  ancien_prix: number | string | null;
  badge_texte: string;
  afficher_pastille_reduction: boolean;
  description: string;
  image_url: string;
  cta_texte: string;
  cta_lien: string;
  mention_legale: string;
  date_fin: string;
  frequence: "session" | "day" | "visit";
  delai_affichage: number;
  intention_de_sortie: boolean;
  couleur_fond: string;
  couleur_accent: string;
  theme: "beige" | "premium";
  updated_at: string;
};

type PromotionCardProps = {
  promotion: PopupPromotion;
  titleId?: string;
  onClose: () => void;
  onCta?: (event: ReactMouseEvent<HTMLAnchorElement>) => void;
  mobilePreview?: boolean;
  preview?: boolean;
};

function euro(value: number | string | null) {
  if (value === null || value === "") return "";
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(parsed)
    : "";
}

function discountPercent(promotion: PopupPromotion) {
  const price = Number(promotion.prix);
  const oldPrice = Number(promotion.ancien_prix);
  if (!Number.isFinite(price) || !Number.isFinite(oldPrice) || oldPrice <= price) return null;
  return Math.floor(((oldPrice - price) / oldPrice) * 100);
}

function urgency(date: string) {
  const until = new Date(date).getTime();
  if (!Number.isFinite(until)) return { date: date, days: null };
  return {
    date: new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(until),
    days: Math.max(0, Math.ceil((until - Date.now()) / 86400000)),
  };
}

function popupBackground(color: string, theme: PopupPromotion["theme"]) {
  const value = color || (theme === "premium" ? "#1E0F08" : "#F6EBD9");
  return theme === "beige" && value.toUpperCase() === "#1E0F08" ? "#F6EBD9" : value;
}

export function PromotionCard({
  promotion,
  titleId,
  onClose,
  onCta,
  mobilePreview = false,
  preview = false,
}: PromotionCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const reduction = discountPercent(promotion);
  const deadline = urgency(promotion.date_fin);
  const style = {
    "--promo-bg": popupBackground(promotion.couleur_fond, promotion.theme),
    "--promo-accent": promotion.couleur_accent || "#FF6A13",
  } as CSSProperties;
  const imageSrc =
    promotion.image_url.startsWith("/api/") ? apiUrl(promotion.image_url) : promotion.image_url;

  useEffect(() => setImageFailed(false), [promotion.image_url]);

  return (
    <article
      className={`promo-card${mobilePreview ? " promo-card--mobile-preview" : ""}${promotion.theme === "premium" ? " promo-card--premium" : ""}`}
      style={style}
      aria-label={preview ? "Aperçu de la promotion" : undefined}
    >
      <div className={`promo-card__photo${!imageSrc || imageFailed ? " promo-card__photo--placeholder" : ""}`}>
        {imageSrc && !imageFailed ? (
          <img
            src={imageSrc}
            alt={promotion.titre}
            onError={() => setImageFailed(true)}
          />
        ) : (
          <span>[PHOTO DU PLAT]</span>
        )}
      </div>
      {promotion.afficher_pastille_reduction && reduction !== null ? (
        <span className="promo-card__discount">-{reduction} %</span>
      ) : null}
      <button className="promo-card__close" type="button" aria-label="Fermer" onClick={onClose}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m6 6 12 12M18 6 6 18" />
        </svg>
      </button>
      <div className="promo-card__content">
        <img className="promo-card__logo" src={asset("images/logo-dark.png")} alt="ALLOKODRONE" />
        {promotion.badge_texte ? <p className="promo-card__badge">{promotion.badge_texte}</p> : null}
        <h2 id={titleId || `promo-title-${promotion.id}`} className="promo-card__title">
          {promotion.titre}
        </h2>
        <div className="promo-card__price-row">
          <span className="promo-card__price-prefix">À</span>
          <span className="promo-card__price">{euro(promotion.prix)}</span>
          {promotion.ancien_prix ? (
            <span className="promo-card__old-price">{euro(promotion.ancien_prix)}</span>
          ) : null}
        </div>
        {promotion.description ? <p className="promo-card__description">{promotion.description}</p> : null}
        <a
          className="promo-card__cta"
          href={preview ? "#preview" : promotion.cta_lien}
          onClick={(event) => {
            if (preview) event.preventDefault();
            else onCta?.(event);
          }}
        >
          {promotion.cta_texte || "COMMANDER MAINTENANT"}
        </a>
        <p className="promo-card__urgency">
          Jusqu&apos;au {deadline.date}
          <span className="promo-card__days">
            {deadline.days === null ? "" : ` · Plus que ${deadline.days} jour${deadline.days > 1 ? "s" : ""}`}
          </span>
        </p>
        {promotion.mention_legale ? <p className="promo-card__legal">{promotion.mention_legale}</p> : null}
        <button className="promo-card__dismiss" type="button" onClick={onClose}>
          {promotion.theme === "premium" ? "Non merci" : "Plus tard"}
        </button>
      </div>
    </article>
  );
}

function frequencyKey(promotion: PopupPromotion) {
  return `alloko-promo-${promotion.id}-${promotion.updated_at}`;
}

function alreadySeen(promotion: PopupPromotion) {
  if (promotion.frequence === "visit") return false;
  try {
    const key = frequencyKey(promotion);
    if (promotion.frequence === "session") return window.sessionStorage.getItem(key) === "1";
    return window.localStorage.getItem(key) === new Date().toLocaleDateString("sv-SE");
  } catch {
    return false;
  }
}

function markSeen(promotion: PopupPromotion) {
  try {
    const key = frequencyKey(promotion);
    if (promotion.frequence === "session") window.sessionStorage.setItem(key, "1");
    if (promotion.frequence === "day") {
      window.localStorage.setItem(key, new Date().toLocaleDateString("sv-SE"));
    }
  } catch {
    return;
  }
}

export function loadPromoFonts() {
  if (document.querySelector('link[data-promo-fonts="true"]')) return;
  const preconnect = document.createElement("link");
  preconnect.rel = "preconnect";
  preconnect.href = "https://fonts.googleapis.com";
  preconnect.dataset.promoFonts = "true";
  document.head.append(preconnect);
  const fonts = document.createElement("link");
  fonts.rel = "stylesheet";
  fonts.href = "https://fonts.googleapis.com/css2?family=Anton&family=DM+Sans:wght@400;500;700&display=swap";
  fonts.dataset.promoFonts = "true";
  document.head.append(fonts);
}

function recordEvent(promotion: PopupPromotion, event: "impression" | "click" | "close") {
  void api<{ ok: boolean }>("/api/promotions/event", {
    method: "POST",
    body: { id: promotion.id, event },
  }).catch((error: unknown) => {
    console.error("Impossible d'enregistrer l'événement promotionnel.", error);
  });
}

export function PromotionPopup({ pathname }: { pathname: string }) {
  const navigate = useNavigate();
  const [promotion, setPromotion] = useState<PopupPromotion | null>(null);
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closedRef = useRef(false);

  const close = useCallback(() => {
    if (!closedRef.current && promotion) {
      closedRef.current = true;
      recordEvent(promotion, "close");
    }
    setOpen(false);
  }, [promotion]);

  useEffect(() => {
    setPromotion(null);
    setOpen(false);
    closedRef.current = false;
    if (/^\/(panier|commander|commande|paiement)(\/|$)/.test(pathname)) return;

    const page = pathname === "/" ? "accueil" : pathname === "/carte" ? "menu" : "autre";
    let cancelled = false;
    let timer: number | undefined;
    let exitHandler: ((event: globalThis.MouseEvent) => void) | undefined;

    void api<{ promotion: PopupPromotion | null }>(`/api/promotions/active?page=${page}`)
      .then(({ promotion: next }) => {
        if (cancelled || !next || alreadySeen(next)) return;
        setPromotion(next);
        const show = () => {
          if (cancelled) return;
          markSeen(next);
          setOpen(true);
          loadPromoFonts();
          recordEvent(next, "impression");
        };
        if (next.intention_de_sortie && window.innerWidth >= 768) {
          exitHandler = (event) => {
            if (event.clientY <= 0 && event.relatedTarget === null) {
              document.removeEventListener("mouseout", exitHandler!);
              show();
            }
          };
          document.addEventListener("mouseout", exitHandler);
        } else {
          timer = window.setTimeout(show, Math.max(0, next.delai_affichage) * 1000);
        }
      })
      .catch((error: unknown) => {
        console.error("Impossible de charger la promotion.", error);
      });

    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
      if (exitHandler) document.removeEventListener("mouseout", exitHandler);
    };
  }, [pathname]);

  useEffect(() => {
    if (!open || !promotion) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusables = () =>
      Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      );
    dialogRef.current?.querySelector<HTMLElement>(".promo-card__close")?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusables();
      if (!items.length) {
        event.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      if (previous?.isConnected) previous.focus();
    };
  }, [open, promotion, close]);

  if (!promotion || !open) return null;
  const activePromotion = promotion;
  const titleId = `promo-title-${activePromotion.id}`;

  async function followCta(event: ReactMouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    try {
      await api("/api/promotions/event", {
        method: "POST",
        body: { id: activePromotion.id, event: "click" },
      });
    } catch (error: unknown) {
      console.error("Impossible d'enregistrer le clic promotionnel.", error);
    } finally {
      if (activePromotion.cta_lien.startsWith("/") && !activePromotion.cta_lien.startsWith("//")) {
        navigate(activePromotion.cta_lien);
      } else {
        window.location.assign(activePromotion.cta_lien);
      }
    }
  }

  return (
    <div
      className="promo-overlay"
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <div
        ref={dialogRef}
        className={`promo-dialog${activePromotion.theme === "premium" ? " promo-dialog--premium" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <PromotionCard promotion={activePromotion} titleId={titleId} onClose={close} onCta={followCta} />
      </div>
    </div>
  );
}
