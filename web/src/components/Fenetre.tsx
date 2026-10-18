import { useEffect, useId, useRef, type ReactNode } from "react";
import "./Fenetre.css";

export interface FenetreProps {
  ouverte: boolean;
  titre: string;
  /** Appelé quand la fenêtre demande à se fermer (Échap, bouton Fermer, clic sur le voile). */
  onFermer: () => void;
  children: ReactNode;
}

/**
 * Fenêtre modale accessible : role="dialog", Échap la ferme, le focus est piégé à l'intérieur
 * et rendu à l'élément qui l'a ouverte quand elle se ferme.
 */
export function Fenetre({ ouverte, titre, onFermer, children }: FenetreProps) {
  const idTitre = useId();
  const refFenetre = useRef<HTMLDivElement>(null);
  const refOuvreur = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!ouverte) return;
    refOuvreur.current = document.activeElement as HTMLElement | null;

    const fenetre = refFenetre.current;
    const premier = fenetre?.querySelector<HTMLElement>(FOCUSABLES);
    (premier ?? fenetre)?.focus();

    const surTouche = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onFermer();
        return;
      }
      if (e.key === "Tab" && fenetre) {
        const elements = Array.from(fenetre.querySelectorAll<HTMLElement>(FOCUSABLES));
        if (elements.length === 0) {
          e.preventDefault();
          return;
        }
        const premierEl = elements[0]!;
        const dernierEl = elements[elements.length - 1]!;
        if (e.shiftKey && document.activeElement === premierEl) {
          e.preventDefault();
          dernierEl.focus();
        } else if (!e.shiftKey && document.activeElement === dernierEl) {
          e.preventDefault();
          premierEl.focus();
        }
      }
    };
    document.addEventListener("keydown", surTouche);
    return () => {
      document.removeEventListener("keydown", surTouche);
      const ouvreur = refOuvreur.current;
      if (ouvreur && typeof ouvreur.focus === "function") ouvreur.focus();
    };
  }, [ouverte, onFermer]);

  if (!ouverte) return null;

  return (
    <div
      className="fenetre__voile"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onFermer();
      }}
    >
      <div
        ref={refFenetre}
        className="fenetre"
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitre}
        tabIndex={-1}
      >
        <div className="fenetre__entete">
          <h2 id={idTitre} className="fenetre__titre">
            {titre}
          </h2>
          <button type="button" className="fenetre__fermer" aria-label="Fermer" onClick={onFermer}>
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <path
                d="M3 3 L13 13 M13 3 L3 13"
                style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" }}
              />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

const FOCUSABLES =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
