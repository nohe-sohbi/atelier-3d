import { expect, test } from "./garde-fous";

test.describe("Étape 4 · File de tâches et Génération", () => {
  test("le worker de dev.py se signale ; la proposition du lot apparaît avec son journal ; Réglages montre la file et la dépense", async ({ page, request }) => {
    // Un lot et sa proposition simulée, lancés par l'API comme le ferait le Brief.
    const lot = (await (await request.post("/api/lots", { data: { theme: "Thème file", besoin: "Quelques contenants." } })).json()) as { id: number };
    const { tache_id } = (await (await request.post(`/api/lots/${lot.id}/proposition`)).json()) as { tache_id: number };
    await expect.poll(async () => ((await (await request.get(`/api/taches/${tache_id}`)).json()) as { etat: string }).etat, { timeout: 30_000 }).toBe("terminee");

    await page.goto(`/lots/${lot.id}/generation`);
    await expect(page.getByText(/Worker actif/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "File du projet" })).toBeVisible();
    await expect(page.getByText("Proposition de la liste par Claude")).toBeVisible();
    await expect(page.getByText("Terminée")).toBeVisible();
    await page.getByRole("button", { name: "Journal : Proposition de la liste par Claude" }).click();
    const journal = page.getByRole("list", { name: `Journal de la tâche ${tache_id}` });
    await expect(journal.getByText(/Tâche proposer_liste terminée/)).toBeVisible();

    await page.goto("/reglages");
    await expect(page.getByText(/Rien dépensé ce mois · \d+ appels? simulés?, gratuits/)).toBeVisible();
    const file = page.locator(".reglages__file");
    await expect(file.getByText(/Worker actif/)).toBeVisible();
    await expect(file.getByRole("link", { name: /Lot / }).first()).toBeVisible();
  });
});
