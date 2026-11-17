import { useEffect } from "react";

/** L’admin est servi par le backend Python sur le même domaine (/admin). */
export function AdminRedirect() {
  useEffect(() => {
    window.location.replace("/admin/");
  }, []);

  return (
    <main className="mx-auto max-w-lg px-4 py-16 text-center">
      <p className="text-sm text-ink-soft">Ouverture de l’administration…</p>
      <p className="mt-4">
        <a className="text-terracotta underline" href="/admin/">
          Continuer vers l’admin
        </a>
      </p>
    </main>
  );
}
