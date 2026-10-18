/* Types du contrat API (voir api/). Codés exactement contre le contrat ; pas de champ inventé. */

export interface Sante {
  statut: string;
  version: string;
}

export interface MenuBadges {
  lots: number;
  bibliotheque: number;
  generateurs: number;
}

export interface MenuCollection {
  id: number | string;
  nom: string;
  couleur: string;
  nombre: number;
}

export interface MenuCredits {
  utilises: number;
  total: number;
  restants: number;
  renouvellement: string | null;
}

export interface Menu {
  badges: MenuBadges;
  collections: MenuCollection[];
  credits: MenuCredits;
}

export interface Notification {
  id: number | string;
  date: string;
  type: string;
  niveau: string;
  titre: string;
  texte: string;
  lien: string | null;
  lu: boolean;
}

export interface ResultatRecherche {
  type: string;
  id: number | string;
  titre: string;
  lien: string;
}

export interface Recherche {
  resultats: ResultatRecherche[];
}

export type ModeService = "simule" | "reel";
export type ModeleClaude = "claude-sonnet-5-5" | "claude-haiku-5-5";
export type RenouvellementJour = 1 | 15;
export type AlertePct = 80 | 90 | 0;

export interface ServiceMeshy {
  mode: ModeService;
  cle_api_definie: boolean;
  cle_api_apercu: string;
  credits_mensuels: number;
  renouvellement_jour: RenouvellementJour;
  alerte_pct: AlertePct;
}

export interface ServiceClaude {
  mode: ModeService;
  cle_api_definie: boolean;
  cle_api_apercu: string;
  modele: ModeleClaude;
  plafond_mensuel_usd: number;
}

export interface ServiceComfyui {
  mode: ModeService;
  url: string;
}

export interface ServiceItchio {
  mode: ModeService;
  cle_api_definie: boolean;
  cle_api_apercu: string;
  compte: string;
  canal: string;
}

export interface ReglagesServices {
  meshy: ServiceMeshy;
  claude: ServiceClaude;
  comfyui: ServiceComfyui;
  itchio: ServiceItchio;
}

export interface ReglagesOutils {
  blender: { chemin: string };
  gltf_validator: { chemin: string };
  butler: { chemin: string };
}

export interface ReglagesBibliotheque {
  dossier: string;
  purge_rejets_jours: number;
}

export interface ReglagesFiles {
  gpu: number;
  meshy: number;
  blender: number;
  relances_max: number;
}

export interface ReglagesNotifications {
  app: boolean;
  bureau: boolean;
}

export interface MeshySolde {
  restants: number;
  total: number;
  utilises: number;
  /** Mode de l'adaptateur qui a donné ce solde : « simule » doit se voir à l'écran. */
  mode: "simule" | "reel";
}

export interface ReglagesEtat {
  meshy_solde: MeshySolde | null;
  /** Suivi des dépenses : arrive à l'étape 4 du plan. */
  claude_depense_mois: null;
}

export interface Reglages {
  services: ReglagesServices;
  outils: ReglagesOutils;
  bibliotheque: ReglagesBibliotheque;
  files: ReglagesFiles;
  notifications: ReglagesNotifications;
  etat: ReglagesEtat;
}

/** Clé API envoyée au PUT : string non vide = remplace ; absent = inchangée ; null = effacée. */
export type CleApiEnvoyee = { cle_api?: string | null };

export interface ReglagesEnvoyes {
  services: {
    meshy: ServiceMeshy & CleApiEnvoyee;
    claude: ServiceClaude & CleApiEnvoyee;
    comfyui: ServiceComfyui;
    itchio: ServiceItchio & CleApiEnvoyee;
  };
  outils: ReglagesOutils;
  bibliotheque: ReglagesBibliotheque;
  files: ReglagesFiles;
  notifications: ReglagesNotifications;
}

export type ServiceTestable =
  | "meshy"
  | "claude"
  | "comfyui"
  | "itchio"
  | "blender"
  | "gltf_validator"
  | "butler";

export type EtatTest = "Connecté" | "Détecté" | "Joignable" | "Erreur";

export interface ResultatTest {
  ok: boolean;
  etat: EtatTest;
  message: string;
  details: Record<string, unknown>;
}
