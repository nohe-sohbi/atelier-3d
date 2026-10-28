import { useEffect, useState } from "react";
import { api, messageErreur } from "../../api/client";
import type { DemandeClaudeCode as Demande, ObjetLot } from "../../api/types";
import { Chargement, Erreur } from "../../components/Etats";
import { Fenetre } from "../../components/Fenetre";

interface Props {
  lotId: number;
  /** L'objet « À créer » dont on prépare la demande ; null : fenêtre fermée. */
  objet: ObjetLot | null;
  onFermer: () => void;
  /** L'objet est passé en voie IA : le Brief se relit. */
  onVoieChangee: () => void;
}

function texteEtat(d: Demande): string {
  if (d.etat === "script_detecte") return `${d.script_attendu} est là : l'objet passe en voie code. ${d.tests.raison}.`;
  if (d.etat === "ecrite") {
    return (
      `En attente de ${d.script_attendu}. L'app regarde le dossier des générateurs toutes les 30 s : dès que le script apparaît, ` +
      `l'objet rejoint le projet en voie code. ${d.tests.raison}.`
    );
  }
  return `Une fois la demande écrite, l'app attend ${d.script_attendu} et reprend l'objet toute seule.`;
}

/** Fenêtre « Demande pour Claude Code » (ClaudeRequest.dc.html) : l'app écrit la demande, Claude Code écrit le script. */
export function DemandeClaudeCode({ lotId, objet, onFermer, onVoieChangee }: Props) {
  const [demande, setDemande] = useState<Demande | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [copie, setCopie] = useState(false);
  const [occupe, setOccupe] = useState(false);

  useEffect(() => {
    if (!objet) return;
    setDemande(null);
    setErreur(null);
    setCopie(false);
    api<Demande>(`/lots/${lotId}/objets/${objet.id}/demande`)
      .then(setDemande)
      .catch((e) => setErreur(messageErreur(e)));
  }, [lotId, objet]);

  const copier = async () => {
    if (!demande) return;
    try {
      await navigator.clipboard.writeText(demande.texte_a_coller);
      setCopie(true);
    } catch {
      setErreur("Copie impossible ici : sélectionne le texte et copie-le à la main.");
    }
  };

  const ecrire = async () => {
    if (!objet) return;
    setOccupe(true);
    try {
      setDemande(await api<Demande>(`/lots/${lotId}/objets/${objet.id}/demande`, { method: "POST" }));
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  const passerEnIA = async () => {
    if (!objet) return;
    setOccupe(true);
    try {
      await api(`/lots/${lotId}/objets/${objet.id}`, { method: "PATCH", body: JSON.stringify({ voie: "ia" }) });
      onVoieChangee();
      onFermer();
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  return (
    <Fenetre ouverte={objet !== null} titre={`Demande pour Claude Code · ${objet?.nom ?? ""}`} onFermer={onFermer}>
      <p className="fenetre-lot__sous-titre">
        Aucun générateur code ne sait fabriquer ce type d'objet. L'app prépare la demande ; Claude Code écrit le script dans ton dépôt.
      </p>
      <div className="fenetre-lot__corps">
        {erreur ? <Erreur message={erreur} /> : null}
        {!demande && !erreur ? <Chargement /> : null}
        {demande ? (
          <>
            <div className="demande__fichier">
              <span className="mono">{demande.chemin_md}</span>
              <span className={`pastille ${demande.etat === "a_ecrire" ? "pastille--neutre" : "pastille--succes"}`}>{demande.libelle_etat}</span>
            </div>
            <pre className="demande__md">{demande.markdown}</pre>
            <div className="demande__bloc">
              <span className="demande__legende" id="demande-coller">
                Texte à coller dans Claude Code
              </span>
              <p className="demande__coller mono" aria-labelledby="demande-coller">
                {demande.texte_a_coller}
              </p>
            </div>
            <div role="status" className={`demande__etat demande__etat--${demande.etat}`}>
              <span aria-hidden="true" className="demande__point" />
              <span>{texteEtat(demande)}</span>
            </div>
          </>
        ) : null}
      </div>
      <div className="fenetre-lot__pied">
        <button type="button" className="fenetre-lot__lien" onClick={passerEnIA} disabled={occupe}>
          Passer en voie IA à la place
        </button>
        <span className="fenetre-lot__espace" />
        <button type="button" className="bouton" onClick={copier} disabled={!demande}>
          {copie ? "Texte copié" : "Copier le texte"}
        </button>
        <button type="button" className="bouton bouton--primaire" onClick={ecrire} disabled={!demande || demande.etat !== "a_ecrire" || occupe}>
          {demande && demande.etat !== "a_ecrire" ? "Demande écrite" : "Écrire dans le dépôt"}
        </button>
      </div>
    </Fenetre>
  );
}
