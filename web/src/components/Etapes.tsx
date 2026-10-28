import { Link } from "react-router-dom";
import "./Etapes.css";

export interface EtapeAffichee {
  cle: string;
  libelle: string;
  /** Petit texte à droite du libellé (« 2 à valider »). */
  detail?: string;
  /** Un lien vers l'écran de l'étape. */
  lien?: string;
  /** Faite, quand l'avancement du projet le dit ; sinon : toute étape avant la courante. */
  faite?: boolean;
  /** L'étape peut être ouverte, même si elle est à venir (le projet y est déjà arrivé). */
  atteinte?: boolean;
}

interface Props {
  etapes: EtapeAffichee[];
  /** Position de l'étape affichée, de 0 à n−1. Sans autre indication, avant elle : faites ; après : à venir. */
  courante: number;
}

/**
 * Frise des étapes. Sur téléphone, seule l'étape en cours garde son libellé à l'écran ;
 * les autres le gardent pour les lecteurs d'écran.
 */
export function Etapes({ etapes, courante }: Props) {
  return (
    <ol className="etapes" aria-label="Étapes du projet">
      {etapes.map((e, i) => {
        const etat = i === courante ? "courante" : (e.faite ?? i < courante) ? "faite" : "a-venir";
        const contenu = (
          <>
            <span className="etapes__rond" aria-hidden="true">
              {etat === "faite" ? "✓" : i + 1}
            </span>
            <span className="etapes__libelle">{e.libelle}</span>
            {e.detail ? <small className="etapes__detail">{e.detail}</small> : null}
            {etat === "faite" ? <span className="visuellement-cache"> (terminée)</span> : null}
          </>
        );
        return (
          <li key={e.cle} className={`etapes__etape etapes__etape--${etat}`} aria-current={etat === "courante" ? "step" : undefined}>
            {e.lien && (etat !== "a-venir" || e.atteinte) ? (
              <Link to={e.lien} className="etapes__contenu">
                {contenu}
              </Link>
            ) : e.lien ? (
              <span role="link" aria-disabled="true" className="etapes__contenu" title="Étape pas encore atteinte">
                {contenu}
              </span>
            ) : (
              <span className="etapes__contenu">{contenu}</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
