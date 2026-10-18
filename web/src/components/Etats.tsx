import type { ReactNode } from "react";
import "./Etats.css";

export function EtatVide({ titre, texte, enfants }: { titre: string; texte?: string; enfants?: ReactNode }) {
  return (
    <div className="etat etat--vide">
      <p className="etat__titre">{titre}</p>
      {texte ? <p className="etat__texte">{texte}</p> : null}
      {enfants}
    </div>
  );
}

export function Erreur({ message, onReessayer }: { message: string; onReessayer?: () => void }) {
  return (
    <div className="etat etat--erreur" role="alert">
      <div className="etat__corps">
        <p className="etat__titre">Une erreur est survenue</p>
        <p className="etat__texte">{message}</p>
      </div>
      {onReessayer ? (
        <button type="button" className="bouton bouton--petit" onClick={onReessayer}>
          Réessayer
        </button>
      ) : null}
    </div>
  );
}

export function Chargement({ texte = "Chargement…" }: { texte?: string }) {
  return (
    <p className="etat etat--chargement" role="status" aria-live="polite">
      {texte}
    </p>
  );
}
