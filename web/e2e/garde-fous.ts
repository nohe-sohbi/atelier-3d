import { expect, test as base, type Page } from "@playwright/test";

/* Sur chaque page : aucune erreur de console ni d'exception, et aucune requête hors de la machine
   (polices locales, pas de Google Fonts). Vérifié à la fin de chaque test. */
export const test = base.extend<{ page: Page }>({
  page: async ({ page }, utiliser) => {
    const erreurs: string[] = [];
    const externes: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error") erreurs.push(m.text());
    });
    page.on("pageerror", (e) => erreurs.push(`pageerror: ${e.message}`));
    page.on("request", (r) => {
      const hote = new URL(r.url()).hostname;
      if (!["127.0.0.1", "localhost"].includes(hote)) externes.push(r.url());
    });
    await utiliser(page);
    expect(erreurs, "erreurs de console").toEqual([]);
    expect(externes, "requêtes hors de la machine").toEqual([]);
  },
});

export { expect };
