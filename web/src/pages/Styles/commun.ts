import type { StyleResume } from "../../api/types";

export const formatNombre = new Intl.NumberFormat("fr-FR");

export function dateCourte(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

export function pluriel(n: number, singulier: string, plurielMot: string): string {
  return `${formatNombre.format(n)} ${n > 1 ? plurielMot : singulier}`;
}

export function usageTexte(u: StyleResume["usage"]): string {
  if (u.assets === 0 && u.lots === 0) return "Aucun asset";
  return `${pluriel(u.assets, "asset", "assets")} · ${pluriel(u.lots, "lot", "lots")}`;
}

/** Même règle que l'API (api/services/styles.py::slug) : minuscules sans accent, tirets. */
export function slug(texte: string): string {
  const base = texte
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return base || "style";
}

export function libelleEtat(etat: StyleResume["etat"]): "Actif" | "Brouillon" {
  return etat === "valide" ? "Actif" : "Brouillon";
}

export const NB_IMAGES = 6;
export const CREDITS_PAR_IMAGE = 3;

/** « caisse 0.6 0.4 0.4 » par ligne → {caisse: [0.6, 0.4, 0.4]}. Les lignes incomplètes sont ignorées. */
export function lireDimensions(texte: string): Record<string, number[]> {
  const out: Record<string, number[]> = {};
  for (const ligne of texte.split("\n")) {
    const parties = ligne.trim().split(/[\s;]+/).filter(Boolean);
    if (parties.length < 4) continue;
    const nombres = parties.slice(1, 4).map((p) => Number(p.replace(",", ".")));
    if (nombres.every((n) => Number.isFinite(n) && n > 0)) out[slug(parties[0]!).replace(/-/g, "_")] = nombres;
  }
  return out;
}
