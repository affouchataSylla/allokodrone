import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router";
import { api, ApiError } from "./api";
import { setCollect, resolveSlot, slotDetail, useCollect, type Collect } from "./collect";
import { useSession } from "./session";
import { SlotCalendar } from "./SlotCalendar";
import { btn } from "./ui";

function ordering(path: string) {
  return path === "/carte" || path === "/panier" || path === "/commander" || path.startsWith("/produit/");
}

function Chevron() {
  return (
    <svg className="h-3 w-3 shrink-0" viewBox="0 0 12 12" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M2 4.5 6 8l4-3.5" />
    </svg>
  );
}

function Bag() {
  return (
    <svg className="h-5 w-5 shrink-0 text-terracotta" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M6 8h12l-1 12H7L6 8z" />
      <path d="M9 8V6.5A3 3 0 0 1 12 3.5 3 3 0 0 1 15 6.5V8" />
    </svg>
  );
}

function Pin() {
  return (
    <svg className="h-5 w-5 shrink-0 text-terracotta" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M12 21s6-5.2 6-10a6 6 0 1 0-12 0c0 4.8 6 10 6 10z" />
      <circle cx="12" cy="11" r="2" />
    </svg>
  );
}

type Where = { rue: string; codePostal: string; ville: string };

function readyAddress(collect: Collect) {
  return Boolean(collect.rue.trim() && collect.codePostal.trim() && collect.ville.trim() && collect.feeLabel);
}

