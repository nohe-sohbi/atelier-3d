/* Lance et arrête `python dev.py` pour les tests bout en bout. Rien ne touche la vraie base ni la
   vraie config : ATELIER_DB, ATELIER_CONFIG et ATELIER_LOTS pointent dans un dossier temporaire. */
import { spawn, type ChildProcess } from "node:child_process";
import { copyFileSync, cpSync, existsSync, mkdirSync, mkdtempSync, openSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const RACINE = resolve(fileURLToPath(new URL("../..", import.meta.url)));
export const ADRESSE = "http://127.0.0.1:5173";
const ETAT = join(RACINE, "web", "test-results", "serveur-e2e.json");

interface Etat {
  pid: number;
  dossier: string;
  journal: string;
}

function python(): string {
  const venv = process.platform === "win32" ? join(RACINE, ".venv", "Scripts", "python.exe") : join(RACINE, ".venv", "bin", "python");
  return existsSync(venv) ? venv : "python";
}

async function attendre(url: string, delaiMs: number): Promise<boolean> {
  const limite = Date.now() + delaiMs;
  while (Date.now() < limite) {
    try {
      const r = await fetch(url);
      if (r.ok) return true;
    } catch {
      /* pas encore prêt */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

export async function demarrer(): Promise<void> {
  const dossier = mkdtempSync(join(tmpdir(), "atelier-e2e-"));
  mkdirSync(join(dossier, "lots"));
  // Les styles créés par les tests vont dans un dossier temporaire ; le style pilote du dépôt y est copié.
  cpSync(join(RACINE, "style", "rome-stylise-v0"), join(dossier, "style", "rome-stylise-v0"), { recursive: true });
  const journal = join(dossier, "dev.log");
  const sortie = openSync(journal, "a");
  const env = {
    ...process.env,
    ATELIER_DB: join(dossier, "atelier.db"),
    ATELIER_CONFIG: join(dossier, "config.local.yaml"),
    ATELIER_LOTS: join(dossier, "lots"),
    ATELIER_STYLES: join(dossier, "style"),
    ATELIER_DEV_SANS_VENV: "1",
  };
  const proc: ChildProcess = spawn(python(), ["dev.py", "--sans-navigateur", "--sans-couleur"], {
    cwd: RACINE,
    env,
    stdio: ["ignore", sortie, sortie],
    detached: process.platform !== "win32",
  });
  if (!proc.pid) throw new Error("dev.py ne démarre pas");
  mkdirSync(join(RACINE, "web", "test-results"), { recursive: true });
  const etat: Etat = { pid: proc.pid, dossier, journal };
  writeFileSync(ETAT, JSON.stringify(etat));
  // /api/sante à travers le proxy Vite : 200 seulement quand Vite ET l'API répondent.
  if (!(await attendre(`${ADRESSE}/api/sante`, 90_000))) {
    const log = existsSync(journal) ? readFileSync(journal, "utf8") : "(pas de journal)";
    await arreter();
    throw new Error(`l'application ne répond pas sur ${ADRESSE}/api/sante\n--- dev.log ---\n${log}`);
  }
}

function vivant(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

export async function arreter(): Promise<void> {
  if (!existsSync(ETAT)) return;
  const etat = JSON.parse(readFileSync(ETAT, "utf8")) as Etat;
  if (vivant(etat.pid)) {
    if (process.platform === "win32") {
      spawn("taskkill", ["/PID", String(etat.pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      process.kill(etat.pid, "SIGINT"); // même chemin que Ctrl+C : dev.py arrête l'API et Vite
    }
    const limite = Date.now() + 30_000;
    while (vivant(etat.pid) && Date.now() < limite) await new Promise((r) => setTimeout(r, 250));
    if (vivant(etat.pid)) process.kill(etat.pid, "SIGKILL");
  }
  // Le journal de dev.py est gardé pour le diagnostic ; le reste du dossier temporaire est effacé.
  if (existsSync(etat.journal)) copyFileSync(etat.journal, join(RACINE, "web", "test-results", "dev.log"));
  rmSync(ETAT, { force: true });
  rmSync(etat.dossier, { recursive: true, force: true });
}
