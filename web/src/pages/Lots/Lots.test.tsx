import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ObjetsLot } from "../../api/types";
import {
  DEMANDE,
  DEMANDE_ECRITE,
  ESTIMATION_APPLIQUER,
  LOTS,
  LOTS_VIDES,
  LOT_CREE,
  LOT_DUPLIQUE,
  LOT_ENTETE,
  LOT_ENTETE_PROPOSE,
  LOT_ENTETE_STYLE_PLUS_RECENT,
  LOT_VALIDE,
  MENU_VIDE,
  NOTIFICATIONS_VIDES,
  OBJETS,
  OBJETS_PASSE_EN_IA,
  OBJETS_UN_DECOCHE,
  OBJETS_VIDES,
  PROPOSITION_LANCEE,
  REFUS_VALIDATION,
  STYLES,
  TACHE_TERMINEE,
  mockApi,
  reponseErreur,
} from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";
import { ilYA, texteDimensions, texteResume } from "./commun";

afterEach(() => vi.unstubAllGlobals());

const LID = LOT_ENTETE_PROPOSE.id;
const BASE = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS_VIDES,
  "GET /api/styles": STYLES,
};
/** Le Brief d'un lot dont la liste a été proposée (Claude simulé). */
const BRIEF = {
  ...BASE,
  [`GET /api/lots/${LID}`]: LOT_ENTETE_PROPOSE,
  [`GET /api/lots/${LID}/objets`]: OBJETS,
};
const A_CREER = OBJETS.objets.find((o) => o.voie === "a_creer")!;
const DECOCHE = OBJETS.objets.find((o) => OBJETS_UN_DECOCHE.objets.some((x) => x.id === o.id && x.retire && !o.retire))!;

