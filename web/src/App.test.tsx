import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MENU_VIDE, NOTIFICATIONS, REGLAGES, mockApi } from "./test/api-mock";
import { rendreApp } from "./test/rendre";

const API = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS,
  "GET /api/reglages": REGLAGES,
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
    expect(screen.getByText("Arrive à l'étape 2 du plan")).toBeInTheDocument();

    await utilisateur.click(menu.getByRole("link", { name: "Accueil" }));
    expect(screen.getByText("Arrive à l'étape 11 du plan")).toBeInTheDocument();
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
    ["/styles", "Styles", 2],
  ])("%s (%s) affiche « Arrive à l'étape %i du plan »", async (chemin, titre, etape) => {
    mockApi(API);
    rendreApp(chemin);
    expect(screen.getByRole("heading", { level: 1, name: titre })).toBeInTheDocument();
    expect(screen.getByText(`Arrive à l'étape ${etape} du plan`)).toBeInTheDocument();
    // Attend la fin des chargements du menu et des notifications
    expect(await screen.findByText("Aucune collection épinglée")).toBeInTheDocument();
    await screen.findByRole("button", { name: "Notifications : 1 nouvelle" });
  });

  it("le bouton Nouveau lot mène aux lots", async () => {
    mockApi(API);
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await screen.findByText("Aucune collection épinglée");
    await utilisateur.click(screen.getByRole("link", { name: "Nouveau lot" }));
    expect(screen.getByRole("heading", { level: 1, name: "Lots" })).toBeInTheDocument();
  });
});
