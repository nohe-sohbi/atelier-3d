import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { StyleDetail, StyleEnvoye } from "../../api/types";
import { MENU_VIDE, NOTIFICATIONS_VIDES, STYLES, STYLE_DETAIL, mockApi, reponseErreur } from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";
import { lireDimensions, slug } from "./commun";

afterEach(() => vi.unstubAllGlobals());

const BASE = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS_VIDES,
  "GET /api/styles": STYLES,
  [`GET /api/styles/${STYLE_DETAIL.id}`]: STYLE_DETAIL,
};

/** Un style créé par les tests, dérivé du contrat réel (même forme), avec une planche de 6 images simulées. */
function styleCree(planche: StyleDetail["planche"] = []): StyleDetail {
  return {
    ...STYLE_DETAIL,
    id: 2,
    code: "medieval-stylise-v0",
    nom: "Médiéval stylisé",
    etat: "brouillon",
    valide_le: null,
    racine_id: 2,
    versions: [{ id: 2, code: "medieval-stylise-v0", version: 0, note: "Version initiale.", date: STYLE_DETAIL.cree_le, etat: "brouillon" }],
    planche,
    credits_planche: planche.reduce((n, i) => n + i.credits, 0),
  };
}
const IMAGES = ["caisse", "amphore", "lampe", "banc", "casque", "table"].map((objet, i) => ({
  id: 10 + i,
  fichier: `${objet}.png`,
  objet,
  gardee: false,
  simule: true,
  credits: 3,
  cree_le: STYLE_DETAIL.cree_le,
  url: `/api/fichiers/styles/medieval-stylise-v0/board/${objet}.png`,
}));

