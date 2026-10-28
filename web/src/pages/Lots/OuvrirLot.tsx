import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import type { EnTeteLot } from "../../api/types";
import { Chargement, Erreur } from "../../components/Etats";
import { CLES_ETAPES } from "./commun";

/** /lots/:id : ouvre le projet sur l'étape où il en est (la recherche globale y mène). */
export function OuvrirLot() {
  const { id } = useParams();
  const [cible, setCible] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    api<EnTeteLot>(`/lots/${id}`)
      .then((lot) => setCible(`/lots/${lot.id}/${CLES_ETAPES[Math.min(lot.etape_courante, CLES_ETAPES.length) - 1]}`))
      .catch((e) => setErreur(messageErreur(e)));
  }, [id]);

  if (cible) return <Navigate to={cible} replace />;
  return (
    <>
      <h1 className="page-titre">Projet</h1>
      {erreur ? <Erreur message={erreur} /> : <Chargement />}
    </>
  );
}
