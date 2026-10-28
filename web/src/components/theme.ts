/* Thème clair (par défaut) ou sombre, gardé d'une visite à l'autre. */
export type Theme = "clair" | "sombre";

const CLE = "theme-atelier";

export function themeEnregistre(): Theme {
  try {
    return localStorage.getItem(CLE) === "sombre" ? "sombre" : "clair";
  } catch {
    return "clair";
  }
}

export function appliquerTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(CLE, theme);
  } catch {
    /* stockage indisponible : le thème vaut pour cette visite seulement */
  }
}
