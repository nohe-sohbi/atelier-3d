import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { Afficheur } from "../../components/afficheur3d/afficheur";
import type { ObjetValidation, ValidationVue } from "../../api/types";
import { LOT_ENTETE_VALIDATION, MENU_VIDE, NOTIFICATIONS_VIDES, VALIDATION, mockApi, reponseErreur } from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";

// jsdom n'a pas de WebGL : l'afficheur est remplacé par un double qui note ce qu'on lui demande.
const mocks = vi.hoisted(() => ({ instances: [] as Array<Record<string, unknown>>, echec: false }));
vi.mock("../../components/afficheur3d/afficheur", () => ({
  creerAfficheur: () => {
    if (mocks.echec) throw new Error("WebGL indisponible");
    const a = {
      charger: vi.fn().mockResolvedValue({ largeur: 0.35, hauteur: 0.9, profondeur: 0.35, pied: 0, niveaux: 3 }),
      niveau: vi.fn(),
      mode: vi.fn(),
      lumiere: vi.fn(),
      reperes: vi.fn(),
      personnage: vi.fn(),
      tourner: vi.fn(),
      recentrer: vi.fn(),
      pointage: vi.fn(),
      effacerPastilles: vi.fn(),
      detruire: vi.fn(),
      surPointage: null,
      surPastille: null,
      surArretRotation: null,
    };
    mocks.instances.push(a);
    return a;
  },
}));

const LID = LOT_ENTETE_VALIDATION.id;
const [NET, A_REGARDER] = VALIDATION.objets as [ObjetValidation, ObjetValidation];

let etat: ValidationVue;
function servir(extra: Record<string, unknown> = {}) {
  etat = structuredClone(VALIDATION);
  return mockApi({
    "GET /api/menu": MENU_VIDE,
    "GET /api/notifications": NOTIFICATIONS_VIDES,
    [`GET /api/lots/${LID}`]: LOT_ENTETE_VALIDATION,
    [`GET /api/lots/${LID}/validation`]: () => etat,
    ...extra,
  });
}
/** Applique une décision à l'état simulé et recalcule le résumé, comme le ferait le serveur. */
function appliquer(id: number, nouvelEtat: ObjetValidation["etat"]) {
  const o = etat.objets.find((x) => x.id === id)!;
  o.etat = nouvelEtat;
  o.peut_annuler = nouvelEtat === "garde" || nouvelEtat === "jete";
  const n = (e: string) => etat.objets.filter((x) => x.etat === e).length;
  etat.resume = { total: etat.objets.length, a_valider: n("a_valider"), gardes: n("garde"), jetes: n("jete"), pas_prets: n("look") + n("en_fabrication") };
  etat.termine = etat.resume.a_valider === 0 && etat.resume.pas_prets === 0;
  return o;
}
/** Le panneau de décision d'un objet (la barre du téléphone répète ses boutons principaux). */
const panneau = (nom: string) => screen.getByRole("region", { name: nom });
const derniereInstance = () => mocks.instances.at(-1) as unknown as Afficheur & { charger: ReturnType<typeof vi.fn> };

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});
beforeEach(() => {
  mocks.instances.length = 0;
  mocks.echec = false;
});
afterEach(() => vi.unstubAllGlobals());

async function ouvrir() {
  rendreApp(`/lots/${LID}/revue`);
  return screen.findByRole("heading", { level: 2, name: NET.nom });
}

