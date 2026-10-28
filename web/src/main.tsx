import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
// Police Inter servie en local (licence OFL, paquet @fontsource) : aucun appel vers Google Fonts.
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "./styles/base.css";
import { appliquerTheme, themeEnregistre } from "./components/theme";

// Le thème est posé avant le premier affichage : pas de flash clair quand on a choisi le sombre.
appliquerTheme(themeEnregistre());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
