import { expect, test } from "./garde-fous";

test.describe("Étape 3 · Projets et Objets", () => {
  test("Créer → Objets → liste proposée (simulée) → décocher → « À créer » passés en IA → Look ; Projets montre l'étape 2", async ({ page }) => {
    // D'autres scénarios ont pu créer des projets avant : celui-ci ne suppose pas une liste vide.
    await page.goto("/lots");
    await expect(page.getByRole("heading", { level: 1, name: "Projets" })).toBeVisible();
    await page.getByRole("main").getByRole("link", { name: "Nouveau projet" }).first().click();

    // Créer : une phrase, le style prêt est déjà choisi ; la liste d'objets est demandée et l'écran Objets s'ouvre.
    await expect(page.getByRole("heading", { level: 1, name: "Que veux-tu créer ?" })).toBeVisible();
    await page.getByLabel("Ta demande").fill("Des contenants, du mobilier et un peu de décor.");
    await page.getByRole("button", { name: /Proposer les objets/ }).click();

    // Le projet est créé et s'ouvre sur Objets ; les étapes suivantes sont verrouillées.
    await expect(page).toHaveURL(/\/lots\/\d+\/brief$/);
    const etapes = page.getByRole("list", { name: "Étapes du projet" });
    await expect(etapes.getByRole("listitem").filter({ hasText: "Objets" })).toHaveAttribute("aria-current", "step");
    await expect(etapes.getByRole("link", { name: /Look/ })).toHaveAttribute("aria-disabled", "true");
    await expect(etapes.getByRole("link", { name: /Jeu/ })).toHaveAttribute("aria-disabled", "true");
    await expect(page.getByRole("complementary", { name: "Aide de cet écran" })).toContainText("Ici, tu choisis ce qui sera fabriqué.");

    // Le worker exécute la proposition avec Claude simulé : la liste le dit.
    const liste = page.getByRole("list", { name: "Objets proposés" });
    await expect(liste).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/Liste simulée/)).toBeVisible();
    const objets = liste.getByRole("listitem");
    const total = await objets.count();
    expect(total).toBeGreaterThan(2);
    await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("Projet sans nom"); // le nom proposé par Claude
    // Le thème se précise à l'écran Objets : il apparaît en puce dans l'en-tête.
    await page.getByLabel("Thème").fill("Thème de bout en bout");
    await page.getByLabel("Ce que tu veux").click();
    await expect(page.getByText("Thème de bout en bout", { exact: true })).toBeVisible();

    // Décocher un objet fabriqué : le compteur suit.
    const retenus = async () => Number((await page.getByText(/objets? retenus?$/).textContent())!.split(" ")[0]);
    const avant = await retenus();
    const ia = objets.filter({ has: page.locator(".voie--ia") }).first();
    await ia.getByRole("checkbox").uncheck();
    await expect.poll(retenus).toBe(avant - 1);

    // Chaque « À créer » : la demande s'écrit dans le dépôt (dossier temporaire), puis l'objet passe en voie IA.
    const aCreer = objets.filter({ has: page.locator(".voie--a_creer") });
    let premier = true;
    while ((await aCreer.count()) > 0) {
      await aCreer.first().getByRole("button", { name: "Préparer la demande pour Claude Code" }).click();
      const fenetre = page.getByRole("dialog");
      await expect(fenetre.getByText(/^generators\/demandes\/.+\.md$/)).toBeVisible();
      if (premier) {
        await fenetre.getByRole("button", { name: "Écrire dans le dépôt" }).click();
        await expect(fenetre.getByText("Écrite dans le dépôt")).toBeVisible();
        await expect(fenetre.getByRole("button", { name: "Demande écrite" })).toBeDisabled();
        premier = false;
      }
      await fenetre.getByRole("button", { name: "Passer en voie IA à la place" }).click();
      await expect(fenetre).toBeHidden();
    }
    await expect(page.getByText(/générateurs? à écrire avant de lancer/)).toBeHidden();

    await page.getByRole("button", { name: "Choisir les looks →" }).click();
    await expect(page).toHaveURL(/\/lots\/\d+\/references$/);
    await expect(page.getByRole("heading", { name: "Choisis un look par objet" })).toBeVisible();
    await expect(etapes.getByRole("listitem").filter({ hasText: "Look" })).toHaveAttribute("aria-current", "step");

    const nom = (await page.getByRole("heading", { level: 1 }).textContent())!;
    await page.getByRole("navigation", { name: "Fil d'Ariane" }).getByRole("link", { name: "Projets" }).click();
    const ligne = page.getByRole("row", { name: new RegExp(nom.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) });
    await expect(ligne.getByText("Étape 2 sur 6 · Look")).toBeVisible();
    await expect(ligne.getByText("À toi")).toBeVisible();
  });
});
