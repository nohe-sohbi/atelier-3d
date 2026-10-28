import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { PageAVenir } from "./components/PageAVenir";
import { Creer } from "./pages/Creer/Creer";
import { Lots } from "./pages/Lots/Lots";
import { OuvrirLot } from "./pages/Lots/OuvrirLot";
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
  { chemin: "/", titre: "Créer", element: <Creer /> },
  { chemin: "/lots", titre: "Projets", element: <Lots /> },
  { chemin: "/lots/nouveau", titre: "Nouveau projet", element: <Navigate to="/" replace /> },
  { chemin: "/lots/:id", titre: "Projet", element: <OuvrirLot /> },
  { chemin: "/bibliotheque", titre: "Bibliothèque", element: <PageAVenir titre="Bibliothèque" etape={9} /> },
  { chemin: "/assets/:id", titre: "Fiche asset", element: <PageAVenir titre="Fiche asset" etape={9} /> },
  { chemin: "/generateurs", titre: "Générateurs", element: <PageAVenir titre="Générateurs" etape={11} /> },
  { chemin: "/styles", titre: "Styles", element: <Styles /> },
  { chemin: "/reglages", titre: "Réglages", element: <Reglages /> },
  // Les six écrans d'un projet : l'en-tête commun, puis l'écran de l'étape (Validation, Essai, Jeu : à venir). Les clés techniques ne changent pas.
  { chemin: "/lots/:id/brief", titre: "Brief", element: <PageLot etape="brief" /> },
  { chemin: "/lots/:id/references", titre: "Références", element: <PageLot etape="references" /> },
  { chemin: "/lots/:id/generation", titre: "Génération", element: <PageLot etape="generation" /> },
  { chemin: "/lots/:id/revue", titre: "Validation", element: <PageLot etape="revue" /> },
  { chemin: "/lots/:id/essai", titre: "Essai", element: <PageLot etape="essai" /> },
  { chemin: "/lots/:id/jeu", titre: "Jeu", element: <PageLot etape="jeu" /> },
];
