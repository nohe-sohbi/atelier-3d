import { vi } from "vitest";
import type { EstimationPlanche, Menu, Notifications, Recherche, Reglages, ResultatTest, StyleDetail, Styles, Tache, TacheLancee } from "../api/types";
import contrat from "./contrat.json";

type Reponse = unknown | ((init: RequestInit | undefined, url: URL) => unknown);

export interface AppelApi {
  methode: string;
  chemin: string;
  corps: unknown;
}

/** Monte un fetch simulé : clés "GET /api/menu", "POST /api/notifications/1/lu"… ; enregistre les appels. */
export function mockApi(reponses: Record<string, Reponse>) {
  const appels: AppelApi[] = [];
  const fetchMock = vi.fn(async (entree: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(entree), "http://localhost");
    const methode = (init?.method ?? "GET").toUpperCase();
    const cle = `${methode} ${url.pathname}`;
    const corps = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    appels.push({ methode, chemin: url.pathname + url.search, corps });
    const r = reponses[cle];
    if (r === undefined) {
      return new Response(JSON.stringify({ erreur: "Introuvable", detail: cle }), { status: 404, headers: { "Content-Type": "application/json" } });
    }
    const valeur = typeof r === "function" ? (r as (i: RequestInit | undefined, u: URL) => unknown)(init, url) : r;
    if (valeur instanceof Response) return valeur;
    return new Response(JSON.stringify(valeur), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { appels, fetchMock };
}

export function reponseErreur(statut: number, erreur: string, detail?: unknown) {
  return new Response(JSON.stringify({ erreur, detail }), { status: statut, headers: { "Content-Type": "application/json" } });
}

/* Les données simulées viennent de web/src/test/contrat.json, généré depuis la vraie API par
   `python -m tests.api.contrat_web --ecrire`. Rien n'est écrit à la main ici : si l'API change de forme,
   le fichier change et les tests le voient. */
const c = contrat as unknown as Record<string, unknown>;
const depuis = <T,>(cle: string): T => {
  if (!(cle in c)) throw new Error(`contrat.json ne contient pas « ${cle} » : régénère-le`);
  return c[cle] as T;
};

export const MENU_VIDE = depuis<Menu>("GET /api/menu");
export const MENU_REMPLI = depuis<Menu>("GET /api/menu#rempli");
export const NOTIFICATIONS_VIDES = depuis<Notifications>("GET /api/notifications");
export const NOTIFICATIONS = depuis<Notifications>("GET /api/notifications#rempli");
export const RECHERCHE_VIDE = depuis<Recherche>("GET /api/recherche?q=");
export const REGLAGES_DEFAUT = depuis<Reglages>("GET /api/reglages");
export const REGLAGES = depuis<Reglages>("GET /api/reglages#rempli");
export const STYLES = depuis<Styles>("GET /api/styles");
export const STYLE_DETAIL = depuis<StyleDetail>("GET /api/styles/{id}");
export const ESTIMATION_PLANCHE = depuis<EstimationPlanche>("GET /api/styles/estimation-planche");
/** Un style créé (brouillon), puis le même avec sa planche simulée rangée par le worker. */
export const STYLE_CREE = depuis<StyleDetail>("POST /api/styles");
export const PLANCHE_LANCEE = depuis<TacheLancee>("POST /api/styles/{id}/planche");
export const STYLE_PLANCHE = depuis<StyleDetail>("GET /api/styles/{id}#planche");
export const TACHE_TERMINEE = depuis<Tache>("GET /api/taches/{id}");
export const TACHE_ECHOUEE = depuis<Tache>("GET /api/taches/{id}#echouee");
export const TEST_CONNEXION = (service: string) => depuis<ResultatTest>(`POST /api/reglages/tester/${service}`);
