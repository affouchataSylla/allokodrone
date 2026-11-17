import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { api, ApiError } from "../api";
import type { CatalogPayload, Product } from "../types";
import { DishCard } from "../DishCard";
import { Alert, input, Pending, Reveal, useTitle } from "../ui";

export function Menu() {
  useTitle("La carte");
  const [params, setParams] = useSearchParams();
  const category = params.get("categorie") ?? "";
  const query = params.get("q") ?? "";
  const [data, setData] = useState<CatalogPayload | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [draft, setDraft] = useState(query);

  useEffect(() => {
    setDraft(query);
  }, [query]);

  useEffect(() => {
    let cancel = false;
    const search = new URLSearchParams();
    if (category) search.set("categorie", category);
    if (query) search.set("q", query);
    const suffix = search.toString();
    api<CatalogPayload>(`/api/catalogue${suffix ? `?${suffix}` : ""}`)
      .then((payload) => {
        if (!cancel) {
          setData(payload);
          setErrors([]);
        }
      })
      .catch((error: unknown) => {
        if (!cancel) setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, [category, query]);

  function href(slug: string) {
    const next = new URLSearchParams();
    if (slug) next.set("categorie", slug);
    if (query) next.set("q", query);
    const value = next.toString();
    return value ? `/carte?${value}` : "/carte";
  }

  const sections = new Map<string, Product[]>();
  for (const product of data?.products ?? []) {
    const list = sections.get(product.categoryName) ?? [];
    list.push(product);
    sections.set(product.categoryName, list);
  }

  const total = (data?.categories ?? []).reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="mx-auto w-full min-w-0 max-w-6xl px-4 py-8 lg:py-12">
      <h1 className="motion-rise font-display text-[clamp(2.1rem,8vw,3.25rem)] leading-none">La carte</h1>
      <nav className="mt-6 flex flex-wrap gap-2" aria-label="Catégories">
        <Link className={chip(!category)} to={href("")} aria-current={!category ? "page" : undefined}>
          Tout
          {data ? <span className={countClass(!category)}>{total}</span> : null}
        </Link>
        {(data?.categories ?? []).map((item) => (
          <Link
            key={item.slug}
            className={chip(category === item.slug)}
            to={href(item.slug)}
            aria-current={category === item.slug ? "page" : undefined}
          >
            {item.name}
            <span className={countClass(category === item.slug)}>{item.count}</span>
          </Link>
        ))}
      </nav>
      <div className="min-w-0">
        <form
          className="mt-6 flex min-w-0 gap-2"
          role="search"
          onSubmit={(event) => {
            event.preventDefault();
            const next = new URLSearchParams(params);
            if (draft.trim()) next.set("q", draft.trim());
            else next.delete("q");
            setParams(next);
          }}
        >
          <input
            className={input}
            type="search"
            name="q"
            value={draft}
            placeholder="Rechercher un plat"
            aria-label="Rechercher un plat"
            onChange={(event) => setDraft(event.target.value)}
          />
          <button className="inline-flex min-h-12 shrink-0 items-center rounded-xl border border-line px-4 text-sm" type="submit">
            Chercher
          </button>
        </form>
        <div className="mt-6">
          <Alert errors={errors} />
          {!data && !errors.length ? <Pending label="Chargement de la carte" /> : null}
          {data && data.products.length === 0 ? (
            <p className="border-t border-line py-8 text-sm text-ink-soft">Aucun plat ne correspond à cette recherche.</p>
          ) : null}
          {[...sections.entries()].map(([name, products]) => (
            <Reveal key={name}>
            <section className="mt-8">
              <h2 className="font-display text-3xl">{name}</h2>
              <ul className="mt-4 grid grid-cols-1 gap-4 min-[460px]:grid-cols-2 lg:grid-cols-3">
                {products.map((product) => (
                  <li key={product.slug} className="min-w-0">
                    <DishCard product={product} />
                  </li>
                ))}
              </ul>
            </section>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  );
}

function chip(active: boolean) {
  return `inline-flex min-h-11 items-center gap-2 rounded-xl border px-4 text-sm transition-colors duration-300 ${active ? "border-ink bg-night text-cream" : "border-line bg-cream text-ink hover:border-ink"}`;
}

function countClass(active: boolean) {
  return `text-xs tabular-nums ${active ? "text-cream/70" : "text-ink-soft"}`;
}
