import { expect, test } from "./garde-fous";

interface Objet {
  id: number;
  nom: string;
  voie: string;
  type_objet: string;
  retire: boolean;
}

test.describe("Étape 5 · Fabrication par code", () => {
  test("Références puis Génération : 4 versions rendues par le vrai Blender, on en choisit une, on lance ; l'objet est prêt pour la revue", async ({ page, request }) => {
    // Blender de la machine (proposé par Réglages) ; sans Blender, ce scénario n'a pas lieu d'être.
    const reglages = (await (await request.get("/api/reglages")).json()) as { etat: { outils: { blender: { suggestion: string | null } } } } & Record<string, unknown>;
    const blender = reglages.etat.outils.blender.suggestion;
    test.skip(!blender, "Blender introuvable sur cette machine");
    const corps: Record<string, unknown> = { ...reglages };
    delete corps.etat; // l'état (présence des outils) se lit, il ne s'envoie pas
    const outils = corps.outils as { blender: { chemin: string } };
    const cheminAvant = outils.blender.chemin;
    outils.blender.chemin = blender!;
    expect((await request.put("/api/reglages", { data: corps })).ok()).toBe(true);
    // Le réglage est remis comme avant à la fin : les autres scénarios attendent la config de test (sans Blender).
    const remettre = async () => {
      outils.blender.chemin = cheminAvant;
      await request.put("/api/reglages", { data: corps });
    };
    try {
      // Un lot dont seul le scutum est gardé, brief validé (comme à l'étape 3).
      const lot = (await (await request.post("/api/lots", { data: { theme: "Thème fabrication", besoin: "Des armes de légionnaire." } })).json()) as { id: number };
      const { tache_id } = (await (await request.post(`/api/lots/${lot.id}/proposition`)).json()) as { tache_id: number };
      await expect.poll(async () => ((await (await request.get(`/api/taches/${tache_id}`)).json()) as { etat: string }).etat, { timeout: 30_000 }).toBe("terminee");
      const objets = ((await (await request.get(`/api/lots/${lot.id}/objets`)).json()) as { objets: Objet[] }).objets;
      const scutum = objets.find((o) => o.type_objet === "scutum")!;
      for (const o of objets) {
        if (o.id !== scutum.id && !o.retire) await request.patch(`/api/lots/${lot.id}/objets/${o.id}`, { data: { retenu: false } });
      }
      expect((await request.post(`/api/lots/${lot.id}/valider-brief`)).ok()).toBe(true);

      // Références : les 4 versions du générateur arrivent (Blender, gratuit) ; on choisit la 2e, puis on lance.
      await page.goto(`/lots/${lot.id}/references`);
      const carte = page.getByRole("region", { name: scutum.nom });
      await expect(carte.getByText("4 versions du générateur · gratuites")).toBeVisible();
      const versions = carte.getByRole("button", { name: /^Version \d sur 4 pour/ });
      await expect(versions).toHaveCount(4, { timeout: 120_000 });
      await versions.nth(1).click();
      await expect(versions.nth(1)).toHaveAttribute("aria-pressed", "true");
      await expect(page.getByText("1 sur 1 choisie")).toBeVisible();
      await page.getByRole("button", { name: "Lancer la génération 3D" }).click();
      await expect(page).toHaveURL(new RegExp(`/lots/${lot.id}/generation$`));
      await expect(page.getByText("Prêt pour la revue")).toBeVisible({ timeout: 180_000 });
      await expect(page.getByRole("img", { name: /^Vignette de / })).toBeVisible();
      await expect(page.getByRole("link", { name: "Voir la planche" })).toHaveAttribute("href", /\/api\/fichiers\/essais\/\d+\/planche\.png$/);
      await expect(page.getByText(/ROM_PROP_Scutum_A/)).toBeVisible();
      await expect(page.getByRole("list", { name: "Où en est la fabrication" }).getByText("/ 1")).toBeVisible();
      // Une seule notification « Revue prête » pour ce lot.
      const notifications = ((await (await request.get("/api/notifications")).json()) as { notifications: Array<{ type: string; lien: string }> }).notifications;
      expect(notifications.filter((n) => n.type === "revue_prete" && n.lien === `/lots/${lot.id}/revue`)).toHaveLength(1);
    } finally {
      await remettre();
    }
  });
});
