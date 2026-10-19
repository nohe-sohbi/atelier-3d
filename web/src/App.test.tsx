import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  LOTS_VIDES,
  LOT_CREE,
  LOT_ENTETE_PROPOSE,
  MENU_VIDE,
  NOTIFICATIONS,
  OBJETS,
  OBJETS_VIDES,
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
    for (const libelle of ["Accueil", "Lots", "Bibliothèque", "Générateurs", "Styles"]) {
      expect(menu.getByRole("link", { name: libelle })).toBeInTheDocument();
    }

    await utilisateur.click(menu.getByRole("link", { name: "Lots" }));
    expect(screen.getByRole("heading", { level: 1, name: "Lots" })).toBeInTheDocument();
    expect(await screen.findByText("Aucun lot pour l'instant")).toBeInTheDocument();
    expect(menu.getByRole("link", { name: "Lots" })).toHaveAttribute("aria-current", "page");

    await utilisateur.click(menu.getByRole("link", { name: "Bibliothèque" }));
    expect(screen.getByText("Arrive à l'étape 9 du plan")).toBeInTheDocument();

    await utilisateur.click(menu.getByRole("link", { name: "Générateurs" }));
    expect(screen.getByText("Arrive à l'étape 11 du plan")).toBeInTheDocument();

    await utilisateur.click(menu.getByRole("link", { name: "Styles" }));
    expect(screen.getByRole("heading", { level: 1, name: "Styles" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Rome antique stylisée/ })).toBeInTheDocument();

    await utilisateur.click(menu.getByRole("link", { name: "Accueil" }));
    expect(screen.getByText("Arrive à l'étape 11 du plan")).toBeInTheDocument();

    await utilisateur.click(screen.getByRole("link", { name: "Réglages" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Réglages" })).toBeInTheDocument();
  });

  it.each([
    ["/", "Accueil", 11],
    ["/bibliotheque", "Bibliothèque", 9],
    ["/assets/ROM_PROP_Scutum_A", "Fiche asset", 9],
    ["/generateurs", "Générateurs", 11],
  ])("%s (%s) affiche « Arrive à l'étape %i du plan »", async (chemin, titre, etape) => {
    mockApi(API);
    rendreApp(chemin);
    expect(screen.getByRole("heading", { level: 1, name: titre })).toBeInTheDocument();
    expect(screen.getByText(`Arrive à l'étape ${etape} du plan`)).toBeInTheDocument();
    // Attend la fin des chargements du menu et des notifications
    expect(await screen.findByText("Aucune collection épinglée")).toBeInTheDocument();
    await screen.findByRole("button", { name: "Notifications : 1 nouvelle" });
  });

  it.each([
    ["references", 6],
    ["revue", 8],
  ])("/lots/:id/%s : l'en-tête du lot, puis « Arrive à l'étape %i du plan »", async (etape, numero) => {
    mockApi(API);
    rendreApp(`/lots/${LOT_ENTETE_PROPOSE.id}/${etape}`);
    expect(await screen.findByRole("heading", { level: 1, name: LOT_ENTETE_PROPOSE.nom })).toBeInTheDocument();
    expect(screen.getByText(`Arrive à l'étape ${numero} du plan`)).toBeInTheDocument();
  });

  it("le bouton Nouveau lot crée un lot et ouvre son Brief, pas la liste", async () => {
    mockApi({
      ...API,
      "POST /api/lots": LOT_CREE,
      [`GET /api/lots/${LOT_CREE.id}`]: LOT_CREE,
      [`GET /api/lots/${LOT_CREE.id}/objets`]: OBJETS_VIDES,
    });
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await screen.findByText("Aucune collection épinglée");
    await utilisateur.click(screen.getByRole("link", { name: "Nouveau lot" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Brief" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Brief/ })).toHaveAttribute("aria-current", "step");
  });
});
