/* Prépare, dans la base du serveur de test, un projet avec de vrais objets fabriqués (sans lancer Blender) :
   tests/outils/projet_demo.py. Les fichiers 3D sont de vrais .glb à niveaux de détail. */
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { RACINE, dossierServeur, python } from "./serveur";

export interface ProjetSeme {
  lot_id: number;
  amphore: number;
  caisse: number;
  lanterne: number;
}

export function semerValidation(nom = "Projet de démonstration"): ProjetSeme {
  const dossier = dossierServeur();
  const r = spawnSync(python(), ["-m", "tests.outils.projet_demo", "--db", join(dossier, "atelier.db"), "--lots", join(dossier, "lots"), "--nom", nom], {
    cwd: RACINE,
    encoding: "utf8",
    env: { ...process.env, ATELIER_DEV_SANS_VENV: "1" },
  });
  if (r.status !== 0) throw new Error(`projet de démonstration impossible :\n${r.stderr}`);
  return JSON.parse(r.stdout.trim().split("\n").at(-1)!) as ProjetSeme;
}
