import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MENU_VIDE, NOTIFICATIONS, REGLAGES, STYLES, STYLE_DETAIL, mockApi } from "./test/api-mock";
import { rendreApp } from "./test/rendre";

const API = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS,
  "GET /api/reglages": REGLAGES,
  "GET /api/styles": STYLES,
  [`GET /api/styles/${STYLE_DETAIL.id}`]: STYLE_DETAIL,
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
    expect(screen.getByText("Arrive à l'étape 3 du plan")).toBeInTheDocument();
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
    ["/lots", "Lots", 3],
    ["/lots/4/brief", "Brief", 3],
    ["/lots/4/references", "Références", 6],
    ["/lots/4/generation", "Génération", 4],
    ["/lots/4/revue", "Revue", 8],
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

  it("le bouton Nouveau lot mène à la création d'un lot (étape 3), pas à la liste", async () => {
    mockApi(API);
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await screen.findByText("Aucune collection épinglée");
    await utilisateur.click(screen.getByRole("link", { name: "Nouveau lot" }));
    expect(screen.getByRole("heading", { level: 1, name: "Nouveau lot" })).toBeInTheDocument();
    expect(screen.getByText("Arrive à l'étape 3 du plan")).toBeInTheDocument();
  });
});
