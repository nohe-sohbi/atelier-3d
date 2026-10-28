import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Generation, Reglages, TacheVue } from "../../api/types";
import {
  GENERATION,
  JOURNAL,
  LOT_ENTETE_PROPOSE,
  MENU_VIDE,
  NOTIFICATIONS_VIDES,
  REFERENCES,
  REGLAGES,
  TACHES_RECENTES,
  mockApi,
} from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const LID = GENERATION.lot_id;
const BASE = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS_VIDES,
  [`GET /api/lots/${LID}`]: { ...LOT_ENTETE_PROPOSE, id: LID },
};
const PROPOSITION = GENERATION.taches.find((t) => t.type === "proposer_liste")!;

/** Le même lot, plus avancé : dérivé du contrat (même forme), comme le serait la réponse de l'API à l'étape 5. */
function avancee(): Generation {
  const [a, b, ...reste] = GENERATION.objets;
  const echec: TacheVue = { ...PROPOSITION, id: 99, etat: "echouee", tentatives: 4, erreur: "RuntimeError: Meshy injoignable", peut_relancer: true };
  return {
    ...GENERATION,
    tuiles: { ...GENERATION.tuiles, prets_revue: 1, en_cours: 1, relances: 3, credits_utilises: 60, credits_simules: true },
    objets: [
      { ...a!, statut: "Finition en cours", ton: "run", pct: 25, etapes: a!.etapes.map((p, i) => ({ ...p, etat: i === 0 ? "fait" : i === 1 ? "en_cours" : "a_faire" })) },
      { ...b!, statut: "Prêt pour la revue", ton: "good", pct: 100, etapes: b!.etapes.map((p) => ({ ...p, etat: "fait" })) },
      ...reste,
    ],
    taches: [echec, PROPOSITION],
  };
}

