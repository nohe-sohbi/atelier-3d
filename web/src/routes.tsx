import type { ReactElement } from "react";
import { PageAVenir } from "./components/PageAVenir";
import { Lots } from "./pages/Lots/Lots";
import { NouveauLot, OuvrirLot } from "./pages/Lots/NouveauLot";
import { PageLot } from "./pages/Lots/PageLot";
import { Reglages } from "./pages/Reglages/Reglages";
import { Styles } from "./pages/Styles/Styles";

export interface Route {
  chemin: string;
  titre: string;
  element: ReactElement;
}

/* Table des routes (docs/maquette/README.md). Les étapes suivantes remplacent PageAVenir par le vrai écran. */
export const ROUTES: Route[] = [
  { chemin: "/", titre: "Accueil", element: <PageAVenir titre="Accueil" etape={11} /> },
  { chemin: "/lots", titre: "Lots", element: <Lots /> },
  { chemin: "/lots/nouveau", titre: "Nouveau lot", element: <NouveauLot /> },
  { chemin: "/lots/:id", titre: "Lot", element: <OuvrirLot /> },
  { chemin: "/bibliotheque", titre: "Bibliothèque", element: <PageAVenir titre="Bibliothèque" etape={9} /> },
  { chemin: "/assets/:id", titre: "Fiche asset", element: <PageAVenir titre="Fiche asset" etape={9} /> },
  { chemin: "/generateurs", titre: "Générateurs", element: <PageAVenir titre="Générateurs" etape={11} /> },
  { chemin: "/styles", titre: "Styles", element: <Styles /> },
  { chemin: "/reglages", titre: "Réglages", element: <Reglages /> },
  // Les quatre écrans d'un lot : l'en-tête commun, puis l'écran de l'étape (Références, Génération, Revue : à venir).
  { chemin: "/lots/:id/brief", titre: "Brief", element: <PageLot etape="brief" /> },
  { chemin: "/lots/:id/references", titre: "Références", element: <PageLot etape="references" /> },
  { chemin: "/lots/:id/generation", titre: "Génération", element: <PageLot etape="generation" /> },
  { chemin: "/lots/:id/revue", titre: "Revue", element: <PageLot etape="revue" /> },
];
