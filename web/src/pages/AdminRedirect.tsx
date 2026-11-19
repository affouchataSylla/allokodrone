import { useEffect } from "react";

/** L’admin est servi par le backend Python sur le même domaine (/admin). */
export function AdminRedirect() {
  useEffect(() => {
    window.location.replace("/admin/promotions");
  }, []);

  return (
    <main className="mx-auto max-w-lg px-4 py-10 text-center">
      <p className="text-sm text-ink-soft">Ouverture des promotions…</p>
      <p className="mt-4">
        <a className="text-terracotta underline" href="/admin/promotions">
          Continuer vers l’admin
        </a>
      </p>
    </main>
  );
}
