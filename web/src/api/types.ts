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
  /** Dépense réelle de l'API Claude ce mois (les appels simulés sont comptés à part, gratuits). */
  claude_depense_mois: DepenseClaude;
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
  /** Images de la planche : une par objet à dessiner, 6 au plus. */
  images_planche: number;
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
  /** null : aucun asset ne note encore ses matériaux (bibliothèque, étape 9). */
  usage_assets: number | null;
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

/** GET /api/styles/estimation-planche : le tarif de l'adaptateur Meshy, seul chiffre affiché. */
export interface EstimationPlanche {
  credits_par_image: number;
  images_max: number;
  simule: boolean;
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

/* ---------- Lots et Brief ---------- */

export type GroupeLots = "tous" | "en_cours" | "termines" | "brouillons";
export type TonLot = "accent" | "run" | "warn" | "good" | "idle";
export type CleEtapeLot = "brief" | "references" | "generation" | "revue" | "essai" | "jeu";
export type Voie = "code" | "ia" | "mixte" | "cc0" | "a_creer" | "reutilise" | "hors_perimetre";

export interface StyleDuLot {
  id: number;
  code: string;
  nom: string;
  version: number;
  racine_id: number;
}

export interface CompteursLot {
  total: number;
  fabriques: number;
  reutilises: number;
  hors_perimetre: number;
  a_creer: number;
  references_a_choisir: number;
  en_generation: number;
  prets_revue: number;
  gardes: number;
  rejetes: number;
  finis: number;
}

/** Où en est un lot : étape 1 à 4, 5 = terminé ; statut, ton et lien calculés par l'API. */
export interface SituationLot {
  etape: number;
  libelle_etape: string;
  statut: string;
  ton: TonLot;
  detail: string;
  lien: string;
  action: string;
  compteurs: CompteursLot;
}

export interface LotResume extends SituationLot {
  id: number;
  nom: string;
  theme: string;
  nb_objets: number;
  style: StyleDuLot | null;
  etat: string;
  cree_le: string;
  maj_le: string;
}

export interface Lots {
  compteurs: Record<GroupeLots, number>;
  lots: LotResume[];
}

export interface EtapeLot {
  cle: CleEtapeLot;
  libelle: string;
  numero: number;
  lien: string;
  atteinte: boolean;
  faite: boolean;
}

/** GET /api/lots/{id}?etape= : l'en-tête des écrans de lot. */
export interface EnTeteLot extends SituationLot {
  id: number;
  nom: string;
  theme: string;
  besoin: string;
  style: StyleDuLot | null;
  style_plus_recent: { id: number; code: string; version: number } | null;
  etat: string;
  cree_le: string;
  maj_le: string;
  duplique_de_id: number | null;
  credits_prevus: number;
  proposition_tache_id: number | null;
  nom_propose: string | null;
  etape_courante: number;
  etapes: EtapeLot[];
  ligne_etat: string;
}

export interface PieceObjet {
  id: number;
  ordre: number;
  nom: string;
  nature: string;
  type_objet: string;
  voie: Voie;
  generateur: string | null;
  etape: string;
}

export interface ObjetLot {
  id: number;
  lot_id: number;
  nom: string;
  type_objet: string;
  description: string;
  categorie: string;
  nature: string;
  voie: Voie;
  raison_voie: string;
  voie_forcee: boolean;
  retire: boolean;
  etape: string;
  dimensions: { largeur: number; profondeur: number; hauteur: number; source: string } | null;
  generateur: string | null;
  pieces: PieceObjet[];
}

export interface ResumeBrief {
  retenus: number;
  a_fabriquer: number;
  cc0: number;
  reutilises: number;
  hors_perimetre: number;
  a_creer: number;
  credits_estimes: number;
  credits_par_objet_ia: number;
}

/** GET /api/lots/{id}/objets (et la réponse de PATCH …/objets/{oid}). */
export interface ObjetsLot {
  lot_id: number;
  objets: ObjetLot[];
  resume: ResumeBrief;
  proposition: { id: number; etat: EtatTache; erreur: string | null } | null;
  simule: boolean;
}

/** GET/POST /api/lots/{id}/objets/{oid}/demande : la fenêtre « Demande pour Claude Code ». */
export interface DemandeClaudeCode {
  lot_id: number;
  objet_id: number;
  objet: string;
  type_objet: string;
  chemin_md: string;
  script_attendu: string;
  markdown: string;
  texte_a_coller: string;
  etat: "a_ecrire" | "ecrite" | "script_detecte";
  libelle_etat: string;
  ecrite_le: string | null;
  script_detecte_le: string | null;
  tests: { disponibles: boolean; raison: string };
  voie_objet: Voie;
}

/** GET /api/lots/{id}/appliquer-style?style_id= : l'estimation de « Appliquer la vN ». */
export interface EstimationAppliquerStyle {
  objets_code: string[];
  objets_ia: string[];
  credits: number;
  lancement_possible: boolean;
  raison: string;
}

/* ---------- File de tâches, coûts, Génération ---------- */

export interface DepenseClaude {
  usd: number;
  appels: number;
  briefs: number;
  avis: number;
  appels_simules: number;
  /** Appels réels dont le modèle n'a pas de tarif connu : comptés, mais pas chiffrés. */
  sans_tarif: number;
}

export interface EtatWorker {
  actif: boolean;
  battu_le: string | null;
  demarre_le: string | null;
  arrete_le: string | null;
  en_cours: number;
  en_attente: number;
}

export interface TacheVue {
  id: number;
  type: string;
  libelle: string;
  file: string;
  libelle_file: string;
  etat: EtatTache;
  tentatives: number;
  max_tentatives: number;
  erreur: string | null;
  progression: { pct: number; texte: string } | null;
  cree_le: string;
  debute_le: string | null;
  fini_le: string | null;
  reprise_le: string | null;
  lot_id: number | null;
  objet_id: number | null;
  peut_relancer: boolean;
  peut_annuler: boolean;
  /** Réglages · File de tâches : le lot ou le style de la tâche. */
  contexte?: { libelle: string; lien: string } | null;
}

export interface TachesRecentes {
  worker: EtatWorker;
  taches: TacheVue[];
}

export interface JournalTache {
  tache_id: number;
  evenements: Array<{ id: number; date: string; type: string; niveau: string; titre: string; texte: string }>;
}

export interface PuceEtape {
  cle: string;
  libelle: string;
  etat: "fait" | "en_cours" | "a_faire" | "echec";
}

export interface ObjetGeneration {
  id: number;
  nom: string;
  voie: Voie;
  fournisseur: string;
  etapes: PuceEtape[];
  statut: string;
  ton: TonLot;
  pct: number;
  /** Le dernier essai de fabrication (étape 5), s'il y en a un. */
  essai: { id: number; numero: number; etat: string; erreur: string | null } | null;
  vignette: string | null;
  planche: string | null;
  asset_id: string | null;
  peut_fabriquer: boolean;
  /** Pourquoi l'objet ne peut pas être fabriqué maintenant. */
  motif: string | null;
  /** Objet code en échec : il peut repartir d'une autre variante, choisie aux Références. */
  peut_rechoisir: boolean;
}

/** GET /api/lots/{id}/generation */
export interface Generation {
  lot_id: number;
  tuiles: {
    prets_revue: number;
    fabriques: number;
    en_cours: number;
    relances: number;
    credits_utilises: number;
    credits_simules: boolean;
    credits_prevus: number;
  };
  objets: ObjetGeneration[];
  reutilises: string[];
  taches: TacheVue[];
  generateurs: Array<{ nom: string; detail: string; etat: string; ton: TonLot }>;
  worker: EtatWorker;
  fabrication: { autres_voies: number; raison_ia: string };
  limites_files: Record<string, number>;
}

/** Une proposition de l'écran Références : image Meshy, variante Blender, ou image donnée par l'utilisateur. */
export interface Proposition {
  id: number;
  genre: "image" | "variante" | "perso";
  serie: number;
  rang: number;
  /** Variante : ce qui la distingue (« Motif foudre · Courbure 0,35 ») ; image donnée : « Ton image ». */
  legende: string;
  url: string;
  simule: boolean;
  choisie: boolean;
}

export interface ObjetReferences {
  id: number;
  nom: string;
  voie: Voie;
  /** « images » : voie IA ou mixte ; « variantes » : voie code. */
  genre: "images" | "variantes";
  etape: string;
  /** Objet mixte : la pièce faite par IA, seule à recevoir des images. */
  piece_ia: string | null;
  /** La phrase envoyée à l'IA (objets IA) ; null pour un objet code. */
  consigne: string | null;
  consigne_modifiee: boolean;
  /** Aux Références et pas encore lancé : on peut encore choisir. */
  peut_changer: boolean;
  choix_id: number | null;
  propositions: Proposition[];
  series: number;
  preparation: { tache_id: number; etat: EtatTache; pct: number | null; texte: string | null } | null;
  erreur: { tache_id: number; message: string; peut_relancer: boolean } | null;
}

/** GET /api/lots/{id}/references */
export interface References {
  lot_id: number;
  objets: ObjetReferences[];
  choisies: number;
  a_choisir: number;
  /** Objets encore sans référence : mis de côté au lancement. */
  sans_choix: string[];
  /** Objets qui n'ont pas besoin de référence (import CC0). */
  sans_reference: string[];
  deja_lances: number;
  peut_lancer: boolean;
  /** Crédits Meshy d'une série de 4 images. */
  credits_serie: number;
  meshy_simule: boolean;
  style: {
    id: number;
    code: string;
    nom: string;
    palette: Array<{ nom: string; hex: string }>;
    materiaux: string[];
    budgets: Array<{ libelle: string; tris: number | null }>;
    texel_density: number;
    unite: string;
  };
}

/** POST /api/lots/{id}/lancer */
export interface Lancement {
  taches: number[];
  lances: number;
  par_code: number;
  par_ia: number;
  /** Objets mixtes et imports : en attente de la suite de l'étape 7. */
  en_attente: number;
  mis_de_cote: string[];
}