describe("Lots", () => {
  it("liste les lots de l'API : filtres avec compteurs, étape, où il en est, lien vers l'étape", async () => {
    const { appels } = mockApi({ ...BASE, "GET /api/lots": (_i: unknown, url: URL) => (url.searchParams.get("groupe") === "termines" ? { ...LOTS, lots: [] } : LOTS) });
    const utilisateur = userEvent.setup();
    rendreApp("/lots");
    expect(screen.getByRole("heading", { level: 1, name: "Lots" })).toBeInTheDocument();
    const table = await screen.findByRole("table", { name: "Lots" });
    const lot = LOTS.lots[0]!;
    const ligne = within(table).getByRole("row", { name: new RegExp(lot.nom) });
    expect(within(ligne).getByRole("link", { name: lot.nom })).toHaveAttribute("href", lot.lien);
    expect(within(ligne).getByText(lot.libelle_etape)).toBeInTheDocument();
    expect(within(ligne).getByText(lot.statut)).toHaveClass(`ton--${lot.ton}`);
    expect(within(ligne).getByText(lot.detail)).toBeInTheDocument();
    expect(within(ligne).getByText(lot.style!.code)).toBeInTheDocument();
    expect(within(table).getAllByRole("row")).toHaveLength(LOTS.lots.length + 1);

    const filtres = within(screen.getByRole("group", { name: "Filtrer les lots" }));
    expect(filtres.getByRole("button", { name: `Tous · ${LOTS.compteurs.tous}` })).toHaveAttribute("aria-pressed", "true");
    await utilisateur.click(filtres.getByRole("button", { name: `Terminés · ${LOTS.compteurs.termines}` }));
    expect(await screen.findByText("Aucun lot terminé")).toBeInTheDocument();
    expect(appels.some((a) => a.chemin === "/api/lots?groupe=termines")).toBe(true);
    expect(filtres.getByRole("button", { name: /^Terminés/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("sans lot : état vide et Nouveau lot", async () => {
    mockApi({ ...BASE, "GET /api/lots": LOTS_VIDES });
    rendreApp("/lots");
    expect(await screen.findByText("Aucun lot pour l'instant")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Nouveau lot" }).length).toBeGreaterThan(1);
  });

  it("Nouveau lot crée un lot vide une seule fois puis ouvre son Brief", async () => {
    const { appels } = mockApi({
      ...BASE,
      "POST /api/lots": LOT_CREE,
      [`GET /api/lots/${LOT_CREE.id}`]: LOT_CREE,
      [`GET /api/lots/${LOT_CREE.id}/objets`]: OBJETS_VIDES,
    });
    rendreApp("/lots/nouveau");
    expect(await screen.findByRole("heading", { level: 2, name: "Brief" })).toBeInTheDocument();
    expect(screen.getByText("Aucune liste pour l'instant")).toBeInTheDocument();
    expect(appels.filter((a) => a.methode === "POST" && a.chemin === "/api/lots")).toHaveLength(1);
  });

  it("/lots/:id ouvre le lot sur l'étape où il en est", async () => {
    mockApi({ ...BASE, [`GET /api/lots/${LID}`]: LOT_VALIDE });
    rendreApp(`/lots/${LID}`);
    expect(await screen.findByText("Arrive à l'étape 6 du plan")).toBeInTheDocument();
  });
});

describe("En-tête de lot", () => {
  it("étapes non atteintes verrouillées, étape courante marquée, puce du style vers Styles, ligne d'état", async () => {
    mockApi(BRIEF);
    rendreApp(`/lots/${LID}/brief`);
    const etapes = within(await screen.findByRole("navigation", { name: "Étapes du lot" }));
    expect(etapes.getByRole("link", { name: /Brief/ })).toHaveAttribute("aria-current", "step");
    for (const nom of [/Références/, /Génération/, /Revue/]) expect(etapes.getByRole("link", { name: nom })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("heading", { level: 1, name: LOT_ENTETE_PROPOSE.nom })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: LOT_ENTETE_PROPOSE.style!.code })).toHaveAttribute("href", `/styles?style=${LOT_ENTETE_PROPOSE.style!.code}`);
    expect(screen.getByText(LOT_ENTETE_PROPOSE.ligne_etat)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Appliquer la v/ })).not.toBeInTheDocument();
  });

  it("renommer envoie PATCH {nom} ; Dupliquer ouvre la copie", async () => {
    const { appels } = mockApi({
      ...BRIEF,
      [`PATCH /api/lots/${LID}`]: { ...LOT_ENTETE_PROPOSE, nom: "Mon lot" },
      [`POST /api/lots/${LID}/dupliquer`]: LOT_DUPLIQUE,
      [`GET /api/lots/${LOT_DUPLIQUE.id}`]: LOT_DUPLIQUE,
      [`GET /api/lots/${LOT_DUPLIQUE.id}/objets`]: OBJETS_VIDES,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/brief`);
    await utilisateur.click(await screen.findByRole("button", { name: "Renommer le lot" }));
    const champ = screen.getByLabelText("Nom du lot");
    await utilisateur.clear(champ);
    await utilisateur.type(champ, "Mon lot{Enter}");
    expect(await screen.findByRole("heading", { level: 1, name: "Mon lot" })).toBeInTheDocument();
    expect(appels.find((a) => a.methode === "PATCH" && a.chemin === `/api/lots/${LID}`)?.corps).toEqual({ nom: "Mon lot" });

    await utilisateur.click(screen.getByRole("button", { name: "Dupliquer le lot" }));
    expect(await screen.findByRole("heading", { level: 1, name: LOT_DUPLIQUE.nom })).toBeInTheDocument();
  });

  it("« Appliquer la v1 » quand le style a une version plus récente : l'estimation seulement", async () => {
    mockApi({
      ...BASE,
      [`GET /api/lots/${LID}`]: LOT_ENTETE_STYLE_PLUS_RECENT,
      [`GET /api/lots/${LID}/appliquer-style`]: ESTIMATION_APPLIQUER,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/references`);
    const v = LOT_ENTETE_STYLE_PLUS_RECENT.style_plus_recent!;
    await utilisateur.click(await screen.findByRole("button", { name: `Appliquer la v${v.version}` }));
    const fenetre = screen.getByRole("dialog", { name: `Appliquer la v${v.version} · ${v.code}` });
    expect(await within(fenetre).findByText(/rien à refaire/)).toBeInTheDocument();
    expect(within(fenetre).getByRole("status")).toHaveTextContent(ESTIMATION_APPLIQUER.raison);
    expect(screen.getByText("Arrive à l'étape 6 du plan")).toBeInTheDocument();
  });
});

describe("Brief", () => {
  it("liste simulée : bandeau, pastilles de voie, dimensions, raison, résumé ; hors périmètre non cochable", async () => {
    mockApi(BRIEF);
    rendreApp(`/lots/${LID}/brief`);
    const liste = within(await screen.findByRole("list", { name: "Objets proposés" }));
    expect(screen.getByText(/Liste simulée/)).toBeInTheDocument();
    expect(liste.getAllByRole("listitem")).toHaveLength(OBJETS.objets.length);
    for (const o of OBJETS.objets) {
      const item = within(liste.getByText(o.nom).closest("li")!);
      expect(item.getByRole("checkbox", { name: o.nom })).toHaveProperty("checked", !o.retire);
      expect(item.getByText(texteDimensions(o.dimensions))).toBeInTheDocument();
      if (o.raison_voie) expect(item.getByText(o.raison_voie)).toBeInTheDocument();
    }
    const hors = OBJETS.objets.find((o) => o.voie === "hors_perimetre")!;
    expect(screen.getByRole("checkbox", { name: hors.nom })).toBeDisabled();
    expect(screen.getAllByText("À créer").length).toBe(OBJETS.objets.filter((o) => o.voie === "a_creer").length);
    expect(screen.getAllByRole("button", { name: "Préparer la demande pour Claude Code" })).toHaveLength(OBJETS.objets.filter((o) => o.voie === "a_creer").length);
    expect(screen.getByText(texteResume(OBJETS.resume))).toBeInTheDocument();
    expect(screen.getByText(`${OBJETS.resume.retenus} objets retenus`)).toBeInTheDocument();
  });

  it("décocher envoie PATCH {retenu: false} et le compteur suit la réponse", async () => {
    const { appels } = mockApi({ ...BRIEF, [`PATCH /api/lots/${LID}/objets/${DECOCHE.id}`]: OBJETS_UN_DECOCHE });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/brief`);
    await utilisateur.click(await screen.findByRole("checkbox", { name: DECOCHE.nom }));
    expect(await screen.findByText(`${OBJETS_UN_DECOCHE.resume.retenus} objets retenus`)).toBeInTheDocument();
    expect(appels.find((a) => a.methode === "PATCH")?.corps).toEqual({ retenu: false });
    expect(screen.getByRole("checkbox", { name: DECOCHE.nom })).not.toBeChecked();
  });

  it("Générer les références : un 409 s'affiche tel quel ; accepté, l'onglet Références s'ouvre", async () => {
    let accepte = false;
    mockApi({
      ...BRIEF,
      [`POST /api/lots/${LID}/valider-brief`]: () => (accepte ? LOT_VALIDE : reponseErreur(409, REFUS_VALIDATION.erreur)),
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/brief`);
    await utilisateur.click(await screen.findByRole("button", { name: "Générer les références" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(REFUS_VALIDATION.erreur);
    accepte = true;
    await utilisateur.click(screen.getByRole("button", { name: "Générer les références" }));
    expect(await screen.findByText("Arrive à l'étape 6 du plan")).toBeInTheDocument();
  });

  it("Proposer la liste : enregistre le besoin tapé, lance la tâche, suit la tâche, recharge la liste", async () => {
    let objets: ObjetsLot = OBJETS_VIDES;
    const { appels } = mockApi({
      ...BASE,
      [`GET /api/lots/${LID}`]: LOT_ENTETE,
      [`PATCH /api/lots/${LID}`]: LOT_ENTETE,
      [`GET /api/lots/${LID}/objets`]: () => objets,
      [`POST /api/lots/${LID}/proposition`]: () => {
        objets = OBJETS;
        return PROPOSITION_LANCEE;
      },
      [`GET /api/taches/${PROPOSITION_LANCEE.tache_id}`]: { ...TACHE_TERMINEE, id: PROPOSITION_LANCEE.tache_id },
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/brief`);
    const besoin = await screen.findByLabelText("Ce que tu veux");
    await utilisateur.clear(besoin);
    await utilisateur.type(besoin, "Des tonneaux et des caisses.");
    await utilisateur.click(screen.getByRole("button", { name: "Proposer la liste" }));
    expect(await screen.findByRole("list", { name: "Objets proposés" })).toBeInTheDocument();
    const ordre = appels.filter((a) => a.methode !== "GET").map((a) => `${a.methode} ${a.chemin}`);
    expect(ordre).toEqual([`PATCH /api/lots/${LID}`, `POST /api/lots/${LID}/proposition`]);
    expect(appels.find((a) => a.methode === "PATCH")?.corps).toMatchObject({ besoin: "Des tonneaux et des caisses." });
    expect(screen.getByRole("button", { name: "Reproposer la liste" })).toBeEnabled();
  });
});

describe("Demande pour Claude Code", () => {
  it("chemin, Markdown, Copier, Écrire dans le dépôt, Échap", async () => {
    const { appels } = mockApi({
      ...BRIEF,
      [`GET /api/lots/${LID}/objets/${A_CREER.id}/demande`]: DEMANDE,
      [`POST /api/lots/${LID}/objets/${A_CREER.id}/demande`]: DEMANDE_ECRITE,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/brief`);
    const item = (await screen.findByText(A_CREER.nom)).closest("li")!;
    const ouvreur = within(item).getByRole("button", { name: "Préparer la demande pour Claude Code" });
    await utilisateur.click(ouvreur);
    const fenetre = within(screen.getByRole("dialog", { name: `Demande pour Claude Code · ${A_CREER.nom}` }));
    expect(await fenetre.findByText(DEMANDE.chemin_md)).toBeInTheDocument();
    expect(fenetre.getByText("Pas encore écrite")).toBeInTheDocument();
    expect(fenetre.getByText(/# Générateur à écrire/)).toBeInTheDocument();

    await utilisateur.click(fenetre.getByRole("button", { name: "Copier le texte" }));
    expect(await navigator.clipboard.readText()).toBe(DEMANDE.texte_a_coller); // presse-papiers de user-event
    expect(fenetre.getByRole("button", { name: "Texte copié" })).toBeInTheDocument();

    await utilisateur.click(fenetre.getByRole("button", { name: "Écrire dans le dépôt" }));
    expect(await fenetre.findByText(DEMANDE_ECRITE.libelle_etat)).toBeInTheDocument();
    expect(fenetre.getByRole("button", { name: "Demande écrite" })).toBeDisabled();
    expect(fenetre.getByRole("status")).toHaveTextContent(DEMANDE_ECRITE.script_attendu);
    expect(appels.filter((a) => a.methode === "POST")).toHaveLength(1);

    await utilisateur.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(ouvreur).toHaveFocus();
  });

  it("Passer en voie IA à la place : PATCH {voie: ia}, puis le Brief relit la liste", async () => {
    let objets = OBJETS;
    const { appels } = mockApi({
      ...BRIEF,
      [`GET /api/lots/${LID}/objets`]: () => objets,
      [`GET /api/lots/${LID}/objets/${A_CREER.id}/demande`]: DEMANDE,
      [`PATCH /api/lots/${LID}/objets/${A_CREER.id}`]: () => {
        objets = OBJETS_PASSE_EN_IA;
        return OBJETS_PASSE_EN_IA;
      },
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/brief`);
    const item = (await screen.findByText(A_CREER.nom)).closest("li")!;
    await utilisateur.click(within(item).getByRole("button", { name: "Préparer la demande pour Claude Code" }));
    await utilisateur.click(await screen.findByRole("button", { name: "Passer en voie IA à la place" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(appels.find((a) => a.methode === "PATCH")?.corps).toEqual({ voie: "ia" });
    const apres = OBJETS_PASSE_EN_IA.objets.find((o) => o.id === A_CREER.id)!;
    expect(await within((await screen.findByText(A_CREER.nom)).closest("li")!).findByText(apres.voie === "ia" ? "IA" : apres.voie)).toBeInTheDocument();
  });
});

describe("outils des lots", () => {
  it("dates relatives et dimensions", () => {
    const maintenant = new Date("2026-10-19T12:00:00Z");
    expect(ilYA("2026-10-19T11:48:00Z", maintenant)).toBe("il y a 12 min");
    expect(ilYA("2026-10-18T09:00:00Z", maintenant)).toBe("hier");
    expect(texteDimensions({ largeur: 0.65, profondeur: 0.2, hauteur: 1.1, source: "style" })).toBe("0,65 × 1,10 m");
    expect(texteDimensions(null)).toBe("—");
  });
});
