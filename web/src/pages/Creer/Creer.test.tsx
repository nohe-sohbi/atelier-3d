import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  LOTS,
  LOTS_VIDES,
  LOT_CREE,
  MENU_VIDE,
  NOTIFICATIONS_VIDES,
  OBJETS_VIDES,
  STYLES,
  mockApi,
  reponseErreur,
} from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";

const BASE = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS_VIDES,
  "GET /api/styles": STYLES,
  "GET /api/lots": LOTS_VIDES,
};

afterEach(() => vi.unstubAllGlobals());

describe("Créer", () => {
  it("propose le formulaire : une phrase, un style prêt déjà choisi, et un bouton qui attend la phrase", async () => {
    mockApi(BASE);
    rendreApp("/");
    expect(screen.getByRole("heading", { level: 1, name: "Que veux-tu créer ?" })).toBeInTheDocument();
    const styles = within(await screen.findByRole("radiogroup", { name: "Style" }));
    const prets = STYLES.styles.filter((s) => s.etat === "valide");
    expect(styles.getAllByRole("radio")).toHaveLength(prets.length);
    expect(styles.getByRole("radio", { name: new RegExp(prets[0]!.nom) })).toBeChecked();
    expect(screen.getByRole("button", { name: /Proposer les objets/ })).toBeDisabled();
  });

  it("crée le projet avec la phrase et le style, demande la liste d'objets, puis ouvre l'écran Objets", async () => {
    const { appels } = mockApi({
      ...BASE,
      "POST /api/lots": LOT_CREE,
      [`POST /api/lots/${LOT_CREE.id}/proposition`]: { tache_id: 7 },
      [`GET /api/lots/${LOT_CREE.id}`]: LOT_CREE,
      [`GET /api/lots/${LOT_CREE.id}/objets`]: OBJETS_VIDES,
    });
    const utilisateur = userEvent.setup();
    rendreApp("/");
    await screen.findByRole("radiogroup", { name: "Style" });
    await utilisateur.type(screen.getByLabelText("Ta demande"), "  Des tonneaux et des caisses  ");
    await utilisateur.click(screen.getByRole("button", { name: /Proposer les objets/ }));

    expect(await screen.findByRole("heading", { level: 2, name: "Ta demande" })).toBeInTheDocument();
    const creation = appels.find((a) => a.methode === "POST" && a.chemin === "/api/lots");
    expect(creation?.corps).toEqual({ besoin: "Des tonneaux et des caisses", style_id: STYLES.styles.find((s) => s.etat === "valide")!.id });
    expect(appels.filter((a) => a.methode === "POST" && a.chemin === `/api/lots/${LOT_CREE.id}/proposition`)).toHaveLength(1);
  });

  it("dit l'erreur du serveur et reste sur le formulaire", async () => {
    mockApi({ ...BASE, "POST /api/lots": () => reponseErreur(500, "Disque plein") });
    const utilisateur = userEvent.setup();
    rendreApp("/");
    await screen.findByRole("radiogroup", { name: "Style" });
    await utilisateur.type(screen.getByLabelText("Ta demande"), "Une lanterne");
    await utilisateur.click(screen.getByRole("button", { name: /Proposer les objets/ }));
    expect(await screen.findByText(/Disque plein/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Que veux-tu créer ?" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /Proposer les objets/ })).toBeEnabled());
  });

  it("sans style prêt : l'écran le dit et renvoie vers Styles, sans rien inventer", async () => {
    mockApi({ ...BASE, "GET /api/styles": { ...STYLES, styles: STYLES.styles.map((s) => ({ ...s, etat: "brouillon" as const })) } });
    rendreApp("/");
    expect(await screen.findByText(/Aucun style prêt/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Crée ou valide un style/ })).toHaveAttribute("href", "/styles");
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Proposer les objets/ })).toBeDisabled();
  });

  it("met « À toi de jouer » avant le formulaire : seuls les projets qui attendent une action", async () => {
    mockApi({ ...BASE, "GET /api/lots": LOTS });
    rendreApp("/");
    const attendent = LOTS.lots.filter((l) => l.ton === "warn" || l.ton === "accent");
    if (attendent.length === 0) {
      expect(screen.queryByRole("heading", { name: "À toi de jouer" })).not.toBeInTheDocument();
      return;
    }
    const section = within(await screen.findByRole("region", { name: "À toi de jouer" }));
    expect(section.getAllByRole("link")).toHaveLength(attendent.length);
    expect(section.getAllByRole("link")[0]).toHaveAttribute("href", attendent[0]!.lien);
    const titres = screen.getAllByRole("heading").map((h) => h.textContent);
    expect(titres.indexOf("À toi de jouer")).toBeLessThan(titres.indexOf("Que veux-tu créer ?"));
  });
});
