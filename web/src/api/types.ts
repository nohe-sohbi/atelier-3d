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
  /** Mode de l'adaptateur qui a donné ce solde : « simule » doit se voir à l'écran. */
  mode: "simule" | "reel";
  renouvellement: string | null;
}

export interface Menu {
  badges: MenuBadges;
  collections: MenuCollection[];
  /** null quand le solde Meshy n'a pas pu être lu : on le dit, on n'invente rien. */
  credits: MenuCredits | null;
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

/** Réponse de GET /api/notifications. */
export interface Notifications {
  notifications: Notification[];
  non_lues: number;
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

/** Présence des outils, sans les lancer (à l'ouverture de l'écran). Blender absent → un chemin suggéré. */
export interface PresenceOutils {
  blender: { present: boolean; suggestion: string | null };
  gltf_validator: { present: boolean };
  butler: { present: boolean };
  git_lfs: { present: boolean };
}

export interface ReglagesEtat {
  meshy_solde: MeshySolde | null;
  /** Suivi des dépenses : arrive à l'étape 4 du plan. */
  claude_depense_mois: null;
  outils: PresenceOutils;
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
  | "butler"
  | "git_lfs";

/** « Introuvable » : l'outil n'est pas sur la machine ; jamais affiché en vert. */
export type EtatTest = "Connecté" | "Détecté" | "Joignable" | "Introuvable" | "Erreur";

export interface ResultatTest {
  ok: boolean;
  etat: EtatTest;
  message: string;
  details: Record<string, unknown>;
}

/* ---------- Styles (étape 2) ---------- */

export interface Couleur {
  nom: string;
  hex: string;
}

export interface StyleResume {
  id: number;
  code: string;
  nom: string;
  version: number;
  etat: "brouillon" | "valide";
  direction: "stylise" | "semi_realiste";
  description: string;
  palette: Couleur[];
  usage: { lots: number; assets: number };
  cree_le: string;
  valide_le: string | null;
  /** Présent quand le fichier style.yaml ne se lit plus. */
  erreur?: string;
}

export interface Styles {
  styles: StyleResume[];
}

export interface MateriauStyle {
  nom: string;
  base: string;
  hex: string;
  roughness: number;
  metallic: number;
  usage_assets: number;
}

export interface BudgetStyle {
  cle: string;
  libelle: string;
  tris: number | null;
  textures_px: number | null;
}

export interface ImagePlanche {
  id: number;
  fichier: string;
  objet: string;
  gardee: boolean;
  simule: boolean;
  credits: number;
  cree_le: string;
  url: string;
}

export interface VersionStyle {
  id: number;
  code: string;
  version: number;
  note: string;
  date: string;
  etat: string;
}

export interface StyleDetail extends StyleResume {
  theme: string;
  note_version: string;
  parent_id: number | null;
  racine_id: number;
  materiaux: MateriauStyle[];
  budgets: BudgetStyle[];
  texel_density: number;
  unite: string;
  tolerances: Record<string, number>;
  dimensions_m: Record<string, number[]>;
  objets_planche: string[];
  prompts_reference: Record<string, string>;
  planche: ImagePlanche[];
  credits_planche: number;
  inspirations: string[];
  versions: VersionStyle[];
  lots: { id: number; nom: string }[];
  peut_modifier: boolean;
}

/** Corps de POST /api/styles. */
export interface StyleEnvoye {
  nom: string;
  code?: string;
  description: string;
  direction?: "stylise" | "semi_realiste";
  palette: Record<string, string>;
  budgets_depuis: number | null;
  budgets?: Record<string, number>;
  texel_density?: number;
  dimensions_m?: Record<string, number[]>;
}

/** Corps de PUT /api/styles/{id} (tous facultatifs). */
export interface StyleModifie {
  nom?: string;
  description?: string;
  palette?: Record<string, string>;
  budgets_tris?: Record<string, number>;
  texel_density_px_per_m?: number;
}

export interface TacheLancee {
  tache_id: number;
  credits_estimes: number;
}

/* ---------- Tâches ---------- */

export type EtatTache = "en_attente" | "en_cours" | "terminee" | "echouee" | "annulee";

export interface Tache {
  id: number;
  type: string;
  file: string;
  etat: EtatTache;
  erreur: string | null;
  tentatives: number;
  max_tentatives: number;
  resultat: { progression?: { pct: number; texte: string } } | null;
}
