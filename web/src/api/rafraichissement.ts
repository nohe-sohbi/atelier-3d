/* Signal interne « quelque chose a changé » : le menu (badges, jauge) et la cloche se rechargent.
   Émis après une tâche finie, une validation, un enregistrement. Le rafraîchissement périodique arrive
   avec la file de tâches (étape 4). */
const EVENEMENT = "atelier:changement";

export function signalerChangement(): void {
  window.dispatchEvent(new Event(EVENEMENT));
}

export function surChangement(cb: () => void): () => void {
  window.addEventListener(EVENEMENT, cb);
  return () => window.removeEventListener(EVENEMENT, cb);
}
