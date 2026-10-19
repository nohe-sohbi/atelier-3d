import { expect, test } from "./garde-fous";

test.describe("Étape 3 · Lots et Brief", () => {
  test("Nouveau lot → Brief → liste proposée (simulée) → décocher → « À créer » passés en IA → références ; Lots montre l'étape 2", async ({ page }) => {
    // D'autres scénarios ont pu créer des lots avant : celui-ci ne suppose pas une liste vide.
    await page.goto("/lots");
    await expect(page.getByRole("heading", { level: 1, name: "Lots" })).toBeVisible();
    await page.getByRole("main").getByRole("link", { name: "Nouveau lot" }).first().click();

    // Le lot est créé vide et s'ouvre sur son Brief ; les étapes suivantes sont verrouillées.
    await expect(page).toHaveURL(/\/lots\/\d+\/brief$/);
    const etapes = page.getByRole("navigation", { name: "Étapes du lot" });
    await expect(etapes.getByRole("link", { name: /Brief/ })).toHaveAttribute("aria-current", "step");
    await expect(etapes.getByRole("link", { name: /Références/ })).toHaveAttribute("aria-disabled", "true");
    await expect(page.getByText("Aucune liste pour l'instant")).toBeVisible();

    await page.getByLabel("Thème").fill("Thème de bout en bout");
    await page.getByLabel("Ce que tu veux").fill("Des contenants, du mobilier et un peu de décor.");
    await page.getByRole("button", { name: "Proposer la liste" }).click();

    // Le worker exécute la proposition avec Claude simulé : la liste le dit.
    const liste = page.getByRole("list", { name: "Objets proposés" });
    await expect(liste).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/Liste simulée/)).toBeVisible();
    const objets = liste.getByRole("listitem");
    const total = await objets.count();
    expect(total).toBeGreaterThan(2);
    await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("Lot sans nom"); // le nom proposé par Claude
    await expect(page.getByText("Thème de bout en bout", { exact: true })).toBeVisible(); // la puce du thème dans l'en-tête

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

    await page.getByRole("button", { name: "Générer les références" }).click();
    await expect(page).toHaveURL(/\/lots\/\d+\/references$/);
    await expect(page.getByText("Arrive à l'étape 6 du plan")).toBeVisible();
    await expect(etapes.getByRole("link", { name: /Références/ })).toHaveAttribute("aria-current", "step");

    const nom = (await page.getByRole("heading", { level: 1 }).textContent())!;
    await page.getByRole("navigation", { name: "Fil d'Ariane" }).getByRole("link", { name: "Lots" }).click();
    const ligne = page.getByRole("row", { name: new RegExp(nom.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) });
    await expect(ligne.getByText("Étape 2 sur 4 · Références")).toBeVisible();
    await expect(ligne.getByText("À toi")).toBeVisible();
  });
});
