import { useId, type ReactNode } from "react";
import type { EtatTest, ModeService } from "../../api/types";

export type EtatPastille = EtatTest | "Non testé" | "Test en cours…";

export function Pastille({ etat }: { etat: EtatPastille }) {
  const ton =
    etat === "Erreur" ? "erreur" : etat === "Non testé" || etat === "Test en cours…" ? "neutre" : "succes";
  return (
    <span className={`pastille pastille--${ton}`} role="status">
      {etat}
    </span>
  );
}

export function Ligne({ libelle, htmlFor, colonne, children }: { libelle: string; htmlFor?: string; colonne?: boolean; children: ReactNode }) {
  return (
    <div className="ligne">
      <dt className="ligne__dt">{htmlFor ? <label htmlFor={htmlFor}>{libelle}</label> : libelle}</dt>
      <dd className={`ligne__dd${colonne ? " ligne__dd--colonne" : ""}`}>{children}</dd>
    </div>
  );
}

export function Interrupteur({ nom, libelle, valeur, onChange }: { nom: string; libelle: string; valeur: ModeService; onChange: (m: ModeService) => void }) {
  const id = useId();
  return (
    <div className="interrupteur" role="radiogroup" aria-label={libelle}>
      {(["simule", "reel"] as const).map((m) => (
        <label key={m} className="interrupteur__option" htmlFor={`${id}-${m}`}>
          <input
            id={`${id}-${m}`}
            type="radio"
            name={`${nom}-mode`}
            value={m}
            checked={valeur === m}
            onChange={() => onChange(m)}
          />
          {m === "simule" ? "Simulé" : "Réel"}
        </label>
      ))}
    </div>
  );
}

export interface ChampCleProps {
  id: string;
  definie: boolean;
  apercu: string;
  valeur: string;
  effacee: boolean;
  note: string;
  onChange: (v: string) => void;
  onEffacer: (effacee: boolean) => void;
}

/** Champ de clé API : vide par défaut, aperçu en placeholder, bouton pour effacer (envoie null). */
export function ChampCle({ id, definie, apercu, valeur, effacee, note, onChange, onEffacer }: ChampCleProps) {
  return (
    <>
      <input
        id={id}
        type="password"
        className="champ champ--cle"
        autoComplete="off"
        placeholder={effacee ? "Sera effacée à l'enregistrement" : definie ? apercu || "••••" : "Aucune clé"}
        value={valeur}
        disabled={effacee}
        onChange={(e) => onChange(e.target.value)}
      />
      <span className="note">{note}</span>
      {definie ? (
        <button
          type="button"
          className="bouton bouton--petit"
          aria-describedby={id}
          onClick={() => {
            onEffacer(!effacee);
            if (!effacee) onChange("");
          }}
        >
          {effacee ? "Garder la clé" : "Effacer la clé"}
        </button>
      ) : null}
    </>
  );
}