describe("Validation", () => {
  it("ouvre le premier objet à valider : sa 3D, son verdict en mots simples, ses raisons", async () => {
    servir();
    await ouvrir();
    await waitFor(() => expect(derniereInstance().charger).toHaveBeenCalledWith(NET.modele));
    const verdict = within(screen.getByText("Prêt à garder").closest(".verdict") as HTMLElement);
    expect(verdict.getByText("Posé au sol")).toBeInTheDocument();
    expect(verdict.getByText("Bien centré sur son point d'ancrage")).toBeInTheDocument();
    expect(verdict.getByText("Taille : 0,35 × 0,35 × 0,90 m")).toBeInTheDocument();
    expect(screen.getByText(NET.source!)).toBeInTheDocument();
    // La file : les deux objets, le premier est en cours.
    const file = within(screen.getByRole("list", { name: "Objets à valider" }));
    expect(file.getAllByRole("button")).toHaveLength(2);
    expect(file.getByRole("button", { name: NET.nom })).toHaveAttribute("aria-current", "true");
    expect(screen.getByText("2 à valider")).toBeInTheDocument();
  });

  it("un objet à regarder : le verdict est orange et met le défaut en premier", async () => {
    servir();
    const u = userEvent.setup();
    await ouvrir();
    await u.click(screen.getByRole("button", { name: A_REGARDER.nom }));
    expect(await screen.findByRole("heading", { level: 2, name: A_REGARDER.nom })).toBeInTheDocument();
    const verdict = screen.getByText("À regarder avant de garder").closest(".verdict") as HTMLElement;
    expect(verdict).toHaveClass("verdict--attention");
    const raisons = within(verdict).getAllByRole("listitem");
    expect(raisons[0]).toHaveTextContent("Des surfaces sont à l'envers (12 faces inversées)");
    expect(raisons[0]).toHaveClass("est-ko");
    // Une nouvelle 3D est chargée pour cet objet.
    await waitFor(() => expect(mocks.instances.length).toBeGreaterThan(1));
  });

  it("les trois questions guident : « Non » propose quoi faire, trois « Oui » mettent « Garder » en avant", async () => {
    servir();
    const u = userEvent.setup();
    await ouvrir();
    const guide = within(screen.getByRole("group", { name: "Regarde l'objet en 3 questions" }));
    const reponse = (q: string, r: "Oui" | "Non") => within(guide.getByRole("group", { name: q })).getByRole("button", { name: r });

    await u.click(reponse("Tourne-le : tout est bien de chaque côté ?", "Non"));
    expect(guide.getByText(/pointe le défaut sur l'objet/)).toBeInTheDocument();
    await u.click(reponse("Ressemble-t-il à ton image ?", "Oui"));
    await u.click(reponse("La taille te paraît juste ?", "Oui"));
    expect(guide.getByText(/Suis la suggestion en orange/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^✓ Garder dans/ })).not.toHaveClass("est-conseille");

    await u.click(reponse("Tourne-le : tout est bien de chaque côté ?", "Oui"));
    expect(guide.getByText(/Tout te paraît bon/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^✓ Garder dans/ })).toHaveClass("est-conseille");
  });

  it("les liens d'aide pilotent la 3D : tourner tout seul, personnage à côté de l'objet", async () => {
    servir();
    const u = userEvent.setup();
    await ouvrir();
    await waitFor(() => expect(derniereInstance().charger).toHaveBeenCalled());
    await u.click(screen.getByRole("button", { name: "Le faire tourner tout seul" }));
    await waitFor(() => expect(derniereInstance().tourner).toHaveBeenLastCalledWith(true));
    await u.click(screen.getByRole("button", { name: "Le voir à côté d'un personnage" }));
    await waitFor(() => expect(derniereInstance().personnage).toHaveBeenLastCalledWith(true));
    expect(screen.getByRole("button", { name: "Voir à côté d'un personnage" })).toHaveAttribute("aria-pressed", "true");
  });

  it("garder : POST, notification avec « Annuler », l'objet suivant s'ouvre ; Annuler revient sur lui", async () => {
    const { appels } = servir({
      [`POST /api/lots/${LID}/objets/${NET.id}/decision`]: (init: RequestInit | undefined) => {
        const d = JSON.parse(String(init?.body)).decision as string;
        return appliquer(NET.id, d === "annuler" ? "a_valider" : "garde");
      },
    });
    const u = userEvent.setup();
    await ouvrir();
    await u.click(screen.getByRole("button", { name: /^✓ Garder dans/ }));
    expect(await screen.findByRole("status")).toHaveTextContent(`${NET.nom} gardé dans ${VALIDATION.collection}`);
    expect(appels.find((a) => a.methode === "POST")?.corps).toEqual({ decision: "garder" });
    expect(await screen.findByRole("heading", { level: 2, name: A_REGARDER.nom })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `${NET.nom} : Gardé` })).toBeInTheDocument();

    await u.click(within(screen.getByRole("status")).getByRole("button", { name: "Annuler" }));
    expect(await screen.findByRole("heading", { level: 2, name: NET.nom })).toBeInTheDocument();
    expect(appels.filter((a) => a.methode === "POST").map((a) => (a.corps as { decision: string }).decision)).toEqual(["garder", "annuler"]);
  });

  it("jeter envoie le motif choisi ; quand tout est décidé, l'écran de fin propose l'Essai", async () => {
    const u = userEvent.setup();
    const { appels } = servir({
      [`POST /api/lots/${LID}/objets/${NET.id}/decision`]: () => appliquer(NET.id, "garde"),
      [`POST /api/lots/${LID}/objets/${A_REGARDER.id}/decision`]: () => appliquer(A_REGARDER.id, "jete"),
    });
    await ouvrir();
    await u.click(screen.getByRole("button", { name: /^✓ Garder dans/ }));
    await screen.findByRole("heading", { level: 2, name: A_REGARDER.nom });
    await u.click(screen.getByRole("button", { name: "Jeter cet objet" }));
    const jeter = within(screen.getByRole("group", { name: "Jeter" }));
    await u.click(jeter.getByRole("button", { name: "Proportions" }));
    await u.click(jeter.getByRole("button", { name: "Jeter l'objet" }));

    const fin = await screen.findByRole("heading", { name: "Tout est validé" });
    expect(fin).toBeInTheDocument();
    expect(appels.filter((a) => a.methode === "POST").at(-1)?.corps).toEqual({ decision: "jeter", motif: "proportions" });
    expect(screen.getByText(/1 objet gardé, 1 jeté/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Essayer les objets ensemble/ })).toHaveAttribute("href", `/lots/${LID}/essai`);
    expect(screen.getByRole("button", { name: `Revenir sur la décision : ${NET.nom}` })).toBeInTheDocument();
  });

  it("corriger : une pastille posée sur la 3D ouvre sa ligne ; les remarques partent avec la demande", async () => {
    const { appels } = servir({
      [`POST /api/lots/${LID}/objets/${NET.id}/decision`]: () => appliquer(NET.id, "look"),
    });
    const u = userEvent.setup();
    await ouvrir();
    await waitFor(() => expect(derniereInstance().charger).toHaveBeenCalled());
    const a = derniereInstance() as unknown as { surPointage: (n: number) => void };
    // L'utilisateur touche l'objet : l'afficheur annonce la pastille 1.
    await waitFor(() => expect(a.surPointage).toBeTypeOf("function"));
    a.surPointage(1);
    const ligne = await screen.findByLabelText("Défaut 1");
    await u.type(ligne, "anse trop fine");
    await u.type(screen.getByLabelText("Tes remarques"), "terre cuite plus claire");
    expect(screen.getByText(/4 nouveaux looks en tenant compte de tes remarques/)).toHaveTextContent("12 crédits");
    await u.click(screen.getByRole("button", { name: "Redessiner les looks" }));
    expect(await screen.findByRole("status")).toHaveTextContent("4 nouveaux looks arrivent, avec tes remarques");
    expect(appels.find((a) => a.methode === "POST")?.corps).toEqual({ decision: "corriger", notes: ["anse trop fine"], texte: "terre cuite plus claire" });
    expect(within(screen.getByRole("status")).getByRole("link", { name: "Ouvrir le Look" })).toHaveAttribute("href", `/lots/${LID}/references`);
  });

  it("refaire ramène au Look sans rien dépenser ; un refus du serveur s'affiche tel quel", async () => {
    let refuser = true;
    const { appels } = servir({
      [`POST /api/lots/${LID}/objets/${NET.id}/decision`]: () => (refuser ? reponseErreur(409, "Refaire : cet objet n'est pas à valider") : appliquer(NET.id, "look")),
    });
    const u = userEvent.setup();
    await ouvrir();
    await u.click(within(panneau(NET.nom)).getByRole("button", { name: "Refaire" }));
    expect(screen.getByText(/Gratuit : rien n'est refait/)).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Revenir au Look" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Refaire : cet objet n'est pas à valider");
    refuser = false;
    await u.click(screen.getByRole("button", { name: "Revenir au Look" }));
    expect(await screen.findByRole("status")).toHaveTextContent(`${NET.nom} retourne au Look`);
    expect(appels.filter((a) => a.methode === "POST")).toHaveLength(2);
  });

  it("un objet fait par script ne se corrige pas : l'écran renvoie vers « Refaire »", async () => {
    servir();
    etat.objets[0] = { ...NET, voie: "code", peut_corriger: false, credits_correction: 0 };
    const u = userEvent.setup();
    await ouvrir();
    await u.click(within(panneau(NET.nom)).getByRole("button", { name: "Corriger" }));
    expect(screen.getByText(/se règle par ses variantes/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Redessiner les looks" })).not.toBeInTheDocument();
  });

  it("sans WebGL : le message le dit, les vues et les vérifications restent", async () => {
    mocks.echec = true;
    servir();
    const u = userEvent.setup();
    await ouvrir();
    expect(await screen.findByText(/La 3D ne peut pas s'afficher ici/)).toBeInTheDocument();
    await u.click(screen.getByRole("tab", { name: /Vérifications/ }));
    expect(screen.getByText("Maillage fermé")).toBeInTheDocument();
    await u.click(screen.getByRole("tab", { name: "Avis de l'IA" }));
    expect(screen.getByText(/Aucun avis de l'IA/)).toBeInTheDocument();
  });

  it("un projet sans objet fabriqué renvoie vers la Fabrication, sans rien inventer", async () => {
    servir({ [`GET /api/lots/${LID}/validation`]: { ...VALIDATION, objets: [], resume: { total: 0, a_valider: 0, gardes: 0, jetes: 0, pas_prets: 0 } } });
    rendreApp(`/lots/${LID}/revue`);
    expect(await screen.findByText("Rien à valider pour l'instant")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voir la fabrication" })).toHaveAttribute("href", `/lots/${LID}/generation`);
  });
});
