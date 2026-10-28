import type { Menu } from "../api/types";

export type CleBadge = keyof Menu["badges"];

export interface EntreeMenu {
  libelle: string;
  chemin: string;
  /** Tracé de l'icône (viewBox 24), utilisé par la barre d'onglets du téléphone. */
  icone: string;
  badge?: CleBadge;
}

/* Les quatre entrées de la maquette (docs/maquette). « Créer » ouvre le formulaire de création d'un projet. */
export const ENTREES: EntreeMenu[] = [
  { libelle: "Créer", chemin: "/lots/nouveau", icone: "M12 5v14M5 12h14" },
  {
    libelle: "Projets",
    chemin: "/lots",
    icone: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    badge: "lots",
  },
  { libelle: "Bibliothèque", chemin: "/bibliotheque", icone: "M12 3 4 7v10l8 4 8-4V7zM4 7l8 4 8-4M12 11v10", badge: "bibliotheque" },
  {
    libelle: "Styles",
    chemin: "/styles",
    icone:
      "M12 21a9 9 0 1 1 9-9c0 2-1.5 3-3.5 3H15a2 2 0 0 0-1.5 3.3c.6.8 0 2.7-1.5 2.7zM8 9.5h.01M14 7.5h.01M17 12.5h.01",
  },
];

/** Le menu est chargé une fois par l'en-tête ; la barre d'onglets le reçoit pour afficher les mêmes badges. */
export function valeurBadge(menu: Menu | null, cle?: CleBadge): number {
  return cle && menu ? menu.badges[cle] : 0;
}

/** « Créer » (/lots/nouveau) et « Projets » (/lots et ses sous-pages) ne doivent jamais être actifs ensemble. */
export function estActif(chemin: string, pathname: string): boolean {
  if (chemin === "/lots") return pathname === "/lots" || (pathname.startsWith("/lots/") && !pathname.startsWith("/lots/nouveau"));
  return pathname === chemin || pathname.startsWith(`${chemin}/`);
}
