import { expect, test } from "./garde-fous";

interface Objet {
  id: number;
  voie: string;
  retire: boolean;
}

/** Une petite image PNG valide (16 × 16, terre cuite), comme une photo qu'on déposerait. */
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGUlEQVR4nGPcGqHHQApgIkn1qIZRDUNKAwD2/gFbGUJzIQAAAABJRU5ErkJggg==",
  "base64",
);

test.describe("Étape 6 · Références", () => {
  test("du Brief à la Génération : 4 images par objet, ta consigne, ton image, un choix par objet, lancer", async ({ page, request }) => {
    // Une liste simulée, tout en voie IA (la config de test n'a pas Blender) : comme si Claude l'avait proposée.
    const lot = (await (await request.post("/api/lots", { data: { theme: "Thème références", besoin: "Des contenants et du mobilier." } })).json()) as {
      id: number;
    };
    const { tache_id } = (await (await request.post(`/api/lots/${lot.id}/proposition`)).json()) as { tache_id: number };
    await expect.poll(async () => ((await (await request.get(`/api/taches/${tache_id}`)).json()) as { etat: string }).etat, { timeout: 30_000 }).toBe("terminee");
    const objets = ((await (await request.get(`/api/lots/${lot.id}/objets`)).json()) as { objets: Objet[] }).objets;
    for (const o of objets) {
      if (!o.retire && (o.voie === "code" || o.voie === "a_creer")) await request.patch(`/api/lots/${lot.id}/objets/${o.id}`, { data: { voie: "ia" } });
    }

    // Brief → « Générer les références » : l'onglet Références s'ouvre, les images arrivent seules.
    await page.goto(`/lots/${lot.id}/brief`);
    await page.getByRole("button", { name: "Générer les références" }).click();
    await expect(page).toHaveURL(new RegExp(`/lots/${lot.id}/references$`));
    await expect(page.getByRole("heading", { name: "Choisis une référence par objet" })).toBeVisible();
    const cartes = page.locator(".references__carte");
    const n = await cartes.count();
    expect(n).toBeGreaterThanOrEqual(2);
    for (let i = 0; i < n; i++) {
      await expect(cartes.nth(i).getByRole("button", { name: /^Image \d sur 4 pour/ })).toHaveCount(4, { timeout: 30_000 });
    }
    // Les images se chargent vraiment (simulées, marquées comme telles).
    const premiere = cartes.nth(0).getByRole("button", { name: /^Image 1 sur 4 pour/ }).locator("img");
    await expect.poll(async () => premiere.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
    await expect(cartes.nth(0).getByText("simulé").first()).toBeVisible();
    // La cloche annonce « Références prêtes ».
    await expect(page.getByRole("button", { name: /Notifications : \d+ nouvelles?/ })).toBeVisible();

    // Objet 1 : ta consigne, puis 4 nouvelles images qui la suivent ; on en choisit une.
    const un = cartes.nth(0);
    await un.getByRole("button", { name: /^Modifier la consigne de / }).click();
    const champ = un.getByRole("textbox", { name: "Consigne envoyée à l'IA" });
    await expect(champ).not.toHaveValue("");
    await champ.fill("Tonneau cerclé de fer, bois sombre, vue trois-quarts.");
    await un.getByRole("button", { name: /Refaire 4 images avec cette consigne/ }).click();
    await expect(un.getByRole("textbox")).toHaveCount(0);
    await expect(un.getByRole("button", { name: /^Image \d sur 4 pour/ })).toHaveCount(4, { timeout: 30_000 });
    await un.getByRole("button", { name: /^Image 3 sur 4 pour/ }).click();
    await expect(un.getByRole("button", { name: /^Image 3 sur 4 pour/ })).toHaveAttribute("aria-pressed", "true");

    // Objet 2 : ton image, choisie d'office.
    const deux = cartes.nth(1);
    await deux.getByLabel(/^Choisir ton image pour /).setInputFiles({ name: "croquis.png", mimeType: "image/png", buffer: PNG });
    await expect(deux.getByRole("button", { name: /^Ton image pour / })).toHaveAttribute("aria-pressed", "true");
    await expect(deux.getByRole("button", { name: /4 images d'après ton image/ })).toBeVisible();

    // Lancer : les autres objets sont annoncés mis de côté, puis Génération montre tes 2 objets partis vers Meshy.
    if (n > 2) await expect(page.getByText(/mis de côté/)).toBeVisible();
    await page.getByRole("button", { name: "Lancer la génération 3D" }).click();
    await expect(page).toHaveURL(new RegExp(`/lots/${lot.id}/generation$`));
    await expect(page.getByText("Objet 3D par IA (Meshy)").first()).toBeVisible(); // ton image part à Meshy
    await expect(page.getByRole("link", { name: /Génération/ }).first()).toBeVisible();
  });
});
