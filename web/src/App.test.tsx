import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  LOTS_VIDES,
  LOT_ENTETE_VALIDATION,
  VALIDATION,
  LOT_ENTETE_PROPOSE,
  MENU_VIDE,
  NOTIFICATIONS,
  OBJETS,
  REFERENCES,
  REGLAGES,
  STYLES,
  STYLE_DETAIL,
  mockApi,
} from "./test/api-mock";
import { rendreApp } from "./test/rendre";

const API = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS,
  "GET /api/reglages": REGLAGES,
  "GET /api/styles": STYLES,
  [`GET /api/styles/${STYLE_DETAIL.id}`]: STYLE_DETAIL,
  "GET /api/lots": LOTS_VIDES,
  [`GET /api/lots/${LOT_ENTETE_PROPOSE.id}`]: LOT_ENTETE_PROPOSE,
  [`GET /api/lots/${LOT_ENTETE_PROPOSE.id}/objets`]: OBJETS,
};

afterEach(() => vi.unstubAllGlobals());

describe("Navigation", () => {
  it("affiche les entrées du menu et chaque entrée ouvre sa page", async () => {
    mockApi(API);
    const utilisateur = userEvent.setup();
    rendreApp("/");
    const menu = within(screen.getByRole("navigation", { name: "Menu principal" }));
    for (const libelle of ["Créer", "Projets", "Bibliothèque", "Styles"]) {
      expect(menu.getByRole("link", { name: libelle })).toBeInTheDocument();
    }
    expect(menu.getByRole("link", { name: "Créer" })).toHaveAttribute("href", "/");

    await utilisateur.click(menu.getByRole("link", { name: "Projets" }));
    expect(screen.getByRole("heading", { level: 1, name: "Projets" })).toBeInTheDocument();
    expect(await screen.findByText("Aucun projet pour l'instant")).toBeInTheDocument();
    expect(menu.getByRole("link", { name: "Projets" })).toHaveAttribute("aria-current", "page");

    await utilisateur.click(menu.getByRole("link", { name: "Bibliothèque" }));
    expect(screen.getByText("Arrive à l'étape 9 du plan")).toBeInTheDocument();

    await utilisateur.click(menu.getByRole("link", { name: "Styles" }));
    expect(screen.getByRole("heading", { level: 1, name: "Styles" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Rome antique stylisée/ })).toBeInTheDocument();

    await utilisateur.click(screen.getByRole("link", { name: "Atelier 3D, accueil" }));
    expect(screen.getByRole("heading", { level: 1, name: "Que veux-tu créer ?" })).toBeInTheDocument();
    expect(menu.getByRole("link", { name: "Créer" })).toHaveAttribute("aria-current", "page");

    await utilisateur.click(screen.getByRole("link", { name: "Réglages" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Réglages" })).toBeInTheDocument();
  });

  it.each([
    ["/bibliotheque", "Bibliothèque", 9],
    ["/assets/ROM_PROP_Scutum_A", "Fiche asset", 9],
    ["/generateurs", "Générateurs", 11],
  ])("%s (%s) affiche « Arrive à l'étape %i du plan »", async (chemin, titre, etape) => {
    mockApi(API);
    rendreApp(chemin);
    expect(screen.getByRole("heading", { level: 1, name: titre })).toBeInTheDocument();
    expect(screen.getByText(`Arrive à l'étape ${etape} du plan`)).toBeInTheDocument();
    // Attend la fin des chargements du menu et des notifications
    await screen.findByText(/Renouvelés le 1er novembre/);
    await screen.findByRole("button", { name: "Notifications : 1 nouvelle" });
  });

  it("/lots/:id/references : l'en-tête du projet, puis l'écran Look", async () => {
    mockApi({ ...API, [`GET /api/lots/${LOT_ENTETE_PROPOSE.id}/references`]: REFERENCES });
    rendreApp(`/lots/${LOT_ENTETE_PROPOSE.id}/references`);
    expect(await screen.findByRole("heading", { level: 1, name: LOT_ENTETE_PROPOSE.nom })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Choisis un look par objet" })).toBeInTheDocument();
  });

  it("/lots/:id/revue : l'en-tête du projet, puis la Validation de ses objets", async () => {
    mockApi({ ...API, [`GET /api/lots/${LOT_ENTETE_VALIDATION.id}`]: LOT_ENTETE_VALIDATION, [`GET /api/lots/${LOT_ENTETE_VALIDATION.id}/validation`]: VALIDATION });
    rendreApp(`/lots/${LOT_ENTETE_VALIDATION.id}/revue`);
    expect(await screen.findByRole("heading", { level: 1, name: LOT_ENTETE_VALIDATION.nom })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: VALIDATION.objets[0]!.nom })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Étapes du projet" })).toBeInTheDocument();
  });

  it.each([
    ["essai", "L'essai en scène arrive à l'étape 8 du plan"],
    ["jeu", "La récupération du pack arrive à l'étape 10 du plan"],
  ])("/lots/:id/%s : l'en-tête du projet, puis « %s »", async (etape, texte) => {
    mockApi(API);
    rendreApp(`/lots/${LOT_ENTETE_PROPOSE.id}/${etape}`);
    expect(await screen.findByRole("heading", { level: 1, name: LOT_ENTETE_PROPOSE.nom })).toBeInTheDocument();
    expect(screen.getByText(texte)).toBeInTheDocument();
  });
});
