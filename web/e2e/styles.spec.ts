import { expect, test } from "./garde-fous";

/** Une image d'inspiration : vert forêt, bois, fer et or sur un fond blanc. */
const INSPIRATION = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAUAAAADICAIAAAAWZq/8AAACrElEQVR4nO3VsU2CURiGUSDuY0ejm2jUghWcghUslOAm2tA50XWFP+CVPMk59XeTt3ly12OMFdC0ufYA4HwChjABQ5iAIUzAECZgCBMwhAkYwgQMYQKGMAFDmIAhTMAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAEHZzyePbh+1f7fhPP5+nhZf7l7upSyZ5ff9eePn4vJu6ZJLjx9vCy9PhfuqSSbZPXwsv/cAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAECZgCBMwhAkYwgQMYQKGMAFDmIAhTMAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAECZgCBMwhAkYwgQMYQKGMAFDmIAhTMAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAECZgCBMwhAkYwgQMYQKGMAFDmIAhTMAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAECZgCBMwhAkYwgQMYQKGMAFDmIAhTMAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAECZgCBMwhAkYwgQMYQKGMAFDmIAhTMAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAECZgCBMwhAkYwtZjjGtvAM7kB4YwAUOYgCFMwBAmYAgTMIQJGMIEDGEChjABQ5iAIUzAECZgCBMwhAkYwgQMYQKGMAFDmIAhTMAQJmAIEzCECRjCBAxhAoYwAUOYgCFMwBD2C1UIE4tFbd8cAAAAAElFTkSuQmCC", "base64");

test.describe("Étape 2 · Styles", () => {
  test("le style du thème pilote est là ; un nouveau style se crée, reçoit sa planche simulée et se valide", async ({ page, request }) => {
    // La jauge part de ce que les autres scénarios ont déjà dépensé (crédits simulés) : on mesure la différence.
    const avant = ((await (await request.get("/api/menu")).json()) as { credits: { utilises: number } }).credits.utilises;
    await page.goto("/styles");
    await expect(page.getByRole("heading", { level: 1, name: "Styles" })).toBeVisible();
    const pilote = page.getByRole("button", { name: /Rome antique stylisée/ });
    await expect(pilote).toHaveAttribute("aria-pressed", "true");
    await expect(pilote.getByText("Actif")).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Rome antique stylisée" })).toBeVisible();
    await expect(page.getByText("Petit objet")).toBeVisible();
    await expect(page.getByText("Aucune image validée pour ce style")).toBeVisible();

    await page.getByRole("button", { name: "Nouveau style" }).click();
    const fenetre = page.getByRole("dialog", { name: "Nouveau style" });
    await fenetre.getByLabel("Nom", { exact: true }).fill("Style de bout en bout");
    await expect(fenetre.getByLabel("Code", { exact: true })).toHaveValue("style-de-bout-en-bout-v0");
    await fenetre.getByLabel("Description", { exact: true }).fill("Formes simples, couleurs franches.");
    await expect(fenetre.getByLabel(/^Nom de la couleur/)).toHaveCount(10); // palette reprise du style pilote
    // Une image d'inspiration : la palette en est tirée (ses 4 couleurs, pas le fond blanc), complétée à 8.
    await fenetre.getByLabel("Choisir des images d'inspiration").setInputFiles({ name: "inspiration.png", mimeType: "image/png", buffer: INSPIRATION });
    await expect(fenetre.getByText(/Tirée de ton image/)).toBeVisible();
    await expect(fenetre.getByLabel(/^Nom de la couleur/)).toHaveCount(8);
    const noms = await fenetre.getByLabel(/^Nom de la couleur/).evaluateAll((champs) => champs.map((c) => (c as HTMLInputElement).value));
    expect(noms).toEqual(expect.arrayContaining(["vert forêt", "bois", "fer", "or"]));
    await fenetre.getByRole("button", { name: /Générer la première planche/ }).click();

    // Le worker exécute la tâche Meshy simulée : 6 images, toutes marquées simulées.
    await expect(fenetre.getByText("simulé")).toHaveCount(6, { timeout: 60_000 });
    await expect(fenetre.getByText(/18 crédits dépensés/)).toBeVisible();
    await expect(fenetre.getByRole("button", { name: "Valider le style" })).toBeDisabled();
    await fenetre.getByRole("button", { name: "Garder" }).first().click();
    await expect(fenetre.getByRole("button", { name: "Gardée" })).toHaveCount(1);
    await fenetre.getByRole("button", { name: "Garder" }).first().click();
    await expect(fenetre.getByText("2 images gardées sur 6")).toBeVisible();
    await fenetre.getByRole("button", { name: "Valider le style" }).click();
    await expect(fenetre).toBeHidden();

    // Le nouveau style est ouvert, actif, avec ses 2 images gardées ; la jauge a baissé de 18 crédits (simulé).
    const nouveau = page.getByRole("button", { name: /Style de bout en bout/ });
    await expect(nouveau).toHaveAttribute("aria-pressed", "true");
    await expect(nouveau.getByText("Actif")).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Style de bout en bout" })).toBeVisible();
    await expect(page.getByRole("list", { name: "Images de la planche" }).getByRole("img")).toHaveCount(2);
    await expect(page.getByRole("progressbar", { name: "Crédits Meshy utilisés" })).toHaveAttribute("aria-valuenow", String(avant + 18));

    // Dupliquer en v1 : nouvelle version ouverte, l'ancienne reste dans la liste.
    await page.getByRole("button", { name: "Dupliquer en v1" }).click();
    await expect(page.getByRole("button", { name: /style-de-bout-en-bout-v1/ })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: /style-de-bout-en-bout-v0/ })).toBeVisible();
    await expect(page.getByText("Dupliquer en v2")).toBeVisible();
  });

  test("Modifier change la description et le budget, et l'écran le montre", async ({ page, request }) => {
    // Un style à ce scénario : une version qu'un lot utilise (créé par un autre scénario) ne se modifie plus.
    const { styles } = (await (await request.get("/api/styles")).json()) as { styles: Array<{ id: number; code: string; palette: Array<{ nom: string; hex: string }> }> };
    const pilote = styles.find((s) => s.code === "rome-stylise-v0")!;
    const r = await request.post("/api/styles", {
      data: { nom: "Style à modifier", palette: Object.fromEntries(pilote.palette.map((c) => [c.nom, c.hex])), budgets_depuis: pilote.id },
    });
    expect(r.ok()).toBe(true);
    await page.goto(`/styles?style=${((await r.json()) as { code: string }).code}`);
    await expect(page.getByRole("heading", { level: 2, name: "Style à modifier" })).toBeVisible();
    await page.getByRole("button", { name: "Modifier", exact: true }).click();
    const fenetre = page.getByRole("dialog");
    await fenetre.getByLabel("Petit objet (tris)").fill("2500");
    await fenetre.getByLabel("Description", { exact: true }).fill("Description modifiée par le test.");
    await fenetre.getByRole("button", { name: "Enregistrer" }).click();
    await expect(fenetre).toBeHidden();
    await expect(page.getByText(/2[\s\u202f\u00a0]500 tris/)).toBeVisible();
  });
});
