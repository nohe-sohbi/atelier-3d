// @vitest-environment node
/* Les couleurs viennent de la maquette, et les polices sont servies en local : deux règles vérifiées ici. */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const RACINE = join(__dirname, "..", "..", "..");
const MAQUETTE = join(RACINE, "docs", "maquette");

function fichiersCss(dossier: string): string[] {
  return readdirSync(dossier, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? fichiersCss(join(dossier, e.name)) : e.name.endsWith(".css") ? [join(dossier, e.name)] : [],
  );
}

describe("couleurs de l'interface", () => {
  const maquette = readdirSync(MAQUETTE)
    .filter((f) => f.endsWith(".dc.html") || f.endsWith(".md"))
    .map((f) => readFileSync(join(MAQUETTE, f), "utf8").toLowerCase())
    .join("\n");

  it("tokens.css n'utilise que des couleurs présentes dans la maquette (docs/maquette)", () => {
    const tokens = readFileSync(join(__dirname, "tokens.css"), "utf8");
    const couleurs = [...tokens.matchAll(/#[0-9a-fA-F]{6}\b/g)].map((m) => m[0].toLowerCase());
    expect(couleurs.length).toBeGreaterThan(10);
    expect([...new Set(couleurs)].filter((c) => !maquette.includes(c))).toEqual([]);
  });

  it("aucune autre feuille de style n'écrit une couleur en dur : tout passe par les variables", () => {
    const fautifs: string[] = [];
    for (const f of fichiersCss(join(RACINE, "web", "src"))) {
      if (f.endsWith("tokens.css")) continue;
      const css = readFileSync(f, "utf8");
      if (/#[0-9a-fA-F]{3,8}\b/.test(css) || /rgba?\(/.test(css)) fautifs.push(f.replace(RACINE, ""));
    }
    expect(fautifs).toEqual([]);
  });
});

describe("index.html", () => {
  it("ne charge rien depuis Google Fonts : IBM Plex est servie en local", () => {
    const html = readFileSync(join(RACINE, "web", "index.html"), "utf8");
    expect(html).not.toMatch(/googleapis|gstatic/);
  });
});
