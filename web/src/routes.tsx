import type { ReactElement } from "react";
import { PageAVenir } from "./components/PageAVenir";
import { Reglages } from "./pages/Reglages/Reglages";

export interface Route {
  chemin: string;
  titre: string;
  element: ReactElement;
}

/* Table des routes (docs/maquette/README.md). Les étapes suivantes remplacent PageAVenir par le vrai écran. */
export const ROUTES: Route[] = [
  { chemin: "/", titre: "Accueil", element: <PageAVenir titre="Accueil" etape={11} /> },
  { chemin: "/lots", titre: "Lots", element: <PageAVenir titre="Lots" etape={3} /> },
  { chemin: "/bibliotheque", titre: "Bibliothèque", element: <PageAVenir titre="Bibliothèque" etape={9} /> },
  { chemin: "/assets/:id", titre: "Fiche asset", element: <PageAVenir titre="Fiche asset" etape={9} /> },
  { chemin: "/generateurs", titre: "Générateurs", element: <PageAVenir titre="Générateurs" etape={11} /> },
  { chemin: "/styles", titre: "Styles", element: <PageAVenir titre="Styles" etape={2} /> },
  { chemin: "/reglages", titre: "Réglages", element: <Reglages /> },
  { chemin: "/lots/:id/brief", titre: "Brief", element: <PageAVenir titre="Brief" etape={3} /> },
  { chemin: "/lots/:id/references", titre: "Références", element: <PageAVenir titre="Références" etape={6} /> },
  { chemin: "/lots/:id/generation", titre: "Génération", element: <PageAVenir titre="Génération" etape={4} /> },
  { chemin: "/lots/:id/revue", titre: "Revue", element: <PageAVenir titre="Revue" etape={8} /> },
];
