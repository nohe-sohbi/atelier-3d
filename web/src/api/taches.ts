import { api } from "./client";
import type { Tache } from "./types";

/** Levée quand l'écran qui attendait la tâche est quitté : la tâche, elle, continue dans le worker. */
export class AttenteAbandonnee extends Error {
  constructor() {
    super("attente abandonnée");
    this.name = "AttenteAbandonnee";
  }
}

/** Au-delà, l'écran dit que la tâche attend le worker (un worker lancé la prend en moins d'une seconde). */
export const ATTENTE_WORKER_MS = 2000;

function pause(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resoudre, rejeter) => {
    const minuteur = setTimeout(resoudre, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(minuteur);
        rejeter(new AttenteAbandonnee());
      },
      { once: true },
    );
  });
}

/** Interroge GET /api/taches/{id} jusqu'à un état final. `surAvancement` reçoit chaque lecture et depuis combien
 *  de temps la tâche est en attente (0 sinon). `signal` arrête l'interrogation (AttenteAbandonnee). */
export async function attendreTache(
  tacheId: number,
  surAvancement?: (t: Tache, enAttenteDepuisMs: number) => void,
  options: { intervalleMs?: number; maxLectures?: number; signal?: AbortSignal } = {},
): Promise<Tache> {
  const { signal } = options;
  const intervalle = options.intervalleMs ?? 1000;
  const max = options.maxLectures ?? 600;
  let debutAttente: number | null = null;
  for (let i = 0; i < max; i += 1) {
    if (signal?.aborted) throw new AttenteAbandonnee();
    let t: Tache;
    try {
      t = await api<Tache>(`/taches/${tacheId}`, { signal });
    } catch (e) {
      if (signal?.aborted) throw new AttenteAbandonnee();
      throw e;
    }
    debutAttente = t.etat === "en_attente" ? (debutAttente ?? Date.now()) : null;
    surAvancement?.(t, debutAttente === null ? 0 : Date.now() - debutAttente);
    if (t.etat === "terminee" || t.etat === "echouee" || t.etat === "annulee") return t;
    await pause(intervalle, signal);
  }
  throw new Error("la tâche ne finit pas");
}
