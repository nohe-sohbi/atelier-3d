import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { StyleDetail, StyleEnvoye, StyleModifie, Tache } from "../../api/types";
import {
  ESTIMATION_PLANCHE,
  MENU_VIDE,
  NOTIFICATIONS_VIDES,
  PLANCHE_LANCEE,
  STYLES,
  STYLE_CREE,
  STYLE_DETAIL,
  STYLE_PLANCHE,
  TACHE_ECHOUEE,
  TACHE_TERMINEE,
  mockApi,
  reponseErreur,
} from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";
import { lireDimensions, slug } from "./commun";

afterEach(() => vi.unstubAllGlobals());

const BASE = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS_VIDES,
  "GET /api/styles": STYLES,
  [`GET /api/styles/${STYLE_DETAIL.id}`]: STYLE_DETAIL,
  "GET /api/styles/estimation-planche": ESTIMATION_PLANCHE,
};

/* Un style créé puis sa planche simulée, la tâche terminée et une tâche échouée : tout vient du contrat
   (vraie API, vrai passage du worker). */
const SID = STYLE_PLANCHE.id;
const IMAGES = STYLE_PLANCHE.planche;
/** La page Styles avec, en plus du pilote, le style brouillon et sa planche. */
const AVEC_PLANCHE = {
  ...BASE,
  "GET /api/styles": { styles: [...STYLES.styles, STYLE_PLANCHE] },
  [`GET /api/styles/${SID}`]: STYLE_PLANCHE,
};

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
    let cree: StyleDetail = STYLE_CREE;
    const premiere = IMAGES[0]!;
    const { appels: journal } = mockApi({
      ...BASE,
      "POST /api/styles": (init: RequestInit | undefined) => {
        appels.push({ cle: "POST /api/styles", corps: JSON.parse(String(init?.body)) });
        return cree;
      },
      [`POST /api/styles/${SID}/planche`]: () => {
        cree = STYLE_PLANCHE;
        return PLANCHE_LANCEE;
      },
      [`GET /api/taches/${PLANCHE_LANCEE.tache_id}`]: TACHE_TERMINEE,
      [`GET /api/styles/${SID}`]: () => cree,
      [`PUT /api/styles/${SID}/planche/${premiere.id}`]: () => {
        cree = { ...cree, planche: cree.planche.map((i) => (i.id === premiere.id ? { ...i, gardee: true } : i)) };
        return cree;
      },
      [`POST /api/styles/${SID}/valider`]: () => ({ ...cree, etat: "valide" }),
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

    // Le tarif vient de l'adaptateur (estimation), le nombre d'images du style de référence.
    await utilisateur.click(within(fenetre).getByRole("button", { name: "Générer la première planche · 6 images, 18 crédits · simulé" }));
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
    expect(journal.some((a) => a.chemin === `/api/taches/${PLANCHE_LANCEE.tache_id}`)).toBe(true);
    expect(within(fenetre).getByText(/« Refaire » relance une image à 3 crédits/)).toBeInTheDocument();

    await utilisateur.click(within(fenetre).getAllByRole("button", { name: "Garder" })[0]!);
    expect(await within(fenetre).findByRole("button", { name: "Gardée" })).toHaveAttribute("aria-pressed", "true");
    expect(within(fenetre).getByText("1 image gardée sur 6")).toBeInTheDocument();
    await utilisateur.click(within(fenetre).getByRole("button", { name: "Valider le style" }));
    await waitFor(() => expect(journal.some((a) => a.methode === "POST" && a.chemin === `/api/styles/${SID}/valider`)).toBe(true));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("une planche qui échoue : l'erreur de la tâche est affichée, telle que l'API la donne", async () => {
    mockApi({
      ...AVEC_PLANCHE,
      [`GET /api/styles/${SID}`]: { ...STYLE_PLANCHE, planche: [] },
      [`POST /api/styles/${SID}/planche`]: { ...PLANCHE_LANCEE, tache_id: TACHE_ECHOUEE.id },
      [`GET /api/taches/${TACHE_ECHOUEE.id}`]: TACHE_ECHOUEE,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/styles?style=${STYLE_PLANCHE.code}`);
    await utilisateur.click(await screen.findByRole("button", { name: /^Générer la planche · 6 images, 18 crédits/ }));
    const fenetre = screen.getByRole("dialog");
    await utilisateur.click(within(fenetre).getByRole("button", { name: /^Générer la planche/ }));
    expect(await within(fenetre).findByRole("alert")).toHaveTextContent(TACHE_ECHOUEE.erreur!);
    expect(within(fenetre).getByRole("button", { name: /^Générer la planche/ })).toBeEnabled();
  });

  it("Refaire relance une seule image puis relit le style", async () => {
    const { appels } = mockApi({
      ...AVEC_PLANCHE,
      [`POST /api/styles/${SID}/planche/${IMAGES[1]!.id}/refaire`]: PLANCHE_LANCEE,
      [`GET /api/taches/${PLANCHE_LANCEE.tache_id}`]: TACHE_TERMINEE,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/styles?style=${STYLE_PLANCHE.code}`);
    await utilisateur.click(await screen.findByRole("button", { name: "Compléter la planche et valider" }));
    const fenetre = screen.getByRole("dialog");
    expect(within(fenetre).getAllByRole("button", { name: "Refaire" })).toHaveLength(IMAGES.length);
    const lectures = () => appels.filter((a) => a.chemin === `/api/styles/${SID}`).length;
    const avant = lectures();
    await utilisateur.click(within(fenetre).getAllByRole("button", { name: "Refaire" })[1]!);
    await waitFor(() => expect(lectures()).toBeGreaterThan(avant));
    expect(appels.filter((a) => a.methode === "POST").map((a) => a.chemin)).toEqual([`/api/styles/${SID}/planche/${IMAGES[1]!.id}/refaire`]);
  });

  it("sans worker : la tâche en attente le dit au lieu d'attendre en silence ; fermer arrête de l'interroger", async () => {
    const enAttente: Tache = { ...TACHE_TERMINEE, etat: "en_attente", resultat: null };
    const { appels } = mockApi({
      ...AVEC_PLANCHE,
      [`GET /api/styles/${SID}`]: { ...STYLE_PLANCHE, planche: [] },
      [`POST /api/styles/${SID}/planche`]: PLANCHE_LANCEE,
      [`GET /api/taches/${PLANCHE_LANCEE.tache_id}`]: enAttente,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/styles?style=${STYLE_PLANCHE.code}`);
    await utilisateur.click(await screen.findByRole("button", { name: /^Générer la planche/ }));
    const fenetre = screen.getByRole("dialog");
    await utilisateur.click(within(fenetre).getByRole("button", { name: /^Générer la planche/ }));
    expect(await within(fenetre).findByText(/le worker la prendra dès qu'il tourne/, {}, { timeout: 5000 })).toBeInTheDocument();
    await utilisateur.click(within(fenetre).getByRole("button", { name: "Plus tard" }));
    const lectures = () => appels.filter((a) => a.chemin === `/api/taches/${PLANCHE_LANCEE.tache_id}`).length;
    const aLaFermeture = lectures();
    await new Promise((r) => setTimeout(r, 1500));
    expect(lectures()).toBe(aLaFermeture);
  }, 15000);

  it("Modifier : renommer une couleur et changer un budget envoient la palette dans l'ordre et les budgets", async () => {
    const corps: StyleModifie[] = [];
    mockApi({
      ...BASE,
      [`PUT /api/styles/${STYLE_DETAIL.id}`]: (init: RequestInit | undefined) => {
        corps.push(JSON.parse(String(init?.body)) as StyleModifie);
        return { ...STYLE_DETAIL, palette: [{ ...STYLE_DETAIL.palette[0]!, nom: "terre_rouge" }, ...STYLE_DETAIL.palette.slice(1)] };
      },
    });
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await utilisateur.click(await screen.findByRole("button", { name: "Modifier" }));
    const fenetre = screen.getByRole("dialog", { name: `Modifier · ${STYLE_DETAIL.nom}` });
    const nomCouleur = within(fenetre).getByLabelText("Nom de la couleur 1");
    await utilisateur.clear(nomCouleur);
    await utilisateur.type(nomCouleur, "Terre rouge");
    const budget = within(fenetre).getByLabelText("Petit objet (tris)");
    await utilisateur.clear(budget);
    await utilisateur.type(budget, "2500");
    await utilisateur.click(within(fenetre).getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(corps).toHaveLength(1));
    expect(Object.keys(corps[0]!.palette!)).toEqual(["Terre rouge", ...STYLE_DETAIL.palette.slice(1).map((c) => c.nom)]);
    expect(corps[0]!.budgets_tris!.petit_prop).toBe(2500);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(await screen.findByText("terre rouge")).toBeInTheDocument();
  });

  it("un ?style= inconnu le dit, puis ouvre le premier style", async () => {
    mockApi(BASE);
    rendreApp("/styles?style=inconnu-v0");
    expect(await screen.findByText(/Aucun style ne porte le code « inconnu-v0 »/)).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: STYLE_DETAIL.nom })).toBeInTheDocument();
  });

  it("saisie à la main : budgets, texels et dimensions envoyés ; une image par type saisi", async () => {
    const corps: StyleEnvoye[] = [];
    mockApi({
      ...BASE,
      "POST /api/styles": (init: RequestInit | undefined) => {
        corps.push(JSON.parse(String(init?.body)) as StyleEnvoye);
        return reponseErreur(409, "un style nommé « Sci-fi » existe déjà en v0 (sci-fi-v0) : choisis un autre nom");
      },
    });
    const utilisateur = userEvent.setup();
    rendreApp("/styles");
    await screen.findByRole("button", { name: /Rome antique stylisée/ });
    await utilisateur.click(screen.getByRole("button", { name: "Nouveau style" }));
    const fenetre = screen.getByRole("dialog", { name: "Nouveau style" });
    await utilisateur.type(within(fenetre).getByLabelText("Nom"), "Sci-fi");
    await utilisateur.selectOptions(within(fenetre).getByLabelText("Budgets et échelle"), "vide");
    expect(within(fenetre).getByLabelText("Densité de texels (px/m)")).toHaveValue(null); // rien d'inventé
    for (const [libelle, valeur] of [["Petit objet (tris)", "4000"], ["Objet moyen (tris)", "12000"], ["Grand objet (tris)", "30000"], ["Module d'architecture (tris)", "16000"], ["Densité de texels (px/m)", "1024"]] as const) {
      await utilisateur.type(within(fenetre).getByLabelText(libelle), valeur);
    }
    expect(within(fenetre).getByRole("button", { name: /^Générer la première planche/ })).toBeDisabled(); // aucun type : aucune image
    await utilisateur.type(within(fenetre).getByLabelText("Dimensions réelles par type"), "caisse 0.6 0.4 0.4{Enter}lampe 0.1 0.1 0.3");
    await utilisateur.click(within(fenetre).getByRole("button", { name: "Générer la première planche · 2 images, 6 crédits · simulé" }));
    await waitFor(() => expect(corps).toHaveLength(1));
    expect(corps[0]).toMatchObject({
      nom: "Sci-fi",
      budgets_depuis: null,
      budgets: { petit_prop: 4000, prop_moyen: 12000, grand_prop: 30000, module_archi: 16000 },
      texel_density: 1024,
      dimensions_m: { caisse: [0.6, 0.4, 0.4], lampe: [0.1, 0.1, 0.3] },
    });
    expect(await within(fenetre).findByRole("alert")).toHaveTextContent("existe déjà en v0");
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