describe("Styles", () => {
  it("liste les styles et ouvre le premier, avec palette, budgets libellés et versions depuis l'API", async () => {
    mockApi(BASE);
    rendreApp("/styles");
    expect(screen.getByRole("heading", { level: 1, name: "Styles" })).toBeInTheDocument();
    const carte = await screen.findByRole("button", { name: /Rome antique stylisée/ });
    expect(carte).toHaveAttribute("aria-pressed", "true");
    expect(within(carte).getByText("Actif")).toBeInTheDocument();
    expect(within(carte).getByText("rome-stylise-v0")).toBeInTheDocument();
    expect(within(carte).getByText("Aucun asset")).toBeInTheDocument();

    expect(await screen.findByRole("heading", { level: 2, name: STYLE_DETAIL.nom })).toBeInTheDocument();
    expect(screen.getByText("Petit objet")).toBeInTheDocument();
    expect(screen.getByText(/2[\s\u202f\u00a0]000 tris/)).toBeInTheDocument();
    expect(screen.getByText(/512 px\/m/)).toBeInTheDocument();
    expect(screen.getByText("Aucune image validée pour ce style")).toBeInTheDocument();
    expect(screen.getByText("v0")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dupliquer en v1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Modifier" })).toBeEnabled();
    // Palette : une nuance par couleur du style, jamais inventée
    expect(screen.getAllByText(/^#[0-9A-F]{6}$/)).toHaveLength(STYLE_DETAIL.palette.length);
  });

  it("sans style : état vide et bouton Nouveau style", async () => {
    mockApi({ ...BASE, "GET /api/styles": { styles: [] } });
    rendreApp("/styles");
    expect(await screen.findByText("Aucun style pour l'instant")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Nouveau style" }).length).toBeGreaterThan(0);
  });

  it("erreur d'API : message et Réessayer, rien d'inventé", async () => {
    mockApi({ ...BASE, "GET /api/styles": () => reponseErreur(500, "Panne") });
    rendreApp("/styles");
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });

  it("Modifier est désactivé quand un lot utilise la version", async () => {
    mockApi({ ...BASE, [`GET /api/styles/${STYLE_DETAIL.id}`]: { ...STYLE_DETAIL, peut_modifier: false, lots: [{ id: 1, nom: "Lot A" }] } });
    rendreApp("/styles");
    expect(await screen.findByRole("button", { name: "Modifier" })).toBeDisabled();
    expect(screen.getByText(/utilisé par 1 lot/)).toBeInTheDocument();
  });

  it("Nouveau style : code depuis le nom, palette reprise du style de référence, création, planche simulée, garder, valider", async () => {
    const appels: Array<{ cle: string; corps: unknown }> = [];
    let cree = styleCree();
    const { appels: journal } = mockApi({
      ...BASE,
      "POST /api/styles": (init: RequestInit | undefined) => {
        appels.push({ cle: "POST /api/styles", corps: JSON.parse(String(init?.body)) });
        return cree;
      },
      "POST /api/styles/2/planche": () => {
        cree = styleCree(IMAGES);
        return { tache_id: 7, credits_estimes: 18 };
      },
      "GET /api/taches/7": { id: 7, type: "planche_style", file: "meshy", etat: "terminee", erreur: null, tentatives: 1, max_tentatives: 4, resultat: {} },
      "GET /api/styles/2": () => cree,
      "PUT /api/styles/2/planche/10": () => {
        cree = { ...cree, planche: cree.planche.map((i) => (i.id === 10 ? { ...i, gardee: true } : i)) };
        return cree;
      },
      "POST /api/styles/2/valider": () => ({ ...cree, etat: "valide" }),
    });
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await screen.findByRole("button", { name: /Rome antique stylisée/ });
    await utilisateur.click(screen.getByRole("button", { name: "Nouveau style" }));
    const fenetre = screen.getByRole("dialog", { name: "Nouveau style" });
    expect(within(fenetre).getByRole("listitem", { current: "step" })).toHaveTextContent("Définir");

    await utilisateur.type(within(fenetre).getByLabelText("Nom"), "Médiéval stylisé");
    expect(within(fenetre).getByLabelText("Code")).toHaveValue("medieval-stylise-v0");
    // La palette vient du style de référence (10 couleurs), pas d'une liste inventée
    expect(within(fenetre).getAllByLabelText(/^Nom de la couleur/)).toHaveLength(STYLE_DETAIL.palette.length);
    expect(within(fenetre).getByLabelText("Budgets et échelle")).toHaveValue(String(STYLE_DETAIL.id));
    await utilisateur.type(within(fenetre).getByLabelText("Description"), "Formes simples.");

    await utilisateur.click(within(fenetre).getByRole("button", { name: /Générer la première planche · 6 images, 18 crédits/ }));
    await waitFor(() => expect(appels).toHaveLength(1));
    const corps = appels[0]!.corps as StyleEnvoye;
    expect(corps.nom).toBe("Médiéval stylisé");
    expect(corps.code).toBeUndefined();
    expect(corps.budgets_depuis).toBe(STYLE_DETAIL.id);
    expect(Object.keys(corps.palette)).toHaveLength(STYLE_DETAIL.palette.length);
    expect(corps.description).toBe("Formes simples.");

    // Étape 2 : 6 tuiles simulées, « 0 image gardée sur 6 », Valider désactivé
    const tuiles = await within(fenetre).findAllByRole("listitem", { name: "" });
    expect(tuiles.length).toBeGreaterThanOrEqual(6);
    expect(within(fenetre).getAllByText("simulé")).toHaveLength(6);
    expect(within(fenetre).getByText("0 image gardée sur 6")).toBeInTheDocument();
    expect(within(fenetre).getByText(/18 crédits dépensés/)).toBeInTheDocument();
    expect(within(fenetre).getByRole("button", { name: "Valider le style" })).toBeDisabled();
    expect(journal.some((a) => a.chemin === "/api/taches/7")).toBe(true);

    await utilisateur.click(within(fenetre).getAllByRole("button", { name: "Garder" })[0]!);
    expect(await within(fenetre).findByRole("button", { name: "Gardée" })).toHaveAttribute("aria-pressed", "true");
    expect(within(fenetre).getByText("1 image gardée sur 6")).toBeInTheDocument();
    await utilisateur.click(within(fenetre).getByRole("button", { name: "Valider le style" }));
    await waitFor(() => expect(journal.some((a) => a.methode === "POST" && a.chemin === "/api/styles/2/valider")).toBe(true));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("Échap ferme la fenêtre et rend le focus au bouton Nouveau style", async () => {
    mockApi(BASE);
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await screen.findByRole("button", { name: /Rome antique stylisée/ });
    const bouton = screen.getByRole("button", { name: "Nouveau style" });
    await utilisateur.click(bouton);
    expect(screen.getByRole("dialog", { name: "Nouveau style" })).toBeInTheDocument();
    await utilisateur.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(bouton).toHaveFocus();
  });

  it("Dupliquer en v1 appelle /versions puis ouvre la nouvelle version", async () => {
    const v1: StyleDetail = { ...STYLE_DETAIL, id: 9, code: "rome-stylise-v1", version: 1, note_version: "Version 1" };
    const { appels } = mockApi({
      ...BASE,
      "POST /api/styles/1/versions": v1,
      "GET /api/styles": { styles: [...STYLES.styles, { ...STYLES.styles[0]!, id: 9, code: "rome-stylise-v1", version: 1 }] },
      "GET /api/styles/9": v1,
    });
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await screen.findByRole("heading", { level: 2, name: STYLE_DETAIL.nom });
    await utilisateur.click(screen.getByRole("button", { name: "Dupliquer en v1" }));
    await waitFor(() => expect(appels.some((a) => a.methode === "POST" && a.chemin === "/api/styles/1/versions")).toBe(true));
    expect(await screen.findByText(/Version rome-stylise-v1 créée/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /rome-stylise-v1/ })).toHaveAttribute("aria-pressed", "true"));
  });
});

describe("outils du formulaire", () => {
  it("slug et lecture des dimensions", () => {
    expect(slug("Médiéval stylisé !")).toBe("medieval-stylise");
    expect(lireDimensions("caisse 0.6 0.4 0.4\nlampe 0,12 0,08 0,06\nincomplet 1")).toEqual({ caisse: [0.6, 0.4, 0.4], lampe: [0.12, 0.08, 0.06] });
  });
});
