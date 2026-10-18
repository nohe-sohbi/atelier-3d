import { screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MENU_REMPLI, MENU_VIDE, NOTIFICATIONS, mockApi, reponseErreur } from "../test/api-mock";
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
    // Badge à 0 : rien d'affiché
    expect(within(menu.getByRole("link", { name: /Bibliothèque/ })).queryByText("0")).not.toBeInTheDocument();

    expect(screen.getByRole("link", { name: /Collection test/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Collection test/ })).toHaveTextContent("8");
    expect(screen.getByText("Renouvelés le 1er novembre")).toBeInTheDocument();
    const jauge = screen.getByRole("progressbar", { name: "Crédits Meshy utilisés" });
    expect(jauge).toHaveAttribute("aria-valuenow", "426");
    expect(jauge).toHaveAttribute("aria-valuemax", "1000");

    expect(appels.some((a) => a.chemin === "/api/menu")).toBe(true);
  });

  it("sans badge ni collection : aucun badge, texte « Aucune collection épinglée »", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": [] });
    rendreApp("/");
    expect(await screen.findByText("Aucune collection épinglée")).toBeInTheDocument();
    const menu = within(screen.getByRole("navigation", { name: "Menu principal" }));
    expect(menu.queryByText("0")).not.toBeInTheDocument();
    expect(menu.getByRole("link", { name: "Lots" })).toHaveTextContent(/^Lots$/);
  });

  it("signale une erreur de chargement sans inventer de données", async () => {
    mockApi({ "GET /api/menu": () => reponseErreur(500, "Panne"), "GET /api/notifications": [] });
    rendreApp("/");
    expect(await screen.findByText(/Menu non chargé : Panne/)).toBeInTheDocument();
    expect(screen.getByText("Aucune collection épinglée")).toBeInTheDocument();
  });
});
