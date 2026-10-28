#!/usr/bin/env node
/*
 * Compare la maquette (docs/maquette) et l'app réelle, écran par écran.
 *
 *   node web/outils/comparer-maquette.mjs [--app http://127.0.0.1:5173] [--ecran validation] [--sans-captures]
 *
 * Pour chaque écran, à 390, 768 et 1440 px, en clair et en sombre :
 *   - deux captures (maquette, app), rangées côte à côte dans une page : web/public/comparaison/index.html ;
 *   - la différence de structure : titres, boutons, champs et libellés d'onglets présents dans la maquette et absents de
 *     l'app, et l'inverse (rapport.md et rapport.json).
 * Les onglets, <details> et menus connus sont parcourus pour que leur contenu compte. La police et three.js, que la maquette
 * charge depuis internet, sont servis depuis node_modules : l'outil marche hors ligne.
 * Les noms de données d'exemple (Camp romain…) sont ignorés : on compare la structure, pas les valeurs.
 */
import { chromium } from "playwright";
import { mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ICI = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(ICI, "..");
const SORTIE = join(WEB, "public", "comparaison");
const arg = (nom, defaut) => {
  const i = process.argv.indexOf(`--${nom}`);
  return i === -1 ? defaut : (process.argv[i + 1]?.startsWith("--") || process.argv[i + 1] === undefined ? true : process.argv[i + 1]);
};
const APP = String(arg("app", "http://127.0.0.1:5173")).replace(/\/$/, "");
const SEUL = arg("ecran", null);
const SANS_CAPTURES = arg("sans-captures", false) === true;

const TAILLES = [
  { nom: "390", largeur: 390, hauteur: 844, tactile: true },
  { nom: "768", largeur: 768, hauteur: 1024, tactile: true },
  { nom: "1440", largeur: 1440, hauteur: 900, tactile: false },
];
const THEMES = ["clair", "sombre"];

/** Données d'exemple de la maquette : ne comptent pas dans la comparaison de structure. */
const IGNORER = [/camp romain|donjon|station orbitale|temple de kyoto|port de p[eê]che|rome antique|m[eé]di[eé]val|fantasy|sci-?fi|post-?apo|japon/i,
  /amphore|bouclier|caisse|tonneau|lanterne|filet|jarre|ancre|pilier|scutum|gladius|colonne|coffre|objet simul/i, /\b\d+\b/];

const normaliser = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

async function idProjetDemo(nom) {
  try {
    const lots = (await (await fetch(`${APP}/api/lots`)).json()).lots;
    return lots.find((l) => normaliser(l.nom).includes(normaliser(nom)))?.id ?? lots[0]?.id ?? 1;
  } catch {
    return 1;
  }
}

async function ecrans() {
  const demo = await idProjetDemo("demo validation");
  const projet = await idProjetDemo("demo validation");
  return [
    { cle: "accueil", nom: "Créer", maquette: "accueil", app: "/" },
    { cle: "objets", nom: "Objets", maquette: "objets", app: `/lots/${projet}/brief` },
    { cle: "look", nom: "Look", maquette: "look", app: `/lots/${projet}/references` },
    { cle: "fabrication", nom: "Fabrication", maquette: "fabrication", app: `/lots/${projet}/generation` },
    { cle: "validation", nom: "Validation", maquette: "validation", app: `/lots/${demo}/revue`, attente: 4500 },
    { cle: "essai", nom: "Essai", maquette: "essai", app: `/lots/${demo}/essai`, attente: 4500 },
    { cle: "jeu", nom: "Jeu", maquette: "jeu", app: `/lots/${demo}/jeu` },
    { cle: "projets", nom: "Projets", maquette: "projets", app: "/lots" },
    { cle: "bibliotheque", nom: "Bibliothèque", maquette: "bibliotheque", app: "/bibliotheque" },
    { cle: "fiche", nom: "Fiche objet", maquette: "fiche", app: "/assets/ROM_PROP_Amphore_D", attente: 3000 },
    { cle: "styles", nom: "Styles", maquette: "styles", app: "/styles" },
    { cle: "style", nom: "Style (détail)", maquette: "style", app: "/styles" },
    { cle: "nouveau-style", nom: "Nouveau style", maquette: "nouveau-style", app: "/styles" },
    { cle: "reglages", nom: "Réglages", maquette: "reglages", app: "/reglages" },
  ];
}

/** Ouvre les <details> et parcourt les onglets, puis lit les titres, actions, champs et onglets visibles. */
async function lireStructure(page) {
  await page.evaluate(() => document.querySelectorAll("details:not([open])").forEach((d) => (d.open = true)));
  const lire = () =>
    page.evaluate(() => {
      const vis = (e) => { const r = e.getBoundingClientRect(); const c = getComputedStyle(e); return r.width > 0 && r.height > 0 && c.visibility !== "hidden" && c.display !== "none"; };
      const racine = document.querySelector(".ecran.actif") || document.querySelector("main") || document.body;
      const txt = (e) => (e.innerText || e.getAttribute("aria-label") || e.getAttribute("title") || "").trim().replace(/\s+/g, " ");
      const dans = (sel) => [...racine.querySelectorAll(sel)].filter(vis).map(txt).filter((t) => t && t.length < 90);
      return {
        titres: dans("h1,h2,h3,legend"),
        actions: dans("button,a.btn,a.bouton,[role=tab],summary,.onglets button"),
        champs: [...dans("label"), ...[...racine.querySelectorAll("input[placeholder],textarea[placeholder]")].filter(vis).map((e) => e.placeholder)],
      };
    });
  const base = await lire();
  const onglets = await page.locator('.ecran.actif [role=tab], .ecran.actif .onglets button, main [role=tab]').all();
  for (const o of onglets) {
    try {
      if (!(await o.isVisible())) continue;
      await o.click({ timeout: 1000 });
      await page.waitForTimeout(150);
      const plus = await lire();
      for (const k of Object.keys(base)) base[k] = [...new Set([...base[k], ...plus[k]])];
    } catch { /* un onglet qui ne s'ouvre pas ne bloque pas la comparaison */ }
  }
  return base;
}

function difference(maquette, app) {
  const ignore = (t) => IGNORER.some((r) => r.test(t));
  const tous = (s) => normaliser(Object.values(s).flat().join(" | "));
  const dansApp = tous(app), dansMaquette = tous(maquette);
  const manquants = {}, enPlus = {};
  for (const k of ["titres", "actions", "champs"]) {
    manquants[k] = [...new Set(maquette[k])].filter((t) => { const n = normaliser(t); return n.length > 3 && !ignore(t) && !dansApp.includes(n); });
    enPlus[k] = [...new Set(app[k])].filter((t) => { const n = normaliser(t); return n.length > 3 && !ignore(t) && !dansMaquette.includes(n); });
  }
  return { manquants, enPlus };
}

async function preparer(ctx) {
  const local = (p) => join(WEB, "node_modules", p);
  const routes = {
    "https://fonts.googleapis.com/**": (r) => r.fulfill({ contentType: "text/css", body: [400, 500, 600, 700].map((w) => `@font-face{font-family:Inter;font-weight:${w};src:url(https://polices.local/${w}.woff2) format("woff2")}`).join("") }),
    "https://polices.local/**": (r) => { const w = r.request().url().match(/(\d+)\.woff2/)?.[1] ?? "400"; return r.fulfill({ path: local(`@fontsource/inter/files/inter-latin-${w}-normal.woff2`), contentType: "font/woff2" }); },
    "https://fonts.gstatic.com/**": (r) => r.abort(),
    "https://unpkg.com/three@*/**": (r) => {
      const chemin = new URL(r.request().url()).pathname.replace(/^\/three@[^/]+\//, "");
      const f = local(`three/${chemin}`);
      return existsSync(f) ? r.fulfill({ path: f, contentType: "text/javascript" }) : r.abort();
    },
  };
  for (const [motif, gestion] of Object.entries(routes)) await ctx.route(motif, gestion);
}

async function photographier(browser, taille, theme, cible, fichier, attente) {
  const ctx = await browser.newContext({ viewport: { width: taille.largeur, height: taille.hauteur }, hasTouch: taille.tactile, isMobile: taille.largeur < 500, deviceScaleFactor: 1 });
  await ctx.addInitScript((t) => { try { localStorage.setItem("theme-atelier", t); } catch {} }, theme);
  await preparer(ctx);
  const page = await ctx.newPage();
  await page.goto(cible);
  await page.waitForTimeout(attente);
  const structure = await lireStructure(page);
  if (!SANS_CAPTURES) await page.screenshot({ path: fichier, fullPage: false });
  await ctx.close();
  return structure;
}

const liste = await ecrans();
const choisis = SEUL ? liste.filter((e) => e.cle === SEUL) : liste;
if (!choisis.length) { console.error(`écran inconnu : ${SEUL}`); process.exit(2); }
rmSync(SORTIE, { recursive: true, force: true });
mkdirSync(SORTIE, { recursive: true });
const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
const rapport = {};
for (const e of choisis) {
  rapport[e.cle] = { nom: e.nom, tailles: {} };
  for (const t of TAILLES) {
    for (const th of THEMES) {
      const id = `${e.cle}-${t.nom}-${th}`;
      const attente = e.attente ?? 1800;
      const m = await photographier(browser, t, th, `${APP}/proposition/index.html#${e.maquette}`, join(SORTIE, `${id}-maquette.png`), attente);
      const a = await photographier(browser, t, th, `${APP}${e.app}`, join(SORTIE, `${id}-app.png`), attente + 700);
      // La structure se compare une fois par écran (1440 px, clair) : c'est l'état le plus complet.
      if (t.nom === "1440" && th === "clair") rapport[e.cle].structure = difference(m, a);
    }
  }
  const d = rapport[e.cle].structure;
  const n = d ? Object.values(d.manquants).flat().length : 0;
  console.log(`${e.nom.padEnd(16)} ${n} éléments de la maquette absents de l'app`);
}
await browser.close();

// --- rapport et page de comparaison ---
const md = ["# Comparaison maquette / app", "", `Générée par \`web/outils/comparer-maquette.mjs\` sur ${APP}.`, ""];
for (const [cle, r] of Object.entries(rapport)) {
  const d = r.structure;
  md.push(`## ${r.nom}`);
  const m = d ? Object.entries(d.manquants).flatMap(([k, v]) => v.map((x) => `- [ ] ${k.slice(0, -1)} : ${x}`)) : [];
  md.push(...(m.length ? ["Absent de l'app :", ...m] : ["Rien d'absent de la maquette."]));
  const p = d ? Object.entries(d.enPlus).flatMap(([k, v]) => v.map((x) => `- ${k.slice(0, -1)} : ${x}`)) : [];
  if (p.length) md.push("", "Dans l'app, pas dans la maquette (à décider) :", ...p);
  md.push("");
}
writeFileSync(join(SORTIE, "rapport.md"), md.join("\n"));
writeFileSync(join(SORTIE, "rapport.json"), JSON.stringify(rapport, null, 2));
const blocs = choisis.map((e) => {
  const lignes = TAILLES.map((t) => THEMES.map((th) => {
    const id = `${e.cle}-${t.nom}-${th}`;
    return `<div class="paire"><b>${t.nom} px · ${th}</b><div class="deux"><figure><figcaption>Maquette</figcaption><img loading="lazy" src="${id}-maquette.png"></figure><figure><figcaption>App</figcaption><img loading="lazy" src="${id}-app.png"></figure></div></div>`;
  }).join("")).join("");
  return `<section id="${e.cle}"><h2>${e.nom}</h2>${lignes}</section>`;
}).join("");
const menu = choisis.map((e) => `<a href="#${e.cle}">${e.nom}</a>`).join(" · ");
writeFileSync(join(SORTIE, "index.html"), `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Comparaison maquette / app</title>
<style>body{font:15px system-ui;margin:0;padding:16px;background:#f6f5f2;color:#1b1a18}nav{position:sticky;top:0;background:#f6f5f2;padding:8px 0;line-height:2}a{color:#3555d6}h2{margin:32px 0 8px}.paire{margin:14px 0}.deux{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:start}figure{margin:0}figcaption{font-size:12px;color:#6b6862}img{max-width:100%;border:1px solid #d6d2ca;border-radius:8px;background:#fff}</style>
<h1>Comparaison maquette / app</h1><p><a href="rapport.md">Rapport de structure</a> · généré le ${new Date().toLocaleString("fr-FR")}</p><nav>${menu}</nav>${blocs}`);
console.log(`\nPage : ${APP}/comparaison/index.html\nRapport : ${join(SORTIE, "rapport.md")}`);
