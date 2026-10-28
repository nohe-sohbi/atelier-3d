import { useState, type ReactNode } from "react";
import "./Aide.css";

const prefixe = "aide-";

function masquee(cle: string): boolean {
  try {
    return localStorage.getItem(prefixe + cle) === "masquee";
  } catch {
    return false;
  }
}

interface Props {
  /** Identifie l'aide : une fois fermée, elle ne revient pas pour cet écran. */
  cle: string;
  /** Une phrase en gras : ce que l'utilisateur fait ici. */
  titre: string;
  children: ReactNode;
}

/** L'encadré « Ce que tu fais ici » en haut de chaque étape : une phrase, une croix pour le fermer. */
export function Aide({ cle, titre, children }: Props) {
  const [visible, setVisible] = useState(() => !masquee(cle));
  if (!visible) return null;
  const fermer = () => {
    try {
      localStorage.setItem(prefixe + cle, "masquee");
    } catch {
      /* stockage indisponible : l'aide reviendra à la prochaine visite */
    }
    setVisible(false);
  };
  return (
    <aside className="aide" aria-label="Aide de cet écran">
      <span className="aide__icone" aria-hidden="true">
        ?
      </span>
      <p className="aide__texte">
        <b>{titre}</b> {children}
      </p>
      <button type="button" className="aide__fermer" aria-label="Masquer cette aide" onClick={fermer}>
        ×
      </button>
    </aside>
  );
}
