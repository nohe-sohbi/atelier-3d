import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ObjetReferences, References } from "../../api/types";
import {
  GENERATION,
  LANCEMENT,
  LOT_ENTETE_REFERENCES,
  MENU_VIDE,
  NOTIFICATIONS_VIDES,
  OBJET_CONSIGNE,
  OBJET_IMAGE_DONNEE,
  OBJET_REFERENCE_CHOISIE,
  QUATRE_AUTRES,
  REFERENCES,
  REFERENCES_EN_PREPARATION,
  mockApi,
} from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";

afterEach(() => {
  vi.unstubAllGlobals();
});

const LID = REFERENCES.lot_id;
const BASE = {
  "GET /api/menu": MENU_VIDE,
  "GET /api/notifications": NOTIFICATIONS_VIDES,
  [`GET /api/lots/${LID}`]: LOT_ENTETE_REFERENCES,
};
const [PREMIER, DEUXIEME] = REFERENCES.objets;

/** La vue du lot avec un objet remplacé (comme la relirait l'API après une action). */
function avec(r: References, o: ObjetReferences): References {
  const objets = r.objets.map((x) => (x.id === o.id ? o : x));
  const choisies = objets.filter((x) => x.peut_changer && x.choix_id !== null).length;
  return { ...r, objets, choisies, sans_choix: objets.filter((x) => x.choix_id === null).map((x) => x.nom), peut_lancer: choisies > 0 };
}

