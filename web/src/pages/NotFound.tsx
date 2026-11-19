import { Link } from "react-router";
import { btn, useTitle } from "../ui";

export function NotFound() {
  useTitle("Page introuvable");
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-terracotta">404</p>
      <h1 className="mt-3 font-display text-5xl leading-none">Cette page n'existe pas</h1>
      <p className="mt-4 text-sm text-ink-soft">Le lien est invalide ou le plat n'est plus affiché ici.</p>
      <Link className={`${btn} mt-6`} to="/carte">Retour à la carte</Link>
    </div>
  );
}
