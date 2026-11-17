import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { asset } from "./base";
import { CalendarMark, InstagramMark, PinMark, PlaneMark } from "./components/brand/Marks";
import { ServiceBar } from "./ServiceBar";
import { useSession } from "./session";

const link = "block text-sm tracking-wide transition-colors duration-300 hover:text-terracotta";

function Item({ to, children, className = "" }: { to: string; children: string; className?: string }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `${link} ${className} ${
          isActive
            ? "text-terracotta underline decoration-2 underline-offset-[0.55rem]"
            : "text-cream"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

function BasketMark() {
  return (
    <svg className="h-[18px] w-[18px] shrink-0" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 9h14l-1.2 10.2a1 1 0 0 1-1 .8H7.2a1 1 0 0 1-1-.8L5 9z" />
      <path d="M8.5 9 10 4.5h4L15.5 9" />
      <path d="M9 13.5v3.5" />
      <path d="M12 13.5v3.5" />
      <path d="M15 13.5v3.5" />
    </svg>
  );
}

const hungry =
  "inline-flex h-9 shrink-0 items-center rounded-xl border border-cream/80 bg-terracotta px-3 text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-white transition-colors duration-300 hover:bg-terracotta-deep sm:h-10 sm:px-5 sm:text-sm";
const cartLink =
  "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-xl border border-cream/75 bg-transparent px-2.5 text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-cream transition-colors duration-300 hover:border-cream sm:h-10 sm:gap-2 sm:px-4 sm:text-sm";

function MenuMark({ open }: { open: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
      {open ? (
        <>
          <path d="M5 5l12 12" />
          <path d="M17 5L5 17" />
        </>
      ) : (
        <>
          <path d="M3 6h16" />
          <path d="M3 11h16" />
          <path d="M3 16h16" />
        </>
      )}
    </svg>
  );
}

export function Shell() {
  const { session, error, refresh } = useSession();
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const count = session?.cartCount ?? 0;
  const restaurant = session?.restaurant;
  const home = pathname === "/";
  const entries: [string, string][] = [
    ["/", "Accueil"],
    ["/concept", "Concept"],
    ["/signature", "Signature"],
    ["/carte", "La carte"],
    ["/avis", "Avis"],
    ["/contact", "Nous trouver"],
  ];

  useEffect(() => {
    setMenuOpen(false);
    if (window.location.hash) return;
    window.scrollTo(0, 0);
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <div className="flex min-h-screen flex-col overflow-x-clip bg-paper font-sans text-ink antialiased">
      <a
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-cream focus:px-3 focus:py-2"
        href="#contenu"
      >
        Aller au contenu
      </a>

      <header className="relative z-50 shrink-0 border-b border-cream/10 bg-night text-cream">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 md:h-[4.5rem] md:gap-6 md:px-6 lg:gap-8 lg:px-8">
          <Link className="flex h-10 w-[9.5rem] shrink-0 items-center overflow-hidden md:h-11 md:w-[11rem]" to="/">
            <img
              className="max-h-10 w-auto max-w-full object-contain object-left md:max-h-11"
              src={asset("images/logo-light.png")}
              width="176"
              height="99"
              alt="ALLOKODRONE"
            />
          </Link>

          <nav className="hidden min-w-0 flex-1 lg:block" aria-label="Navigation principale">
            <ul className="flex items-center justify-center gap-5 xl:gap-7">
              {entries.map(([to, label]) => (
                <li key={to}>
                  <Item to={to}>{label}</Item>
                </li>
              ))}
            </ul>
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
            <NavLink
              to="/panier"
              className={({ isActive }) =>
                `${cartLink} ${isActive ? "border-terracotta text-terracotta" : ""} max-lg:h-10 max-lg:min-w-10 max-lg:justify-center max-lg:gap-1 max-lg:px-2`
              }
              aria-label={count > 0 ? `Panier, ${count} article${count > 1 ? "s" : ""}` : "Panier"}
            >
              <BasketMark />
              <span className="hidden lg:inline">Panier</span>
              {count > 0 ? <span className="tabular-nums text-[0.65rem] lg:text-[0.7rem]">{count}</span> : null}
            </NavLink>
            <Link className={`${hungry} hidden lg:inline-flex`} to={count > 0 ? "/panier" : "/carte"}>
              J&apos;ai faim
            </Link>
            <button
              className="inline-flex h-10 w-10 items-center justify-center text-cream lg:hidden"
              type="button"
              aria-expanded={menuOpen}
              aria-controls="menu-mobile"
              aria-label={menuOpen ? "Fermer le menu" : "Ouvrir le menu"}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <MenuMark open={menuOpen} />
            </button>
          </div>
        </div>

        <nav
          id="menu-mobile"
          className={`${menuOpen ? "block" : "hidden"} border-t border-cream/15 bg-night px-4 py-2 lg:hidden`}
          aria-label="Sections"
        >
          <ul className="flex flex-col">
            {entries.map(([to, label]) => (
              <li key={to} className="border-b border-cream/10 last:border-b-0">
                <Item className="py-3 text-base" to={to}>
                  {label}
                </Item>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      {error ? (
        <div className="border-b border-line bg-paper-2 px-4 py-3 text-sm" role="alert">
          {error}{" "}
          <button className="underline" type="button" onClick={() => void refresh()}>
            Réessayer
          </button>
        </div>
      ) : null}

      {!home ? <ServiceBar /> : null}

      <main id="contenu" className="relative z-0 min-w-0 flex-1">
        <div key={pathname} className="motion-fade">
          <Outlet />
        </div>
      </main>

      <footer className="relative z-0 mt-auto bg-night text-cream">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8 lg:px-8 lg:py-14">
          <div>
            <Link to="/" className="inline-block">
              <img className="max-h-12 w-auto max-w-[10rem] object-contain" src={asset("images/logo-light.png")} width="176" height="99" alt="ALLOKODRONE" />
            </Link>
            <p className="mt-4 max-w-[14rem] text-[0.7rem] font-semibold uppercase leading-relaxed tracking-[0.14em] text-cream/85">
              L&apos;Afrique servie à grande vitesse.
            </p>
          </div>
          <nav aria-label="Pied de page" className="text-sm lg:pt-2">
            <ul className="space-y-2.5">
              <li>
                <Link className="transition-colors hover:text-terracotta" to="/carte">
                  La carte
                </Link>
              </li>
              <li>
                <Link className="transition-colors hover:text-terracotta" to="/panier">
                  Panier
                </Link>
              </li>
              <li>
                <Link className="transition-colors hover:text-terracotta" to="/contact">
                  Contact
                </Link>
              </li>
            </ul>
          </nav>
          <div className="lg:pt-1">
            <h2 className="text-sm font-semibold tracking-wide">Restaurant</h2>
            <ul className="mt-4 space-y-3 text-sm text-cream/80">
              <li className="flex items-start gap-2.5">
                <PinMark className="mt-0.5 h-[18px] w-[18px] shrink-0 text-terracotta" />
                <span>{restaurant?.address ?? "24 rue Emmanuel Arago, 93130 Noisy-le-Sec"}</span>
              </li>
              {(restaurant?.hoursLines?.length
                ? restaurant.hoursLines
                : [restaurant?.hoursLabel ?? "Lundi – samedi : 11h30 – 22h30"]
              ).map((line) => (
                <li key={line} className="flex items-start gap-2.5">
                  <CalendarMark className="mt-0.5 h-[18px] w-[18px] shrink-0 text-terracotta" />
                  <span>{line.replace(/ · /g, " : ")}</span>
                </li>
              ))}
              <li>
                <a
                  className="inline-flex items-center gap-2.5 transition-colors hover:text-terracotta"
                  href={
                    restaurant?.maps ??
                    "https://www.google.com/maps/dir/?api=1&destination=24+rue+Emmanuel+Arago+93130+Noisy-le-Sec"
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <PlaneMark className="h-[18px] w-[18px] shrink-0 text-terracotta" />
                  Itinéraire
                </a>
              </li>
            </ul>
          </div>
          <div className="lg:pt-1">
            <h2 className="text-sm font-semibold tracking-wide">Réseaux</h2>
            <ul className="mt-4 space-y-3 text-sm">
              <li>
                <a
                  className="inline-flex items-center gap-2.5 transition-colors hover:text-terracotta"
                  href={restaurant?.instagram ?? "https://www.instagram.com/alloko_drone/"}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <InstagramMark className="h-[18px] w-[18px] shrink-0 text-terracotta" />
                  Instagram
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-cream/20">
          <p className="mx-auto max-w-6xl px-4 py-4 text-center text-xs text-cream/55 lg:px-8">
            © 2026 ALLOKODRONE. Tous droits réservés.
          </p>
        </div>
      </footer>
    </div>
  );
}
