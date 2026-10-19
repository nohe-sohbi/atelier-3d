import type { CleEtapeLot, ObjetLot, ResumeBrief, Voie } from "../../api/types";
import { dateCourte, formatNombre, pluriel } from "../Styles/commun";

export { pluriel };

export const LIBELLES_VOIES: Record<Voie, string> = {
  code: "Code",
  ia: "IA",
  mixte: "Mixte",
  cc0: "CC0",
  a_creer: "À créer",
  reutilise: "Réutilisé",
  hors_perimetre: "Hors périmètre",
};

/** Étape du plan qui construit chaque écran de lot (les écrans 2 à 4 ne sont pas encore construits). */
export const ETAPE_DU_PLAN: Record<CleEtapeLot, number> = { brief: 3, references: 6, generation: 4, revue: 8 };

export const CLES_ETAPES: CleEtapeLot[] = ["brief", "references", "generation", "revue"];

export function nomDuLot(nom: string): string {
  return nom.trim() || "Lot sans nom";
}

const decimales = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** « 0,65 × 1,10 m » : largeur × hauteur, comme la maquette ; « — » sans dimensions. */
export function texteDimensions(d: ObjetLot["dimensions"]): string {
  if (!d) return "—";
  return `${decimales.format(d.largeur)} × ${decimales.format(d.hauteur)} m`;
}

/** « il y a 12 min », « il y a 5 h », « hier », puis la date courte. */
export function ilYA(iso: string, maintenant: Date = new Date()): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const minutes = Math.floor((maintenant.getTime() - d.getTime()) / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  if (minutes < 24 * 60 && d.getDate() === maintenant.getDate()) return `il y a ${Math.floor(minutes / 60)} h`;
  const hier = new Date(maintenant);
  hier.setDate(hier.getDate() - 1);
  if (d.toDateString() === hier.toDateString()) return "hier";
  return dateCourte(iso);
}

/** « 3 à fabriquer · 1 importé en CC0 · 0 réutilisé · ≈ 42 crédits Meshy · 2 générateurs à écrire avant de lancer ». */
export function texteResume(r: ResumeBrief): string {
  const parties = [
    `${formatNombre.format(r.a_fabriquer)} à fabriquer`,
    `${pluriel(r.cc0, "importé", "importés")} en CC0`,
    pluriel(r.reutilises, "réutilisé", "réutilisés"),
    `≈ ${pluriel(r.credits_estimes, "crédit", "crédits")} Meshy`,
  ];
  if (r.a_creer > 0) parties.push(`${pluriel(r.a_creer, "générateur", "générateurs")} à écrire avant de lancer`);
  return parties.join(" · ");
}
