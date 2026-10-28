import { useState } from "react";
import { appliquerTheme, themeEnregistre, type Theme } from "./theme";

export function BoutonTheme() {
  const [theme, setTheme] = useState<Theme>(() => themeEnregistre());
  const suivant: Theme = theme === "sombre" ? "clair" : "sombre";
  const basculer = () => {
    appliquerTheme(suivant);
    setTheme(suivant);
  };
  return (
    <button type="button" className="entete__theme" onClick={basculer} aria-label={`Activer le mode ${suivant}`} title={`Mode ${suivant}`}>
      <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
        {theme === "sombre" ? (
          <path
            d="M12 4V2M12 22v-2M4.9 4.9 3.5 3.5M20.5 20.5l-1.4-1.4M4 12H2M22 12h-2M4.9 19.1l-1.4 1.4M20.5 3.5l-1.4 1.4M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z"
            style={{ fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" }}
          />
        ) : (
          <path
            d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"
            style={{ fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }}
          />
        )}
      </svg>
      <span className="entete__theme-nom">{suivant === "sombre" ? "Sombre" : "Clair"}</span>
    </button>
  );
}
