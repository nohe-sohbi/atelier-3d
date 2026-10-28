import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MENU_REMPLI, MENU_VIDE, NOTIFICATIONS, NOTIFICATIONS_VIDES, mockApi, reponseErreur } from "../test/api-mock";
import { rendreApp } from "../test/rendre";

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
});
afterEach(() => vi.unstubAllGlobals());

describe("En-tête", () => {
  it("lit /api/menu : badges non nuls, crédits restants et crédits utilisés", async () => {
    const { appels } = mockApi({ "GET /api/menu": MENU_REMPLI, "GET /api/notifications": NOTIFICATIONS });
    rendreApp("/");
    const menu = within(screen.getByRole("navigation", { name: "Menu principal" }));

    expect(await menu.findByText("3")).toBeInTheDocument();
    expect(within(menu.getByRole("link", { name: /Projets/ })).getByText("3")).toBeInTheDocument();
    expect(within(menu.getByRole("link", { name: /Bibliothèque/ })).getByText("2")).toBeInTheDocument();
    // La barre d'onglets du téléphone porte les mêmes badges.
    const onglets = within(screen.getByRole("navigation", { name: "Menu du téléphone" }));
    expect(within(onglets.getByRole("link", { name: /Projets/ })).getByText("3")).toBeInTheDocument();

    // On affiche le solde restant (940) ; la jauge dit ce qui est utilisé (60 sur 1 000).
    expect(screen.getByText("940")).toBeInTheDocument();
    const jauge = screen.getByRole("progressbar", { name: "Crédits Meshy utilisés" });
    expect(jauge).toHaveAttribute("aria-valuenow", "60");
    expect(jauge).toHaveAttribute("aria-valuemax", "1000");
    // Le solde vient du simulateur : l'écran le dit.
    expect(screen.getByText(/solde simulé/)).toBeInTheDocument();
    expect(appels.some((a) => a.chemin === "/api/menu")).toBe(true);
  });

  it("sans badge : aucun badge n'est affiché", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp("/");
    await screen.findByText(/Renouvelés le 1er novembre/);
    const menu = within(screen.getByRole("navigation", { name: "Menu principal" }));
    expect(menu.queryByText("0")).not.toBeInTheDocument();
    expect(menu.getByRole("link", { name: "Projets" })).toHaveTextContent(/^Projets$/);
  });

  it("signale une erreur de chargement sans inventer de chiffre", async () => {
    mockApi({ "GET /api/menu": () => reponseErreur(500, "Panne"), "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp("/");
    expect(await screen.findByText(/Menu non chargé : Panne/)).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("dit « Solde Meshy non lu » quand l'API renvoie credits: null, sans chiffre inventé", async () => {
    mockApi({ "GET /api/menu": { ...MENU_VIDE, credits: null }, "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp("/");
    expect(await screen.findByText("Solde Meshy non lu (voir Réglages)")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Crédits Meshy utilisés" })).toHaveAttribute("aria-valuenow", "0");
  });

  it.each([
    ["/lots/nouveau", "Créer"],
    ["/lots", "Projets"],
    ["/lots/12/brief", "Projets"],
    ["/bibliotheque", "Bibliothèque"],
    ["/styles", "Styles"],
  ])("%s : seul « %s » est l'entrée en cours", async (chemin, libelle) => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp(chemin);
    for (const nom of ["Menu principal", "Menu du téléphone"]) {
      const liens = within(screen.getByRole("navigation", { name: nom })).getAllByRole("link");
      expect(liens.filter((l) => l.getAttribute("aria-current") === "page").map((l) => l.textContent)).toEqual([libelle]);
    }
    await screen.findByText(/Renouvelés le 1er novembre/);
  });

  it("le menu du téléphone propose les mêmes quatre entrées que l'ordinateur", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp("/");
    const noms = (nav: string) => within(screen.getByRole("navigation", { name: nav })).getAllByRole("link").map((l) => l.textContent);
    expect(noms("Menu du téléphone")).toEqual(noms("Menu principal"));
    expect(noms("Menu principal")).toEqual(["Créer", "Projets", "Bibliothèque", "Styles"]);
    await screen.findByText(/Renouvelés le 1er novembre/);
  });

  it("le bouton de thème passe du clair au sombre, et le choix est gardé", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES });
    const utilisateur = userEvent.setup();
    rendreApp("/");
    await utilisateur.click(screen.getByRole("button", { name: "Activer le mode sombre" }));
    expect(document.documentElement.dataset.theme).toBe("sombre");
    expect(localStorage.getItem("theme-atelier")).toBe("sombre");
    await utilisateur.click(screen.getByRole("button", { name: "Activer le mode clair" }));
    expect(document.documentElement.dataset.theme).toBe("clair");
    await screen.findByText(/Renouvelés le 1er novembre/);
  });

  it("la loupe ouvre le champ de recherche, qui garde son nom accessible", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES });
    const utilisateur = userEvent.setup();
    rendreApp("/");
    const loupe = screen.getByRole("button", { name: "Rechercher" });
    expect(loupe).toHaveAttribute("aria-expanded", "false");
    await utilisateur.click(loupe);
    expect(loupe).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("combobox", { name: "Rechercher partout" })).toBeInTheDocument();
    await screen.findByText(/Renouvelés le 1er novembre/);
  });
});
