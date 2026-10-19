/** Client HTTP minimal : JSON, préfixe /api, erreurs typées {erreur, detail}. */

export class ErreurApi extends Error {
  readonly statut: number;
  readonly erreur: string;
  readonly detail: unknown;

  constructor(statut: number, erreur: string, detail?: unknown) {
    super(erreur);
    this.name = "ErreurApi";
    this.statut = statut;
    this.erreur = erreur;
    this.detail = detail;
  }
}

const PREFIXE = "/api";

export async function api<T>(chemin: string, init?: RequestInit): Promise<T> {
  const entetes = new Headers(init?.headers);
  entetes.set("Accept", "application/json");
  if (init?.body !== undefined && !(init.body instanceof FormData) && !entetes.has("Content-Type")) {
    entetes.set("Content-Type", "application/json");
  }

  let reponse: Response;
  try {
    reponse = await fetch(PREFIXE + chemin, { ...init, headers: entetes });
  } catch {
    throw new ErreurApi(0, "API injoignable", "Le serveur ne répond pas.");
  }

  const texte = await reponse.text();
  let corps: unknown = null;
  if (texte) {
    try {
      corps = JSON.parse(texte);
    } catch {
      corps = texte;
    }
  }

  if (!reponse.ok) {
    const c = (corps ?? {}) as { erreur?: unknown; detail?: unknown };
    const erreur = typeof c.erreur === "string" ? c.erreur : `Erreur ${reponse.status}`;
    throw new ErreurApi(reponse.status, erreur, c.detail);
  }
  return corps as T;
}

export function messageErreur(e: unknown): string {
  if (e instanceof ErreurApi) {
    if (typeof e.detail === "string" && e.detail) return `${e.erreur} : ${e.detail}`;
    return e.erreur;
  }
  if (e instanceof Error) return e.message;
  return "Erreur inconnue";
}