export function ServiceBar() {
  const { pathname } = useLocation();
  const { session } = useSession();
  const collect = useCollect();
  const modeRef = useRef<HTMLDivElement>(null);
  const [panel, setPanel] = useState<"" | "mode" | "when" | "where">("");
  const [later, setLater] = useState(false);
  const [draftId, setDraftId] = useState("");
  const [where, setWhere] = useState<Where>({ rue: "", codePostal: "", ville: "" });
  const [whereError, setWhereError] = useState("");
  const [wherePending, setWherePending] = useState(false);
  const [locatePending, setLocatePending] = useState(false);

  useEffect(() => {
    setPanel("");
  }, [pathname]);

  useEffect(() => {
    if (collect.mode !== "delivery" || readyAddress(collect)) return;
    setWhere({ rue: collect.rue, codePostal: collect.codePostal, ville: collect.ville });
    setWhereError("");
    setPanel("where");
  }, [pathname, collect.mode, collect.rue, collect.codePostal, collect.ville, collect.feeLabel]);

  function closePanel() {
    if (panel === "where" && !readyAddress(collect)) {
      setCollect({ ...collect, mode: "pickup" });
    }
    setPanel("");
  }

  useEffect(() => {
    if (!panel) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closePanel();
    };
    const onPointer = (event: MouseEvent) => {
      if (panel !== "mode") return;
      if (modeRef.current && !modeRef.current.contains(event.target as Node)) setPanel("");
    };
    window.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [panel, collect]);

  if (!ordering(pathname) || !session) return null;

  const slots = session.slots ?? [];
  const point = (session.points ?? [])[0];
  const address = point?.address || session.restaurant.address;
  const chosen = resolveSlot(slots, collect);
  const asap = collect.asap || !chosen || String(chosen.id) === String(slots[0]?.id);
  const deliveryOpen = session.restaurant.deliveryOpen;
  const delivered = collect.mode === "delivery" && readyAddress(collect);

  function openWhen() {
    const current = resolveSlot(slots, collect);
    setLater(!(collect.asap || !current || String(current.id) === String(slots[0]?.id)));
    setDraftId(current ? String(current.id) : "");
    setPanel("when");
  }

  function openWhere() {
    setWhere({ rue: collect.rue, codePostal: collect.codePostal, ville: collect.ville });
    setWhereError("");
    setPanel("where");
  }

  function chooseDelivery() {
    if (readyAddress(collect)) {
      setCollect({ ...collect, mode: "delivery" });
      setPanel("");
      return;
    }
    openWhere();
  }

  function validateWhen() {
    if (later) {
      if (!draftId) return;
      setCollect({ ...collect, asap: false, slotId: draftId });
    } else {
      setCollect({ ...collect, asap: true, slotId: "" });
    }
    setPanel("");
  }

  async function validateWhere() {
    const rue = where.rue.trim();
    const codePostal = where.codePostal.trim();
    const ville = where.ville.trim();
    if (rue.length < 4 || codePostal.length < 4 || ville.length < 2) {
      setWhereError("Indique une adresse complète pour calculer les frais.");
      return;
    }
    setWherePending(true);
    setWhereError("");
    try {
      const result = await api<{ feeLabel: string; meters: number }>("/api/livraison/estimer", {
        method: "POST",
        body: { rue, codePostal, ville },
      });
      setCollect({
        ...collect,
        mode: "delivery",
        rue,
        codePostal,
        ville,
        feeLabel: result.feeLabel,
      });
      setPanel("");
    } catch (error: unknown) {
      setWhereError(error instanceof ApiError ? error.message : "Le tarif n'a pas pu être calculé.");
    } finally {
      setWherePending(false);
    }
  }

  function useLocationNow() {
    if (!navigator.geolocation) {
      setWhereError("La localisation n'est pas disponible sur cet appareil.");
      return;
    }
    setLocatePending(true);
    setWhereError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        void (async () => {
          try {
            const result = await api<{
              rue: string;
              codePostal: string;
              ville: string;
              feeLabel?: string;
              feeError?: string;
              incomplete?: boolean;
            }>("/api/livraison/localisation", {
              method: "POST",
              body: {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
              },
            });
            const next = {
              rue: result.rue || "",
              codePostal: result.codePostal || "",
              ville: result.ville || "",
            };
            setWhere(next);
            if (result.feeLabel && next.rue && next.codePostal && next.ville) {
              setCollect({
                ...collect,
                mode: "delivery",
                rue: next.rue,
                codePostal: next.codePostal,
                ville: next.ville,
                feeLabel: result.feeLabel,
              });
              setPanel("");
              return;
            }
            if (result.feeError) {
              setWhereError(result.feeError);
            } else if (result.incomplete || !next.rue || !next.codePostal || !next.ville) {
              setWhereError("Adresse incomplète. Complétez-la puis validez pour calculer les frais.");
            } else {
              setWhereError("Les frais n'ont pas pu être calculés. Vérifiez l'adresse puis validez.");
            }
          } catch (error: unknown) {
            setWhereError(error instanceof ApiError ? error.message : "La position n'a pas pu être lue.");
          } finally {
            setLocatePending(false);
          }
        })();
      },
      () => {
        setLocatePending(false);
        setWhereError("Autorisez la localisation pour remplir l'adresse.");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  }

  const place = delivered
    ? `${collect.rue}, ${collect.codePostal} ${collect.ville}${collect.feeLabel ? ` · ${collect.feeLabel}` : ""}`
    : address;

  return (
    <div className="relative z-10 border-b border-line bg-cream text-ink">
      <div className="mx-auto grid max-w-7xl grid-cols-3 divide-x divide-line">
        <div className="relative min-w-0" ref={modeRef}>
          <div className="flex min-h-12 w-full items-center gap-1.5 px-2 py-1.5 text-left sm:min-h-16 sm:gap-3 sm:px-5 sm:py-2">
            {delivered ? <Pin /> : <Bag />}
            <span className="min-w-0">
              <button
                className="flex items-center gap-1 text-[0.62rem] font-semibold uppercase tracking-[0.1em] text-terracotta sm:text-xs sm:tracking-[0.12em]"
                type="button"
                aria-expanded={panel === "mode"}
                aria-haspopup="listbox"
                onClick={() => setPanel((open) => (open === "mode" ? "" : "mode"))}
              >
                {delivered ? "Livraison" : "Click & Collect"}
                <Chevron />
              </button>
              {delivered ? (
                <button className="mt-0.5 line-clamp-2 text-left text-[0.7rem] leading-snug text-ink sm:text-sm" type="button" onClick={openWhere}>
                  {place}
                </button>
              ) : (
                <span className="mt-0.5 line-clamp-2 block text-[0.7rem] leading-snug text-ink sm:text-sm">{address}</span>
              )}
            </span>
          </div>
          {panel === "mode" ? (
            <div className="absolute left-0 top-full z-40 w-full min-w-52 border border-line bg-cream" role="listbox" aria-label="Mode">
              <button
                className="block min-h-12 w-full px-4 text-left text-sm hover:bg-paper-2"
                type="button"
                role="option"
                aria-selected={collect.mode === "pickup"}
                onClick={() => {
                  setCollect({ ...collect, mode: "pickup" });
                  setPanel("");
                }}
              >
                Click &amp; Collect
              </button>
              {deliveryOpen ? (
                <button
                  className="block min-h-12 w-full border-t border-line px-4 text-left text-sm hover:bg-paper-2"
                  type="button"
                  role="option"
                  aria-selected={collect.mode === "delivery"}
                  onClick={chooseDelivery}
                >
                  Livraison
                </button>
              ) : null}
              {delivered ? (
                <button
                  className="block min-h-12 w-full border-t border-line px-4 text-left text-sm hover:bg-paper-2"
                  type="button"
                  onClick={openWhere}
                >
                  Modifier l'adresse
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
        <div className="min-w-0">
          <button
            className="flex min-h-12 w-full flex-col justify-center px-2 py-1.5 text-left sm:min-h-16 sm:px-5 sm:py-2"
            type="button"
            aria-haspopup="dialog"
            aria-expanded={panel === "when"}
            onClick={openWhen}
          >
            <span className="flex items-center gap-1 text-[0.62rem] font-semibold uppercase tracking-[0.1em] text-terracotta sm:text-xs sm:tracking-[0.12em]">
              {asap ? "Au plus tôt" : "Créneau"}
              <Chevron />
            </span>
            <span className="mt-0.5 text-[0.7rem] leading-snug text-ink sm:text-sm">
              {chosen ? slotDetail(chosen) : "Aucun créneau ouvert"}
            </span>
          </button>
        </div>
        <Link className="flex min-h-12 min-w-0 flex-col justify-center px-2 py-1.5 sm:min-h-16 sm:px-5 sm:py-2" to="/contact">
          <span className="truncate text-[0.62rem] font-semibold uppercase tracking-[0.1em] text-terracotta sm:text-xs sm:tracking-[0.12em]">
            {session.restaurant.name}
          </span>
          <span className="mt-0.5 text-[0.7rem] underline decoration-line underline-offset-4 sm:text-sm">Nous trouver</span>
        </Link>
      </div>
      {panel === "when" ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-night/40 px-4 pt-24" onClick={closePanel}>
          <div
            className="max-h-[80vh] w-full max-w-lg overflow-y-auto border border-line bg-cream p-5 text-ink"
            role="dialog"
            aria-modal="true"
            aria-labelledby="pour-quand"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="pour-quand" className="font-display text-3xl">Pour quand ?</h2>
            <div className="mt-4 space-y-2">
              <label className="flex min-h-12 cursor-pointer items-center justify-between gap-3 border border-line px-3 text-sm has-checked:border-ink">
                <span>
                  <span className="block">Dès que possible</span>
                  {slots[0] ? <span className="text-ink-soft">{slotDetail(slots[0])}</span> : null}
                </span>
                <input type="radio" name="quand" checked={!later} onChange={() => setLater(false)} />
              </label>
              <label className="flex min-h-12 cursor-pointer items-center justify-between gap-3 border border-line px-3 text-sm has-checked:border-ink">
                <span>Pour plus tard</span>
                <input type="radio" name="quand" checked={later} onChange={() => setLater(true)} />
              </label>
            </div>
            {later ? (
              slots.length ? (
                <SlotCalendar slots={slots} selectedId={draftId} onSelect={setDraftId} />
              ) : (
                <p className="mt-4 text-sm text-terracotta-deep">Aucun créneau n'est ouvert.</p>
              )
            ) : null}
            <div className="mt-5 flex gap-3">
              <button className={btn} type="button" disabled={later && !draftId} onClick={validateWhen}>Valider</button>
              <button className="min-h-12 px-3 text-sm underline" type="button" onClick={closePanel}>Fermer</button>
            </div>
          </div>
        </div>
      ) : null}
      {panel === "where" ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-night/40 px-4 pt-24" onClick={closePanel}>
          <div
            className="w-full max-w-lg border border-line bg-cream p-5 text-ink"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ou-livrer"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="ou-livrer" className="font-display text-3xl">Où vous livrer ?</h2>
            <label className="mt-4 flex flex-col gap-1.5 text-sm">
              <span>Rue</span>
              <input className="min-h-12 border border-line bg-cream px-3" autoComplete="street-address" value={where.rue} onChange={(event) => setWhere((current) => ({ ...current, rue: event.target.value }))} />
            </label>
            <div className="mt-3 grid gap-3 sm:grid-cols-[8rem_1fr]">
              <label className="flex flex-col gap-1.5 text-sm">
                <span>Code postal</span>
                <input className="min-h-12 border border-line bg-cream px-3" autoComplete="postal-code" value={where.codePostal} onChange={(event) => setWhere((current) => ({ ...current, codePostal: event.target.value }))} />
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span>Ville</span>
                <input className="min-h-12 border border-line bg-cream px-3" autoComplete="address-level2" value={where.ville} onChange={(event) => setWhere((current) => ({ ...current, ville: event.target.value }))} />
              </label>
            </div>
            <button
              className="mt-4 inline-flex min-h-12 items-center gap-2 rounded-xl border border-line px-3 text-sm text-ink hover:border-ink disabled:opacity-50"
              type="button"
              disabled={locatePending || wherePending}
              onClick={useLocationNow}
            >
              <Pin />
              {locatePending ? "Localisation et frais…" : "Ajouter ma localisation"}
            </button>
            <p className="mt-3 text-sm text-ink-soft">
              Un clic remplit l'adresse et calcule les frais. Sinon saisissez l'adresse puis validez.
            </p>
            {whereError ? <p className="mt-3 text-sm text-terracotta-deep" role="alert">{whereError}</p> : null}
            <div className="mt-5 flex gap-3">
              <button className={btn} type="button" disabled={wherePending || locatePending} onClick={() => void validateWhere()}>
                {wherePending ? "Calcul…" : "Valider"}
              </button>
              <button className="min-h-12 px-3 text-sm underline" type="button" onClick={closePanel}>Fermer</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
