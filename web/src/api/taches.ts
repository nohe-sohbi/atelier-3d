import { api } from "./client";
import type { Tache } from "./types";

/** Interroge GET /api/taches/{id} jusqu'à un état final ; `surAvancement` reçoit chaque lecture. */
export async function attendreTache(
  tacheId: number,
  surAvancement?: (t: Tache) => void,
  options: { intervalleMs?: number; maxLectures?: number } = {},
): Promise<Tache> {
  const intervalle = options.intervalleMs ?? 1000;
  const max = options.maxLectures ?? 600;
  for (let i = 0; i < max; i += 1) {
    const t = await api<Tache>(`/taches/${tacheId}`);
    surAvancement?.(t);
    if (t.etat === "terminee" || t.etat === "echouee" || t.etat === "annulee") return t;
    await new Promise((r) => setTimeout(r, intervalle));
  }
  throw new Error("la tâche ne finit pas");
}
