import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Reglages as ReglagesApi, ReglagesEnvoyes } from "../../api/types";
import { MENU_VIDE, REGLAGES, mockApi, reponseErreur } from "../../test/api-mock";
import { rendreApp } from "../../test/rendre";

afterEach(() => vi.unstubAllGlobals());

function monter(extra: Record<string, unknown> = {}) {
  return mockApi({
    "GET /api/menu": MENU_VIDE,
    "GET /api/notifications": [],
    "GET /api/reglages": REGLAGES,
    "PUT /api/reglages": (init: RequestInit | undefined) => {
      const corps = JSON.parse(String(init?.body)) as ReglagesEnvoyes;
      const r: ReglagesApi = { ...REGLAGES, ...corps, etat: REGLAGES.etat };
      return r;
    },
    ...extra,
  });
}

describe("Réglages", () => {
  it("charge GET /api/reglages et affiche les valeurs", async () => {
    monter();
    rendreApp("/reglages");
    const cle = await screen.findByLabelText("Clé API", { selector: "#meshy-key" });
    expect(screen.getByRole("heading", { level: 1, name: "Réglages" })).toBeInTheDocument();
    expect(cle).toHaveValue("");
    expect(cle).toHaveAttribute("placeholder", "••••ab12");
    expect(screen.getByLabelText("Clé API", { selector: "#claude-key" })).toHaveAttribute("placeholder", "Aucune clé");

    const solde = screen.getByText(/crédits restants/);
    expect(solde).toHaveTextContent(/574 \/ 1[\s\u202f\u00a0]000 crédits restants/);
    expect(solde).toHaveTextContent("lu par l'API à l'ouverture de l'app");
    expect(screen.getByText(/≈ 0,45 \$/)).toBeInTheDocument();
    expect(screen.getByText(/5 briefs et 14 avis IA/)).toBeInTheDocument();
    expect(screen.getByLabelText("Renouvellement")).toHaveValue("1");
    expect(screen.getByLabelText("Alerte")).toHaveValue("80");
    expect(screen.getByLabelText("Modèle")).toHaveValue("claude-sonnet-5-5");
    expect(screen.getByLabelText("Plafond mensuel")).toHaveValue(5);
    expect(screen.getByLabelText("Compte itch.io")).toHaveValue("mon-compte");
    expect(screen.getByLabelText("Canal")).toHaveValue("assets");
    expect(screen.getByLabelText("Exécutable", { selector: "#blender-path" })).toHaveValue("/usr/bin/blender");
    expect(screen.getByLabelText("Adresse")).toHaveValue("http://127.0.0.1:8188");
    expect(screen.getByLabelText("Dossier")).toHaveValue("assets/");
    expect(screen.getByLabelText("File Meshy")).toHaveValue("3");
    expect(screen.getByLabelText("File Blender")).toHaveValue("2");
    expect(screen.getByLabelText("Relances automatiques")).toHaveValue(3);
    expect(screen.getByLabelText(/Dans l'app/)).toBeChecked();
    expect(screen.getByLabelText(/Aussi en notification de l'ordinateur/)).not.toBeChecked();
    expect(screen.getAllByText("Non testé").length).toBeGreaterThan(0);
    // Mode simulé coché par défaut
    expect(within(screen.getByRole("radiogroup", { name: "Mode Meshy" })).getByRole("radio", { name: "Simulé" })).toBeChecked();
  });

  it("affiche « Solde non lu » quand meshy_solde est null", async () => {
    monter({ "GET /api/reglages": { ...REGLAGES, etat: { ...REGLAGES.etat, meshy_solde: null } } });
    rendreApp("/reglages");
    expect(await screen.findByText("Solde non lu")).toBeInTheDocument();
  });

  it("modifie une valeur, Enregistrer envoie PUT avec la bonne forme (clé absente si vide), puis confirme", async () => {
    const { appels } = monter();
    const utilisateur = userEvent.setup();
    rendreApp("/reglages");
    await screen.findByLabelText("Renouvellement");

    await utilisateur.selectOptions(screen.getByLabelText("Renouvellement"), "15");
    await utilisateur.selectOptions(screen.getByLabelText("Alerte"), "0");
    await utilisateur.selectOptions(screen.getByLabelText("Modèle"), "claude-haiku-5-5");
    await utilisateur.selectOptions(screen.getByLabelText("File Meshy"), "5");
    const relances = screen.getByLabelText("Relances automatiques");
    await utilisateur.clear(relances);
    await utilisateur.type(relances, "2");
    await utilisateur.click(screen.getByLabelText(/Aussi en notification de l'ordinateur/));
    await utilisateur.click(within(screen.getByRole("radiogroup", { name: "Mode Meshy" })).getByRole("radio", { name: "Réel" }));

    await utilisateur.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() => expect(appels.some((a) => a.methode === "PUT" && a.chemin === "/api/reglages")).toBe(true));
    const put = appels.find((a) => a.methode === "PUT")!;
    const corps = put.corps as ReglagesEnvoyes & { etat?: unknown };
    expect(corps.etat).toBeUndefined();
    expect(corps.services.meshy.mode).toBe("reel");
    expect(corps.services.meshy.renouvellement_jour).toBe(15);
    expect(corps.services.meshy.alerte_pct).toBe(0);
    expect(corps.services.meshy.credits_mensuels).toBe(1000);
    expect(corps.services.claude.modele).toBe("claude-haiku-5-5");
    expect(corps.services.claude.plafond_mensuel_usd).toBe(5);
    expect(corps.files).toEqual({ gpu: 1, meshy: 5, blender: 2, relances_max: 2 });
    expect(corps.notifications).toEqual({ app: true, bureau: true });
    expect(corps.outils.blender.chemin).toBe("/usr/bin/blender");
    expect(corps.bibliotheque).toEqual({ dossier: "assets/", purge_rejets_jours: 30 });
    // Champs de clé vides : aucune cle_api envoyée
    expect("cle_api" in corps.services.meshy).toBe(false);
    expect("cle_api" in corps.services.claude).toBe(false);
    expect("cle_api" in corps.services.itchio).toBe(false);

    expect(await screen.findByText("Réglages enregistrés")).toBeInTheDocument();
    // Rechargé depuis la réponse du PUT
    expect(screen.getByLabelText("Renouvellement")).toHaveValue("15");
  });

  it("une clé tapée est envoyée, une clé effacée est envoyée à null", async () => {
    const { appels } = monter();
    const utilisateur = userEvent.setup();
    rendreApp("/reglages");
    const cleClaude = await screen.findByLabelText("Clé API", { selector: "#claude-key" });
    await utilisateur.type(cleClaude, "sk-nouvelle");

    // Meshy : clé définie, bouton Effacer
    const carteMeshy = screen.getByRole("heading", { level: 3, name: "Meshy" }).closest(".reglages__carte")!;
    await utilisateur.click(within(carteMeshy as HTMLElement).getByRole("button", { name: "Effacer la clé" }));
    expect(within(carteMeshy as HTMLElement).getByRole("button", { name: "Garder la clé" })).toBeInTheDocument();

    await utilisateur.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(appels.some((a) => a.methode === "PUT")).toBe(true));
    const corps = appels.find((a) => a.methode === "PUT")!.corps as ReglagesEnvoyes;
    expect(corps.services.claude.cle_api).toBe("sk-nouvelle");
    expect(corps.services.meshy.cle_api).toBeNull();
    expect("cle_api" in corps.services.itchio).toBe(false);

    // Après enregistrement, les champs de clé sont vidés
    await screen.findByText("Réglages enregistrés");
    expect(screen.getByLabelText("Clé API", { selector: "#claude-key" })).toHaveValue("");
  });

  it("Annuler recharge depuis l'API et oublie les modifications", async () => {
    const { appels } = monter();
    const utilisateur = userEvent.setup();
    rendreApp("/reglages");
    const canal = await screen.findByLabelText("Canal");
    await utilisateur.clear(canal);
    await utilisateur.type(canal, "autre");
    expect(canal).toHaveValue("autre");

    const avant = appels.filter((a) => a.chemin === "/api/reglages").length;
    await utilisateur.click(screen.getByRole("button", { name: "Annuler" }));
    await waitFor(() => expect(appels.filter((a) => a.chemin === "/api/reglages").length).toBe(avant + 1));
    await waitFor(() => expect(screen.getByLabelText("Canal")).toHaveValue("assets"));
    expect(appels.some((a) => a.methode === "PUT")).toBe(false);
  });

  it("affiche l'erreur 422 renvoyée par le PUT", async () => {
    monter({ "PUT /api/reglages": () => reponseErreur(422, "Réglages invalides", "plafond_mensuel_usd doit être positif") });
    const utilisateur = userEvent.setup();
    rendreApp("/reglages");
    await screen.findByLabelText("Canal");
    await utilisateur.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Réglages invalides : plafond_mensuel_usd doit être positif");
  });

  it("Tester la connexion affiche l'état renvoyé par l'API", async () => {
    const { appels } = monter({
      "POST /api/reglages/tester/meshy": { ok: true, etat: "Connecté", message: "Solde lu : 574 crédits", details: {} },
      "POST /api/reglages/tester/claude": { ok: false, etat: "Erreur", message: "Clé absente", details: {} },
      "POST /api/reglages/tester/blender": { ok: true, etat: "Détecté", message: "Blender 5.2.2", details: {} },
      "POST /api/reglages/tester/comfyui": { ok: true, etat: "Joignable", message: "", details: {} },
    });
    const utilisateur = userEvent.setup();
    rendreApp("/reglages");
    await screen.findByLabelText("Canal");

    const carte = (nom: string) => within(screen.getByRole("heading", { level: 3, name: nom }).closest(".reglages__carte") as HTMLElement);

    await utilisateur.click(carte("Meshy").getByRole("button", { name: "Tester la connexion" }));
    expect(await carte("Meshy").findByText("Connecté")).toBeInTheDocument();
    expect(carte("Meshy").getByText("Solde lu : 574 crédits")).toBeInTheDocument();

    await utilisateur.click(carte("API Claude").getByRole("button", { name: "Tester la connexion" }));
    expect(await carte("API Claude").findByText("Erreur")).toBeInTheDocument();
    expect(carte("API Claude").getByText("Clé absente")).toBeInTheDocument();

    await utilisateur.click(carte("Blender").getByRole("button", { name: "Tester" }));
    expect(await carte("Blender").findByText("Détecté")).toBeInTheDocument();

    await utilisateur.click(carte("ComfyUI").getByRole("button", { name: "Tester" }));
    expect(await carte("ComfyUI").findByText("Joignable")).toBeInTheDocument();

    expect(appels.filter((a) => a.methode === "POST" && a.chemin.startsWith("/api/reglages/tester/")).map((a) => a.chemin)).toEqual([
      "/api/reglages/tester/meshy",
      "/api/reglages/tester/claude",
      "/api/reglages/tester/blender",
      "/api/reglages/tester/comfyui",
    ]);
  });

  it("affiche une erreur claire si GET échoue", async () => {
    monter({ "GET /api/reglages": () => reponseErreur(500, "Fichier illisible") });
    rendreApp("/reglages");
    expect(await screen.findByRole("alert")).toHaveTextContent("Fichier illisible");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });
});
