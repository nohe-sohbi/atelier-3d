import { defineConfig } from "@playwright/test";
import { ADRESSE } from "./e2e/serveur";

/* Bout en bout contre l'application réelle : global-setup lance `python dev.py` (API + Vite) avec une
   base et une config temporaires, les tests pilotent Chromium, global-teardown arrête tout. */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "./test-results",
  use: {
    baseURL: ADRESSE,
    trace: "retain-on-failure",
    locale: "fr-FR",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
