import { expect, test } from "./garde-fous";
import { semerValidation } from "./semer";

test.describe("Validation · décisions sur de vrais objets", () => {
  // Le parcours enchaîne une douzaine de gestes, avec la 3D logicielle de Chromium recréée à chaque objet.
  test.setTimeout(150_000);

  test("verdict, trois questions, garder et annuler, jeter avec un motif, refaire : le serveur suit chaque geste", async ({ page, request }) => {
    const p = semerValidation("Validation e2e");
    const etat = async () => ((await (await request.get(`/api/lots/${p.lot_id}/validation`)).json()) as { objets: Array<{ nom: string; etat: string }> }).objets.map((o) => `${o.nom}:${o.etat}`);
    await page.goto(`/lots/${p.lot_id}/revue`);

    // L'en-tête a ses six étapes, la Validation est ouverte alors que la lanterne se fabrique encore.
    const etapes = page.getByRole("list", { name: "Étapes du projet" });
    await expect(etapes.getByRole("listitem")).toHaveCount(6);
    await expect(etapes.getByRole("link", { name: /Validation/ })).toBeVisible();

    // Premier objet : net. Verdict, raisons mesurées sur le fichier, questions.
    await expect(page.getByRole("heading", { level: 2, name: "Amphore" })).toBeVisible();
    await expect(page.getByText("Prêt à garder")).toBeVisible();
    await expect(page.getByText("Posé au sol")).toBeVisible();
    await expect(page.getByText(/^\+ 7 autres vérifications réussies$/)).toBeVisible();
    const guide = page.getByRole("group", { name: "Regarde l'objet en 3 questions" });
    for (const q of ["Ressemble-t-il à ton image ?", "Tourne-le : tout est bien de chaque côté ?", "La taille te paraît juste ?"]) {
      await guide.getByRole("group", { name: q }).getByRole("button", { name: "Oui" }).click();
    }
    await expect(guide.getByText(/Tout te paraît bon/)).toBeVisible();

    // Garder : le serveur range l'objet, une notification propose d'annuler, l'objet suivant s'ouvre.
    await page.getByRole("region", { name: "Amphore" }).getByRole("button", { name: /^✓ Garder dans/ }).click();
    await expect(page.getByRole("status")).toContainText("Amphore gardé dans Validation e2e");
    await expect(page.getByRole("heading", { level: 2, name: "Caisse ferrée" })).toBeVisible();
    expect(await etat()).toEqual(["Amphore:garde", "Caisse ferrée:a_valider", "Lanterne:en_fabrication"]);
    await page.getByRole("status").getByRole("button", { name: "Annuler" }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Amphore" })).toBeVisible();
    expect(await etat()).toEqual(["Amphore:a_valider", "Caisse ferrée:a_valider", "Lanterne:en_fabrication"]);

    // Objet à regarder : le défaut passe en premier.
    await page.getByRole("button", { name: "Caisse ferrée" }).click();
    await expect(page.getByText("À regarder avant de garder")).toBeVisible();
    await expect(page.locator(".verdict__raisons li").first()).toContainText("Des surfaces sont à l'envers (12 faces inversées)");

    // Jeter avec un motif.
    const caisse = page.getByRole("region", { name: "Caisse ferrée" });
    await caisse.getByRole("button", { name: "Jeter cet objet" }).click();
    await caisse.getByRole("button", { name: "Proportions" }).click();
    await caisse.getByRole("button", { name: "Jeter l'objet" }).click();
    await expect.poll(etat).toContain("Caisse ferrée:jete");
    await expect(page.getByRole("status")).toContainText("Caisse ferrée jeté");
    await page.getByRole("status").getByRole("button", { name: "Annuler" }).click();
    await expect.poll(etat).toContain("Caisse ferrée:a_valider");
    // Depuis la file, un objet décidé se rouvre aussi : « Revenir sur ma décision ».
    await page.getByRole("button", { name: "Amphore", exact: true }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Amphore" })).toBeVisible();
    await page.getByRole("region", { name: "Amphore" }).getByRole("button", { name: /^✓ Garder dans/ }).click();
    await expect.poll(etat).toContain("Amphore:garde");
    await page.getByRole("button", { name: "Amphore : Gardé" }).click();
    await expect(page.getByRole("button", { name: "Revenir sur ma décision" })).toBeVisible();
    await page.getByRole("button", { name: "Revenir sur ma décision" }).click();
    await expect.poll(etat).toContain("Amphore:a_valider");
    await page.getByRole("button", { name: "Caisse ferrée" }).click();

    // Refaire : l'objet retourne au Look, sans rien dépenser.
    await page.getByRole("region", { name: "Caisse ferrée" }).getByRole("button", { name: "Refaire" }).click();
    await page.getByRole("button", { name: "Revenir au Look" }).click();
    await expect(page.getByRole("status")).toContainText("Caisse ferrée retourne au Look");
    await expect.poll(etat).toContain("Caisse ferrée:look");
    await page.getByRole("status").getByRole("link", { name: "Ouvrir le Look" }).click();
    await expect(page).toHaveURL(new RegExp(`/lots/${p.lot_id}/references$`));
  });

  test("corriger : les remarques partent, de nouveaux looks sont demandés au worker (Meshy simulé)", async ({ page, request }) => {
    const p = semerValidation("Correction e2e");
    await page.goto(`/lots/${p.lot_id}/revue`);
    const amphore = page.getByRole("region", { name: "Amphore" });
    await amphore.getByRole("button", { name: "Corriger" }).click();
    await expect(page.getByText(/4 nouveaux looks en tenant compte de tes remarques/)).toContainText("12 crédits");
    const envoyer = page.getByRole("button", { name: "Redessiner les looks" });
    await expect(envoyer).toBeDisabled();
    await page.getByLabel("Tes remarques").fill("terre cuite plus claire");
    await envoyer.click();
    await expect(page.getByRole("status")).toContainText("4 nouveaux looks arrivent, avec tes remarques");
    // Le serveur a repris l'objet au Look avec une consigne qui contient les remarques, et une tâche d'images est en file.
    await expect
      .poll(async () => {
        const g = (await (await request.get(`/api/lots/${p.lot_id}/references`)).json()) as { objets: Array<{ nom: string; consigne: string }> };
        return g.objets.find((o) => o.nom === "Amphore")?.consigne ?? "";
      })
      .toContain("terre cuite plus claire");
  });
});
