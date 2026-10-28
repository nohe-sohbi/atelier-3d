import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MENU_VIDE, NOTIFICATIONS, NOTIFICATIONS_VIDES, RECHERCHE_VIDE, mockApi } from "../test/api-mock";

const NON_LUE = NOTIFICATIONS.notifications.find((n) => !n.lu)!;
import { rendreApp } from "../test/rendre";

afterEach(() => vi.unstubAllGlobals());

describe("Recherche globale", () => {
  it("interroge /api/recherche?q= et propose les résultats dans une liste accessible", async () => {
    const { appels } = mockApi({
      "GET /api/menu": MENU_VIDE,
      "GET /api/notifications": NOTIFICATIONS_VIDES,
      "GET /api/recherche": (_init: RequestInit | undefined, url: URL) => ({
        resultats: url.searchParams.get("q") === "scut" ? [{ type: "asset", id: "ROM_PROP_Scutum_A", titre: "Scutum A", lien: "/assets/ROM_PROP_Scutum_A" }] : [],
      }),
    });
    const utilisateur = userEvent.setup();
    rendreApp("/");

    const champ = screen.getByRole("combobox", { name: "Rechercher partout" });
    await utilisateur.type(champ, "scut");

    const liste = await screen.findByRole("listbox", { name: "Résultats de la recherche" });
    expect(within(liste).getByRole("option", { name: /Scutum A/ })).toBeInTheDocument();
    expect(champ).toHaveAttribute("aria-expanded", "true");
    expect(appels.some((a) => a.chemin === "/api/recherche?q=scut")).toBe(true);

    await utilisateur.keyboard("{ArrowDown}{Enter}");
    expect(screen.getByRole("heading", { level: 1, name: "Fiche asset" })).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("dit « Aucun résultat » quand la liste est vide", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES, "GET /api/recherche": RECHERCHE_VIDE });
    const utilisateur = userEvent.setup();
    rendreApp("/");
    await utilisateur.type(screen.getByRole("combobox", { name: "Rechercher partout" }), "zzz");
    expect(await screen.findByText("Aucun résultat")).toBeInTheDocument();
  });
});

describe("Notifications", () => {
  it("compte les non lues, ouvre le panneau et marque une notification lue", async () => {
    // Après le POST, l'API relue dit que tout est lu : le mock suit l'état, comme la vraie API.
    let marquee = false;
    const { appels } = mockApi({
      "GET /api/menu": MENU_VIDE,
      "GET /api/notifications": () =>
        marquee ? { notifications: NOTIFICATIONS.notifications.map((n) => ({ ...n, lu: true })), non_lues: 0 } : NOTIFICATIONS,
      [`POST /api/notifications/${NON_LUE.id}/lu`]: () => {
        marquee = true;
        return { ok: true, id: NON_LUE.id };
      },
    });
    const utilisateur = userEvent.setup();
    rendreApp("/");

    const cloche = await screen.findByRole("button", { name: "Notifications : 1 nouvelle" });
    await utilisateur.click(cloche);
    const panneau = screen.getByRole("region", { name: "Notifications" });
    expect(within(panneau).getByText("1 nouvelle")).toBeInTheDocument();
    expect(within(panneau).getByText("À valider · Lot test")).toBeInTheDocument();

    await utilisateur.click(within(panneau).getByRole("button", { name: /À valider · Lot test/ }));
    await waitFor(() => expect(appels.some((a) => a.methode === "POST" && a.chemin === `/api/notifications/${NON_LUE.id}/lu`)).toBe(true));
    // Le lien de la notification est suivi
    expect(await screen.findByText("La validation arrive à l'étape 8 du plan")).toBeInTheDocument(); // l'écran Revue du lot
    expect(screen.getByRole("button", { name: "Notifications : aucune nouvelle" })).toBeInTheDocument();
  });

  it("« Tout marquer lu » appelle /api/notifications/tout-lu ; Échap ferme le panneau", async () => {
    const { appels } = mockApi({
      "GET /api/menu": MENU_VIDE,
      "GET /api/notifications": NOTIFICATIONS,
      "POST /api/notifications/tout-lu": { ok: true, marquees: 1 },
    });
    const utilisateur = userEvent.setup();
    rendreApp("/");
    const cloche = await screen.findByRole("button", { name: "Notifications : 1 nouvelle" });
    await utilisateur.click(cloche);
    await utilisateur.click(screen.getByRole("button", { name: "Tout marquer lu" }));
    await waitFor(() => expect(appels.some((a) => a.methode === "POST" && a.chemin === "/api/notifications/tout-lu")).toBe(true));

    await utilisateur.keyboard("{Escape}");
    expect(screen.queryByRole("region", { name: "Notifications" })).not.toBeInTheDocument();
    expect(cloche).toHaveFocus();
  });

  it("panneau vide sans notification", async () => {
    mockApi({ "GET /api/menu": MENU_VIDE, "GET /api/notifications": NOTIFICATIONS_VIDES });
    const utilisateur = userEvent.setup();
    rendreApp("/");
    await utilisateur.click(await screen.findByRole("button", { name: "Notifications : aucune nouvelle" }));
    expect(screen.getByText("Aucune notification")).toBeInTheDocument();
  });
});
