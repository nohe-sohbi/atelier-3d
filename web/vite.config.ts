import { rmSync } from "node:fs";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Port de l'API : dev.py le passe par ATELIER_API_PORT quand il n'est pas 8000.
const portApi = process.env.ATELIER_API_PORT ?? "8000";

export default defineConfig({
  plugins: [
    react(),
    {
      // La maquette (web/public/proposition) et la comparaison (web/public/comparaison) servent à construire l'app :
      // elles ne partent jamais dans la version publiée.
      name: "sans-outils-de-conception",
      closeBundle() {
        for (const dossier of ["proposition", "comparaison"]) rmSync(`dist/${dossier}`, { recursive: true, force: true });
      },
    },
  ],
  server: {
    // 127.0.0.1 et pas « localhost » : là où localhost désigne d'abord ::1, Vite n'écouterait qu'en IPv6
    // et http://127.0.0.1:5173 (ouvert par dev.py, visé par les tests) ne répondrait pas.
    // `python dev.py --reseau` passe 0.0.0.0 : l'interface s'ouvre aux autres appareils, l'API reste locale (proxy).
    host: process.env.ATELIER_WEB_HOTE ?? "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${portApi}`,
        changeOrigin: false,
      },
      "/sante": {
        target: `http://127.0.0.1:${portApi}`,
        changeOrigin: false,
      },
    },
  },
  build: {
    // Pas « assets » : c'est la route de la fiche asset (/assets/:id) dans l'application.
    assetsDir: "statique",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
  },
});