describe("Références", () => {
  it("pendant la préparation : 4 cases en attente par objet, « 4 autres » et le lancement attendent", async () => {
    mockApi({ ...BASE, [`GET /api/lots/${LID}/references`]: REFERENCES_EN_PREPARATION });
    rendreApp(`/lots/${LID}/references`);
    expect(await screen.findByRole("heading", { name: "Choisis une référence par objet" })).toBeInTheDocument();
    for (const o of REFERENCES_EN_PREPARATION.objets) {
      const carte = within(screen.getByRole("region", { name: o.nom }));
      expect(carte.getByText(/En attente/)).toBeInTheDocument();
      expect(carte.getByRole("button", { name: /4 autres · 12 crédits/ })).toBeDisabled();
    }
    expect(screen.getByText(/Images simulées : Meshy est en mode simulé/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lancer la génération 3D" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Modifier le style" })).toHaveAttribute("href", `/styles?style=${REFERENCES.style.code}`);
  });

  it("choisir une image par objet, puis lancer : les objets sans référence sont annoncés mis de côté, on arrive sur Génération", async () => {
    let r = REFERENCES;
    const { appels } = mockApi({
      ...BASE,
      [`GET /api/lots/${LID}/references`]: () => r,
      [`PUT /api/lots/${LID}/objets/${PREMIER!.id}/reference`]: () => {
        r = avec(r, OBJET_REFERENCE_CHOISIE);
        return OBJET_REFERENCE_CHOISIE;
      },
      [`POST /api/lots/${LID}/lancer`]: LANCEMENT,
      [`GET /api/lots/${LID}/generation`]: GENERATION,
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/references`);
    const carte = within(await screen.findByRole("region", { name: PREMIER!.nom }));
    const tuiles = carte.getAllByRole("button", { name: new RegExp(`^Image \\d sur 4 pour`) });
    expect(tuiles).toHaveLength(4);
    expect(tuiles.every((t) => t.getAttribute("aria-pressed") === "false")).toBe(true);
    expect(screen.getByRole("button", { name: "Lancer la génération 3D" })).toBeDisabled();

    await utilisateur.click(tuiles[0]!);
    await waitFor(() => expect(carte.getAllByRole("button", { name: /^Image 1 sur 4/ })[0]).toHaveAttribute("aria-pressed", "true"));
    const choix = appels.find((a) => a.methode === "PUT")!;
    expect(choix.corps).toEqual({ proposition_id: PREMIER!.propositions[0]!.id });
    expect(await screen.findByText(`1 sur ${REFERENCES.a_choisir} choisies`)).toBeInTheDocument();
    expect(screen.getByText(/sans référence : .* seront mis de côté/)).toBeInTheDocument();

    await utilisateur.click(screen.getByRole("button", { name: "Lancer la génération 3D" }));
    expect(await screen.findByRole("list", { name: "Où en est la fabrication" })).toBeInTheDocument();
    expect(appels.some((a) => a.methode === "POST" && a.chemin === `/api/lots/${LID}/lancer`)).toBe(true);
  });

  it("réécrire la consigne : la phrase de l'app s'affiche, ta version part avec « Refaire 4 images »", async () => {
    let r = REFERENCES;
    const { appels } = mockApi({
      ...BASE,
      [`GET /api/lots/${LID}/references`]: () => r,
      [`PUT /api/lots/${LID}/objets/${PREMIER!.id}/consigne`]: OBJET_CONSIGNE,
      [`POST /api/lots/${LID}/objets/${PREMIER!.id}/propositions`]: () => {
        r = avec(r, QUATRE_AUTRES.objet);
        return QUATRE_AUTRES;
      },
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/references`);
    const carte = within(await screen.findByRole("region", { name: PREMIER!.nom }));
    await utilisateur.click(carte.getByRole("button", { name: `Modifier la consigne de ${PREMIER!.nom}` }));
    const champ = carte.getByRole("textbox", { name: "Consigne envoyée à l'IA" });
    expect(champ).toHaveValue(PREMIER!.consigne);
    await utilisateur.clear(champ);
    await utilisateur.type(champ, "Une consigne réécrite à la main.");
    await utilisateur.click(carte.getByRole("button", { name: /Refaire 4 images avec cette consigne · 12 crédits/ }));
    await waitFor(() => expect(carte.getAllByText(/En attente|Meshy/).length).toBeGreaterThan(0));
    const ecrits = appels.filter((a) => a.methode !== "GET").map((a) => [a.methode, a.corps]);
    expect(ecrits).toEqual([
      ["PUT", { consigne: "Une consigne réécrite à la main." }],
      ["POST", {}],
    ]);
    expect(carte.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("ta propre image : envoyée, elle devient le choix ; « 4 images d'après ton image » part avec elle comme modèle", async () => {
    let r = REFERENCES;
    const perso = OBJET_IMAGE_DONNEE.propositions.find((p) => p.genre === "perso")!;
    const { appels } = mockApi({
      ...BASE,
      [`GET /api/lots/${LID}/references`]: () => r,
      [`POST /api/lots/${LID}/objets/${DEUXIEME!.id}/image`]: () => {
        r = avec(r, OBJET_IMAGE_DONNEE);
        return OBJET_IMAGE_DONNEE;
      },
      [`POST /api/lots/${LID}/objets/${DEUXIEME!.id}/propositions`]: { ...QUATRE_AUTRES, objet: { ...OBJET_IMAGE_DONNEE, preparation: QUATRE_AUTRES.objet.preparation } },
    });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/references`);
    const carte = within(await screen.findByRole("region", { name: DEUXIEME!.nom }));
    const fichier = new File(["png"], "croquis.png", { type: "image/png" });
    await utilisateur.upload(carte.getByLabelText(`Choisir ton image pour ${DEUXIEME!.nom}`), fichier);
    const tuile = await carte.findByRole("button", { name: `Ton image pour ${DEUXIEME!.nom}` });
    expect(tuile).toHaveAttribute("aria-pressed", "true");
    expect(appels.some((a) => a.methode === "POST" && a.chemin === `/api/lots/${LID}/objets/${DEUXIEME!.id}/image`)).toBe(true);
    await utilisateur.click(carte.getByRole("button", { name: /4 images d'après ton image · 12 crédits/ }));
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith("/propositions"))).toBe(true));
    expect(appels.find((a) => a.chemin.endsWith("/propositions"))!.corps).toEqual({ modele_id: perso.id });
  });

  it("une préparation en échec : le motif et Réessayer", async () => {
    const enEchec: References = {
      ...REFERENCES,
      objets: [{ ...PREMIER!, propositions: [], preparation: null, erreur: { tache_id: 77, message: "crédits Meshy insuffisants", peut_relancer: true } }],
    };
    const { appels } = mockApi({ ...BASE, [`GET /api/lots/${LID}/references`]: enEchec, "POST /api/taches/77/relancer": {} });
    const utilisateur = userEvent.setup();
    rendreApp(`/lots/${LID}/references`);
    const alerte = await screen.findByRole("alert");
    expect(alerte).toHaveTextContent("Préparation en échec : crédits Meshy insuffisants");
    await utilisateur.click(within(alerte).getByRole("button", { name: "Réessayer" }));
    await waitFor(() => expect(appels.some((a) => a.methode === "POST" && a.chemin === "/api/taches/77/relancer")).toBe(true));
  });
});
