import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { api, ApiError } from "../api";
import { useSession } from "../session";
import type { User } from "../types";
import { Alert, btn, btnLine, field, input, Pending, useTitle } from "../ui";

type AccountPayload = { user: User | null; orders: { ref: string; statusLabel: string; totalLabel: string }[] };

export function Account() {
  useTitle("Compte");
  const { refresh } = useSession();
  const [data, setData] = useState<AccountPayload | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [pending, setPending] = useState("");

  function load() {
    return api<AccountPayload>("/api/compte").then(setData);
  }

  useEffect(() => {
    let cancel = false;
    load()
      .catch((error: unknown) => {
        if (!cancel) setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  async function send(path: string, body: unknown, event: FormEvent) {
    event.preventDefault();
    setPending(path);
    setErrors([]);
    try {
      await api(path, { method: "POST", body });
      await refresh();
      await load();
    } catch (error: unknown) {
      setErrors(error instanceof ApiError ? error.errors : ["Connexion interrompue. Réessayez."]);
    } finally {
      setPending("");
    }
  }

  if (!data && !errors.length) return <div className="mx-auto max-w-6xl px-4"><Pending /></div>;
  if (data?.user?.role === "admin") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="font-display text-5xl">Administration</h1>
        <p className="mt-4 text-sm text-ink-soft">Vous êtes connecté à l'espace restaurant.</p>
        <a className={`${btn} mt-6`} href="/admin/">Ouvrir l'administration</a>
      </div>
    );
  }
  if (data?.user) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <h1 className="font-display text-5xl">Bonjour {data.user.name}</h1>
        <h2 className="mt-8 font-display text-3xl">Commandes</h2>
        {data.orders.length ? (
          <ul className="mt-4 border-t border-line">
            {data.orders.map((order) => (
              <li key={order.ref} className="border-b border-line py-3">
                <Link className="font-medium hover:text-terracotta" to={`/commande/${order.ref}`}>{order.ref}</Link>
                <span className="text-sm text-ink-soft"> — {order.statusLabel} — {order.totalLabel}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-ink-soft">Aucune commande liée à ce compte.</p>
        )}
        <form className="mt-6" onSubmit={(event) => void send("/api/compte/deconnexion", {}, event)}>
          <button className={btnLine} type="submit" disabled={pending !== ""}>Se déconnecter</button>
        </form>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <Alert errors={errors} />
      <div className="mt-6 grid gap-12 lg:grid-cols-2">
      <section>
        <h1 className="font-display text-5xl">Connexion</h1>
        <form className="mt-2" onSubmit={(event) => void send("/api/compte/connexion", formValues(event), event)}>
          <label className={field}><span>E-mail</span><input className={input} name="email" type="email" required autoComplete="email" /></label>
          <label className={field}><span>Mot de passe</span><input className={input} name="password" type="password" required autoComplete="current-password" /></label>
          <button className={`${btn} mt-5`} type="submit" disabled={pending !== ""}>{pending ? "Connexion…" : "Se connecter"}</button>
        </form>
      </section>
      <section>
        <h2 className="font-display text-4xl">Créer un compte</h2>
        <p className="mt-3 text-sm text-ink-soft">La commande invité reste possible sans compte.</p>
        <form onSubmit={(event) => void send("/api/compte/inscription", formValues(event), event)}>
          <label className={field}><span>Nom</span><input className={input} name="nom" required autoComplete="name" /></label>
          <label className={field}><span>E-mail</span><input className={input} name="email" type="email" required autoComplete="email" /></label>
          <label className={field}><span>Téléphone</span><input className={input} name="telephone" type="tel" autoComplete="tel" /></label>
          <label className={field}><span>Mot de passe</span><input className={input} name="password" type="password" required minLength={10} autoComplete="new-password" /></label>
          <button className={`${btnLine} mt-5`} type="submit" disabled={pending !== ""}>Créer le compte</button>
        </form>
      </section>
      </div>
    </div>
  );
}

function formValues(event: FormEvent) {
  const data = new FormData(event.currentTarget as HTMLFormElement);
  return Object.fromEntries(data.entries());
}
