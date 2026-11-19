import { apiUrl } from "./base";

export class ApiError extends Error {
  status: number;
  errors: string[];

  constructor(errors: string[], status: number) {
    super(errors[0] || "La requête a échoué.");
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

let csrf = "";
let csrfWarm: Promise<void> | null = null;
const credentials: RequestCredentials = apiUrl("/").startsWith("http") ? "include" : "same-origin";

export function setCsrf(value: string) {
  csrf = value;
}

async function ensureCsrf() {
  if (csrf) return;
  if (!csrfWarm) {
    csrfWarm = (async () => {
      const response = await fetch(apiUrl("/api/session"), {
        method: "GET",
        credentials,
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new ApiError(["Session indisponible. Rechargez la page."], response.status);
      const data = (await response.json()) as { csrf?: string };
      if (!data.csrf) throw new ApiError(["Session indisponible. Rechargez la page."], 400);
      csrf = data.csrf;
    })().finally(() => {
      csrfWarm = null;
    });
  }
  await csrfWarm;
}

export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const method = init?.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET" && method !== "HEAD") {
    await ensureCsrf();
    headers["Content-Type"] = "application/json";
    headers["X-CSRF"] = csrf;
  }
  const url = path.startsWith("http") ? path : apiUrl(path);
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      credentials,
      headers,
      body: init?.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch (reason) {
    if (reason instanceof ApiError) throw reason;
    throw new ApiError(["Connexion interrompue. Réessayez."], 0);
  }
  let data: { errors?: string[]; error?: string; csrf?: string } = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) {
    const errors = Array.isArray(data.errors) ? data.errors : [data.error || "La requête a échoué."];
    // Après un retour Stripe, le jeton peut être périmé : on en prend un neuf et on retente une fois.
    if (response.status === 400 && errors[0] === "Requete refusee." && method !== "GET" && method !== "HEAD") {
      csrf = "";
      await ensureCsrf();
      headers["X-CSRF"] = csrf;
      const retry = await fetch(url, {
        method,
        credentials,
        headers,
        body: init?.body === undefined ? undefined : JSON.stringify(init.body),
      });
      let retryData: { errors?: string[]; error?: string } = {};
      try {
        retryData = await retry.json();
      } catch {
        retryData = {};
      }
      if (!retry.ok) {
        const retryErrors = Array.isArray(retryData.errors)
          ? retryData.errors
          : [retryData.error || "La requête a échoué."];
        throw new ApiError(retryErrors, retry.status);
      }
      return retryData as T;
    }
    throw new ApiError(errors, response.status);
  }
  return data as T;
}

export async function apiUpload<T>(path: string, body: FormData): Promise<T> {
  await ensureCsrf();
  const url = path.startsWith("http") ? path : apiUrl(path);
  const request = () =>
    fetch(url, {
      method: "POST",
      credentials,
      headers: { Accept: "application/json", "X-CSRF": csrf },
      body,
    });
  let response: Response;
  try {
    response = await request();
  } catch {
    throw new ApiError(["Connexion interrompue. Réessayez."], 0);
  }
  let data: { errors?: string[]; error?: string } = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok && response.status === 400 && data.error === "Requete refusee.") {
    csrf = "";
    await ensureCsrf();
    response = await request();
    try {
      data = await response.json();
    } catch {
      data = {};
    }
  }
  if (!response.ok) {
    const errors = Array.isArray(data.errors) ? data.errors : [data.error || "La requête a échoué."];
    throw new ApiError(errors, response.status);
  }
  return data as T;
}
