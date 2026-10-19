/* Signal interne « quelque chose a changé » : le menu (badges, jauge) et la cloche se rechargent.
   Émis après une tâche finie, une validation, un enregistrement. En plus, ils se relisent toutes les 15 s :
   le worker travaille sans l'écran (une liste proposée, une tâche en échec arrivent toutes seules). */
const EVENEMENT = "atelier:changement";
export const PERIODE_MS = 15_000;

export function signalerChangement(): void {
  window.dispatchEvent(new Event(EVENEMENT));
}

export function surChangement(cb: () => void): () => void {
  window.addEventListener(EVENEMENT, cb);
  return () => window.removeEventListener(EVENEMENT, cb);
}

/** surChangement, plus une relecture toutes les PERIODE_MS (onglet visible seulement). */
export function surChangementEtPeriodique(cb: () => void): () => void {
  const arreter = surChangement(cb);
  const minuteur = window.setInterval(() => {
    if (document.visibilityState !== "hidden") cb();
  }, PERIODE_MS);
  return () => {
    arreter();
    window.clearInterval(minuteur);
  };
}
