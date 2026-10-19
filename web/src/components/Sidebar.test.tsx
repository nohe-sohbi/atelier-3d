import { screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MENU_REMPLI, MENU_VIDE, NOTIFICATIONS, NOTIFICATIONS_VIDES, mockApi, reponseErreur } from "../test/api-mock";
import { rendreApp } from "../test/rendre";

afterEach(() => vi.unstubAllGlobals());

describe("Sidebar", () => {
  it("lit /api/menu et affiche les badges non nuls, les collections et les crédits", async () => {
    const { appels } = mockApi({ "GET /api/menu": MENU_REMPLI, "GET /api/notifications": NOTIFICATIONS });
    rendreApp("/");
    const menu = within(screen.getByRole("navigation", { name: "Menu principal" }));

    expect(await menu.findByText("3")).toBeInTheDocument();
    expect(within(menu.getByRole("link", { name: /Lots/ })).getByText("3")).toBeInTheDocument();
    expect(within(menu.getByRole("link", { name: /Générateurs/ })).getByText("1")).toBeInTheDocument();
    expect(within(menu.getByRole("link", { name: /Bibliothèque/ })).getByText("2")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: /Collection test/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Collection test/ })).toHaveTextContent("2");
    expect(screen.getByText("Renouvelés le 1er novembre")).toBeInTheDocument();
    const jauge = screen.getByRole("progressbar", { name: "Crédits Meshy utilisés" });
    expect(jauge).toHaveAttribute("aria-valuenow", "60");
    expect(jauge).toHaveAttribute("aria-valuemax", "1000");
    // Le solde vient du simulateur : l'écran le dit.
    expect(screen.getByText("· simulé")).toBeInTheDocument();

    expect(appels.some((a) => a.chemin === "/api/menu")).toBe(true);
  });

  it("sans badge ni collection : aucun badge, texte « Aucune collection épinglée »", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp("/");
    expect(await screen.findByText("Aucune collection épinglée")).toBeInTheDocument();
    const menu = within(screen.getByRole("navigation", { name: "Menu principal" }));
    expect(menu.queryByText("0")).not.toBeInTheDocument();
    expect(menu.getByRole("link", { name: "Lots" })).toHaveTextContent(/^Lots$/);
  });

  it("signale une erreur de chargement sans inventer de données", async () => {
    mockApi({ "GET /api/menu": () => reponseErreur(500, "Panne"), "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp("/");
    expect(await screen.findByText(/Menu non chargé : Panne/)).toBeInTheDocument();
    expect(screen.getByText("Aucune collection épinglée")).toBeInTheDocument();
  });

  it("dit « Solde Meshy non lu » quand l'API renvoie credits: null, sans chiffre inventé", async () => {
    mockApi({ "GET /api/menu": { ...MENU_VIDE, credits: null }, "GET /api/notifications": NOTIFICATIONS_VIDES });
    rendreApp("/");
    expect(await screen.findByText("Solde Meshy non lu (voir Réglages)")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Crédits Meshy utilisés" })).toHaveAttribute("aria-valuenow", "0");
  });
});
