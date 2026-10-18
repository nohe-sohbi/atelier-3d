import { vi } from "vitest";
import type { Menu, Notification, Reglages } from "../api/types";

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

export const MENU_VIDE: Menu = {
  badges: { lots: 0, bibliotheque: 0, generateurs: 0 },
  collections: [],
  credits: { utilises: 0, total: 0, restants: 0, renouvellement: null },
};

export const MENU_REMPLI: Menu = {
  badges: { lots: 3, bibliotheque: 0, generateurs: 1 },
  collections: [{ id: 7, nom: "Collection test", couleur: "#B5582E", nombre: 8 }],
  credits: { utilises: 426, total: 1000, restants: 574, renouvellement: "Renouvelés le 1er novembre" },
};

export const NOTIFICATIONS: Notification[] = [
  {
    id: 1,
    date: "2026-10-18T08:00:00Z",
    type: "revue_prete",
    niveau: "info",
    titre: "Revue prête · Lot test",
    texte: "4 objets à juger",
    lien: "/lots/1/revue",
    lu: false,
  },
  {
    id: 2,
    date: "2026-10-17T08:00:00Z",
    type: "banc_termine",
    niveau: "info",
    titre: "Banc d'essai terminé",
    texte: "",
    lien: "/generateurs",
    lu: true,
  },
];

export const REGLAGES: Reglages = {
  services: {
    meshy: { mode: "simule", cle_api_definie: true, cle_api_apercu: "••••ab12", credits_mensuels: 1000, renouvellement_jour: 1, alerte_pct: 80 },
    claude: { mode: "simule", cle_api_definie: false, cle_api_apercu: "", modele: "claude-sonnet-5-5", plafond_mensuel_usd: 5.0 },
    comfyui: { mode: "simule", url: "http://127.0.0.1:8188" },
    itchio: { mode: "simule", cle_api_definie: true, cle_api_apercu: "••••zz99", compte: "mon-compte", canal: "assets" },
  },
  outils: { blender: { chemin: "/usr/bin/blender" }, gltf_validator: { chemin: "gltf_validator" }, butler: { chemin: "butler" } },
  bibliotheque: { dossier: "assets/", purge_rejets_jours: 30 },
  files: { gpu: 1, meshy: 3, blender: 2, relances_max: 3 },
  notifications: { app: true, bureau: false },
  etat: {
    meshy_solde: { restants: 574, total: 1000, utilises: 426, mode: "simule" },
    claude_depense_mois: null,
  },
};
