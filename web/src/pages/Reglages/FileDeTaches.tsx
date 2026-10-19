import { useCallback, useEffect, useState } from "react";
import { api, messageErreur } from "../../api/client";
import { surChangementEtPeriodique } from "../../api/rafraichissement";
import type { TachesRecentes } from "../../api/types";
import { Erreur } from "../../components/Etats";
import { EtatDuWorker, ListeTaches } from "../../components/Taches";

/** Réglages · File de tâches : le worker tourne-t-il, et les tâches actives ou récentes, tous lots et styles confondus. */
export function FileDeTaches() {
  const [donnees, setDonnees] = useState<TachesRecentes | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    api<TachesRecentes>("/worker/taches")
      .then((d) => {
        setDonnees(d);
        setErreur(null);
      })
      .catch((e) => setErreur(messageErreur(e)));
  }, []);

  useEffect(() => {
    charger();
    return surChangementEtPeriodique(charger);
  }, [charger]);

  if (erreur) return <Erreur message={erreur} onReessayer={charger} />;
  if (!donnees) return null;
  return (
    <div className="reglages__file">
      <EtatDuWorker worker={donnees.worker} />
      <h3 className="reglages__h3">Tâches récentes</h3>
      <ListeTaches taches={donnees.taches} onChangement={charger} vide="Aucune tâche pour l'instant : elles apparaissent ici dès qu'un lot ou un style en lance." />
    </div>
  );
}