describe("Génération", () => {
  it("objets IA lancés vers Meshy : tuiles réelles, worker arrêté, 1re étape en cours, tâches du lot et leur journal", async () => {
    const g: Generation = { ...GENERATION, taches: [PROPOSITION] };
    mockApi({ ...BASE, [`GET /api/lots/${LID}/generation`]: g, [`GET /api/taches/${PROPOSITION.id}/journal`]: JOURNAL });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/generation`);
    const tuiles = within(await screen.findByRole("list", { name: "Où en est la fabrication" }));
    expect(tuiles.getByText(`/ ${GENERATION.tuiles.fabriques}`)).toBeInTheDocument();
    expect(tuiles.getByText(new RegExp(`${GENERATION.tuiles.credits_prevus}.prévus`))).toBeInTheDocument();
    expect(screen.getByText(/Le worker ne tourne pas/)).toBeInTheDocument();
    expect(screen.queryByText(new RegExp(GENERATION.fabrication.raison_ia.slice(0, 40)))).not.toBeInTheDocument(); // ni mixte ni import
    expect(screen.getAllByText("Génération en cours")).toHaveLength(GENERATION.objets.length);
    const objets = within(screen.getByRole("list", { name: "Objets du lot" }));
    expect(objets.getAllByRole("listitem", { name: "" }).length).toBeGreaterThan(0);
    for (const o of GENERATION.objets) {
      const puces = within(screen.getByRole("list", { name: `Étapes de ${o.nom}` }));
      expect(puces.getAllByRole("listitem")[0]).toHaveTextContent("Génération : en cours");
      expect(puces.getAllByText(/: à faire/)).toHaveLength(3);
      // L'image choisie aux Références sert de vignette tant que l'objet n'est pas rendu.
      expect(screen.getByRole("img", { name: `Vignette de ${o.nom}` }).getAttribute("src")).toMatch(/^\/api\/fichiers\/references\/\d+$/);
    }
    expect(screen.getByRole("button", { name: "Ouvrir la revue · 0 prêt" })).toBeDisabled();

    expect(screen.getByText(PROPOSITION.libelle)).toBeInTheDocument();
    expect(screen.getByText("Terminée")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Relancer" })).not.toBeInTheDocument();
    await utilisateur.click(screen.getByRole("button", { name: `Journal : ${PROPOSITION.libelle}` }));
    const journal = within(await screen.findByRole("list", { name: `Journal de la tâche ${PROPOSITION.id}` }));
    expect(await journal.findByText(new RegExp(JOURNAL.evenements[0]!.titre))).toBeInTheDocument();
    expect(journal.getAllByRole("listitem")).toHaveLength(JOURNAL.evenements.length);
  });

  it("en cours : puces, prêts pour la revue, relances, crédits simulés ; Relancer une tâche en échec", async () => {
    let g = avancee();
    const { appels } = mockApi({
      ...BASE,
      [`GET /api/lots/${LID}/generation`]: () => g,
      "POST /api/taches/99/relancer": () => {
        g = { ...g, taches: g.taches.map((t) => (t.id === 99 ? { ...t, etat: "en_attente", erreur: null, peut_relancer: false, peut_annuler: true } : t)) };
        return {};
      },
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/generation`);
    const premier = GENERATION.objets[0]!;
    const puces = within(await screen.findByRole("list", { name: `Étapes de ${premier.nom}` }));
    expect(puces.getByText(/: fait/)).toBeInTheDocument();
    expect(puces.getByText(/: en cours/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ouvrir la revue · 1 prêt" })).toHaveAttribute("href", `/lots/${LID}/revue`);
    expect(screen.getByText(/utilisés · simulé/)).toBeInTheDocument();
    expect(screen.getByText("RuntimeError: Meshy injoignable")).toBeInTheDocument();
    await utilisateur.click(screen.getByRole("button", { name: "Relancer" }));
    await waitFor(() => expect(appels.some((a) => a.methode === "POST" && a.chemin === "/api/taches/99/relancer")).toBe(true));
    expect(await screen.findByRole("button", { name: /^Annuler : / })).toBeInTheDocument();
  });

  it("une tâche qui tourne : l'écran se relit toutes les 2 s", async () => {
    const enCours: Generation = { ...GENERATION, taches: [{ ...PROPOSITION, etat: "en_cours", progression: { pct: 40, texte: "Claude réfléchit" } }] };
    const { appels } = mockApi({ ...BASE, [`GET /api/lots/${LID}/generation`]: enCours });
    rendreApp(`/lots/${LID}/generation`);
    expect(await screen.findByText("Claude réfléchit")).toBeInTheDocument();
    const lectures = () => appels.filter((a) => a.chemin === `/api/lots/${LID}/generation`).length;
    const avant = lectures();
    await waitFor(() => expect(lectures()).toBeGreaterThan(avant), { timeout: 3500 });
  });
});

describe("Génération · en-tête du lot", () => {
  it("le worker fait avancer un objet : l'en-tête du lot se relit (étapes et ligne d'état à jour)", async () => {
    const tourne: Generation = { ...GENERATION, taches: [{ ...PROPOSITION, etat: "en_cours", progression: { pct: 40, texte: "Meshy simulé : objet 3D · 40 %" } }] };
    let lectures = 0;
    const { appels } = mockApi({
      ...BASE,
      [`GET /api/lots/${LID}/generation`]: () => {
        lectures += 1;
        const o = GENERATION.objets[0]!;
        return lectures < 2 ? tourne : { ...tourne, objets: [{ ...o, statut: "Prêt pour la revue", ton: "good", pct: 100 }, ...GENERATION.objets.slice(1)] };
      },
    });
    rendreApp(`/lots/${LID}/generation`);
    await screen.findByText("Meshy simulé : objet 3D · 40 %");
    const entetes = () => appels.filter((x) => x.chemin.startsWith(`/api/lots/${LID}?`) || x.chemin === `/api/lots/${LID}`).length;
    const avant = entetes();
    await waitFor(() => expect(entetes()).toBeGreaterThan(avant), { timeout: 3500 });
  });
});

describe("Génération · fabrication par code", () => {
  it("un échec : son motif, Refaire, ou Choisir une autre version (retour aux Références) ; un objet fini : vignette et planche", async () => {
    const [a, b] = GENERATION.objets;
    const essai = (id: number, etat: string, erreur: string | null = null) => ({ id, numero: 1, etat, erreur });
    const g: Generation = {
      ...GENERATION,
      objets: [
        {
          ...a!, voie: "code", peut_fabriquer: true, peut_rechoisir: true, motif: null, essai: essai(40, "echec", "contrôles en échec : Dimensions"),
          ton: "warn", statut: "Échec à l'étape Tests : contrôles en échec : Dimensions",
          etapes: a!.etapes.map((p, i) => ({ ...p, etat: i < 2 ? "fait" : i === 2 ? "echec" : "a_faire" })),
        },
        {
          ...b!, voie: "code", peut_fabriquer: false, peut_rechoisir: false, motif: "déjà fabriqué : il attend la revue", essai: essai(41, "pret"),
          vignette: "/api/fichiers/essais/41/vignette.png", planche: "/api/fichiers/essais/41/planche.png", asset_id: "TST_PROP_Objet_A",
          statut: "Prêt pour la revue", ton: "good", pct: 100, etapes: b!.etapes.map((p) => ({ ...p, etat: "fait" })),
        },
      ],
    };
    const { appels } = mockApi({
      ...BASE,
      [`GET /api/lots/${LID}/generation`]: g,
      [`POST /api/lots/${LID}/fabriquer`]: { taches: [1] },
      [`POST /api/lots/${LID}/objets/${a!.id}/rouvrir`]: {},
      [`GET /api/lots/${LID}/references`]: REFERENCES,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/generation`);
    expect(await screen.findByRole("img", { name: `Vignette de ${b!.nom}` })).toHaveAttribute("src", "/api/fichiers/essais/41/vignette.png");
    expect(screen.getByRole("link", { name: "Voir la planche" })).toHaveAttribute("href", "/api/fichiers/essais/41/planche.png");
    expect(screen.getByText("TST_PROP_Objet_A")).toBeInTheDocument();
    expect(screen.getByText(/: en échec/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Fabriquer les objets code/ })).not.toBeInTheDocument(); // on lance depuis les Références
    await utilisateur.click(screen.getByRole("button", { name: "Refaire (essai 2)" }));
    await waitFor(() => expect(appels.some((x) => x.methode === "POST" && x.chemin === `/api/lots/${LID}/fabriquer`)).toBe(true));
    expect(appels.find((x) => x.chemin === `/api/lots/${LID}/fabriquer`)!.corps).toEqual({ objet_id: a!.id });
    await utilisateur.click(screen.getByRole("button", { name: "Choisir une autre version" }));
    expect(await screen.findByRole("heading", { name: "Choisis une référence par objet" })).toBeInTheDocument();
  });
});

describe("Réglages · File de tâches et dépenses", () => {
  it("tâches récentes de tous les lots et styles, Relancer ; dépense réelle et appels simulés", async () => {
    const reglages: Reglages = {
      ...REGLAGES,
      etat: { ...REGLAGES.etat, claude_depense_mois: { usd: 0.0312, appels: 2, briefs: 2, avis: 0, appels_simules: 3, sans_tarif: 0 } },
    };
    const echec = TACHES_RECENTES.taches.find((t) => t.peut_relancer)!;
    const { appels } = mockApi({
      ...BASE,
      "GET /api/reglages": reglages,
      "GET /api/worker/taches": TACHES_RECENTES,
      ...Object.fromEntries(TACHES_RECENTES.taches.filter((t) => t.peut_relancer).map((t) => [`POST /api/taches/${t.id}/relancer`, {}])),
    });
    const utilisateur = userEvent.setup();
    rendreApp("/reglages");
    expect(await screen.findByText("0,0312 $ · 2 briefs, 0 avis · 3 appels simulés, gratuits")).toBeInTheDocument();
    for (const t of TACHES_RECENTES.taches.filter((x) => x.contexte)) {
      const liens = screen.getAllByRole("link", { name: t.contexte!.libelle }).map((l) => l.getAttribute("href"));
      expect(liens).toContain(t.contexte!.lien);
    }
    await utilisateur.click(screen.getAllByRole("button", { name: "Relancer" })[0]!);
    await waitFor(() => expect(appels.some((a) => a.methode === "POST" && a.chemin === `/api/taches/${echec.id}/relancer`)).toBe(true));
  });
});

describe("Menu", () => {
  it("se relit tout seul toutes les 15 s (le worker travaille sans l'écran)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { appels } = mockApi({ ...BASE, [`GET /api/lots/${LID}/generation`]: GENERATION });
    rendreApp(`/lots/${LID}/generation`);
    await screen.findByText(/Renouvelés le 1er novembre/);
    const lectures = () => appels.filter((a) => a.chemin === "/api/menu").length;
    const avant = lectures();
    await vi.advanceTimersByTimeAsync(15_000);
    await waitFor(() => expect(lectures()).toBeGreaterThan(avant));
  });
});
