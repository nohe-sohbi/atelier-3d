import { spawnSync } from "node:child_process";
import { expect, test } from "./garde-fous";
import { RACINE } from "./serveur";

const ENTREES: Array<[string, string, number]> = [
  ["Bibliothèque", "Bibliothèque", 9],
  ["Générateurs", "Générateurs", 11],
  ["Accueil", "Accueil", 11],
];

test.describe("Étape 1 · Socle", () => {
  test("l'API répond sur /sante et /api/sante, et une route inconnue répond en JSON", async ({ request }) => {
    for (const chemin of ["/sante", "/api/sante"]) {
      const r = await request.get(chemin);
      expect(r.ok()).toBe(true);
      expect((await r.json()).statut).toBe("ok");
    }
    const inconnue = await request.get("/api/nexistepas");
    expect(inconnue.status()).toBe(404);
    expect(await inconnue.json()).toEqual({ erreur: "Not Found", detail: null });
  });

  test("chaque entrée du menu ouvre sa page « Arrive à l'étape N du plan »", async ({ page }) => {
    await page.goto("/");
    const menu = page.getByRole("navigation", { name: "Menu principal" });
    for (const [libelle, titre, etape] of ENTREES) {
      await menu.getByRole("link", { name: libelle }).click();
      await expect(page.getByRole("heading", { level: 1, name: titre })).toBeVisible();
      await expect(page.getByText(`Arrive à l'étape ${etape} du plan`)).toBeVisible();
      await expect(menu.getByRole("link", { name: libelle })).toHaveAttribute("aria-current", "page");
    }
    // Lots est construit (étape 3) : la page s'ouvre sur ses filtres.
    await menu.getByRole("link", { name: "Lots" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Lots" })).toBeVisible();
    await expect(page.getByRole("group", { name: "Filtrer les lots" })).toBeVisible();
    await expect(menu.getByRole("link", { name: "Lots" })).toHaveAttribute("aria-current", "page");
    // La jauge vient du simulateur et le dit ; aucune collection n'est inventée.
    await expect(page.getByText("· simulé")).toBeVisible();
    await expect(page.getByText("Aucune collection épinglée")).toBeVisible();
  });

  test("la cloche s'ouvre sur ce que l'API contient (« Aucune notification » quand il n'y en a pas)", async ({ page, request }) => {
    // D'autres scénarios ont pu écrire des notifications (une revue prête) : on compare avec l'API.
    const { notifications } = (await (await request.get("/api/notifications")).json()) as { notifications: Array<{ titre: string }> };
    await page.goto("/");
    await page.getByRole("button", { name: /^Notifications/ }).click();
    const panneau = page.getByRole("region", { name: "Notifications" });
    if (notifications.length === 0) await expect(panneau.getByText("Aucune notification")).toBeVisible();
    else await expect(panneau.getByText(notifications[0]!.titre)).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(panneau).toBeHidden();
  });

  test("Réglages : une valeur enregistrée est conservée après rechargement ; Annuler oublie", async ({ page }) => {
    await page.goto("/reglages");
    await expect(page.getByRole("heading", { level: 1, name: "Réglages" })).toBeVisible();
    const renouvellement = page.getByLabel("Renouvellement");
    await expect(renouvellement).toHaveValue("1");
    await renouvellement.selectOption("15");
    await page.getByRole("button", { name: "Enregistrer" }).click();
    await expect(page.getByText("Réglages enregistrés")).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Renouvellement")).toHaveValue("15");

    const canal = page.getByLabel("Canal");
    await canal.fill("autre");
    await page.getByRole("button", { name: "Annuler" }).click();
    await expect(page.getByLabel("Canal")).toHaveValue("assets");
  });

  test("Réglages : les tests de connexion répondent, simulés Connecté, outils absents Introuvable, jamais verts", async ({ page, request }) => {
    const presence = (await (await request.get("/api/reglages")).json()).etat.outils as Record<string, { present: boolean }>;
    await page.goto("/reglages");
    await expect(page.getByRole("heading", { level: 1, name: "Réglages" })).toBeVisible();
    const carte = (nom: string) => page.locator(".reglages__carte", { has: page.getByRole("heading", { level: 3, name: nom }) });

    await carte("Meshy").getByRole("button", { name: "Tester la connexion" }).click();
    await expect(carte("Meshy").getByText("Connecté")).toBeVisible();
    await carte("API Claude").getByRole("button", { name: "Tester la connexion" }).click();
    await expect(carte("API Claude").getByText("Connecté")).toBeVisible();
    await carte("ComfyUI").getByRole("button", { name: "Tester" }).click();
    await expect(carte("ComfyUI").getByText("Joignable")).toBeVisible();
    await carte("itch.io").getByRole("button", { name: /Tester/ }).click();
    await expect(carte("itch.io").getByText("Connecté")).toBeVisible();

    // La config de test laisse Blender vide : « Introuvable » dès l'ouverture, et toujours après le test, jamais en vert.
    // glTF-Validator et Git LFS dépendent de la machine. glTF-Validator : l'attente suit ce que l'API dit de sa
    // présence. Git LFS : l'API ne regarde que git à l'ouverture ; l'attente suit `git lfs version` sur la machine.
    const blender = carte("Blender");
    await expect(blender.getByRole("status")).toHaveText("Introuvable");
    await blender.getByRole("button", { name: "Tester" }).click();
    await expect(blender.getByRole("status")).toHaveText("Introuvable");
    await expect(blender.getByRole("status")).not.toHaveClass(/pastille--succes/);
    await expect(blender.getByText(/Aucun Blender renseigné|introuvable/)).toBeVisible();
    await carte("glTF-Validator").getByRole("button", { name: "Tester" }).click();
    await expect(carte("glTF-Validator").getByRole("status")).toHaveText(presence.gltf_validator!.present ? /Détecté|Erreur/ : "Introuvable");

    await carte("Bibliothèque").getByRole("button", { name: "Tester Git LFS" }).click();
    const lfs = spawnSync("git", ["lfs", "version"], { cwd: RACINE }).status === 0;
    await expect(carte("Bibliothèque").getByRole("status")).toHaveText(lfs ? /Détecté|Erreur/ : "Introuvable");
  });
});
