import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import type { EnTeteLot } from "../../api/types";
import { Chargement, Erreur } from "../../components/Etats";
import { CLES_ETAPES } from "./commun";

/** /lots/nouveau : crée un lot vide (POST /api/lots), puis ouvre son Brief à la place de cette page. */
export function NouveauLot() {
  const naviguer = useNavigate();
  const [erreur, setErreur] = useState<string | null>(null);
  const lance = useRef(false);

  const creer = useCallback(async () => {
    setErreur(null);
    try {
      const lot = await api<EnTeteLot>("/lots", { method: "POST", body: JSON.stringify({}) });
      signalerChangement();
      naviguer(`/lots/${lot.id}/brief`, { replace: true });
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, [naviguer]);

  useEffect(() => {
    // Une seule création, même quand React rejoue l'effet (mode strict en développement).
    if (lance.current) return;
    lance.current = true;
    creer();
  }, [creer]);

  return (
    <>
      <h1 className="page-titre">Nouveau lot</h1>
      {erreur ? <Erreur message={erreur} onReessayer={creer} /> : <Chargement texte="Création du lot…" />}
    </>
  );
}

/** /lots/:id : ouvre le lot sur l'étape où il en est (la recherche globale y mène). */
export function OuvrirLot() {
  const { id } = useParams();
  const [cible, setCible] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    api<EnTeteLot>(`/lots/${id}`)
      .then((lot) => setCible(`/lots/${lot.id}/${CLES_ETAPES[Math.min(lot.etape_courante, 4) - 1]}`))
      .catch((e) => setErreur(messageErreur(e)));
  }, [id]);

  if (cible) return <Navigate to={cible} replace />;
  return (
    <>
      <h1 className="page-titre">Lot</h1>
      {erreur ? <Erreur message={erreur} /> : <Chargement />}
    </>
  );
}
