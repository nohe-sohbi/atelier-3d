// @vitest-environment node
/* Les couleurs viennent de la maquette, et les polices sont servies en local : deux règles vérifiées ici. */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const RACINE = join(__dirname, "..", "..", "..");
const MAQUETTE = join(RACINE, "docs", "maquette");

describe("tokens.css", () => {
  it("n'utilise que des couleurs présentes dans la maquette (docs/maquette)", () => {
    const tokens = readFileSync(join(__dirname, "tokens.css"), "utf8");
    const couleurs = [...tokens.matchAll(/#[0-9a-fA-F]{6}\b/g)].map((m) => m[0].toLowerCase());
    expect(couleurs.length).toBeGreaterThan(10);
    const maquette = readdirSync(MAQUETTE)
      .filter((f) => f.endsWith(".dc.html") || f.endsWith(".md"))
      .map((f) => readFileSync(join(MAQUETTE, f), "utf8").toLowerCase())
      .join("\n");
    const absentes = [...new Set(couleurs)].filter((c) => !maquette.includes(c));
    expect(absentes).toEqual([]);
  });
});

describe("index.html", () => {
  it("ne charge rien depuis Google Fonts : IBM Plex est servie en local", () => {
    const html = readFileSync(join(RACINE, "web", "index.html"), "utf8");
    expect(html).not.toMatch(/googleapis|gstatic/);
  });
});
