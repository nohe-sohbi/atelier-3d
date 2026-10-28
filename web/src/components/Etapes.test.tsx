import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Etapes } from "./Etapes";
import { LIBELLES_ETAPES } from "./libellesEtapes";

const ETAPES = LIBELLES_ETAPES.map((libelle) => ({ cle: libelle.toLowerCase(), libelle }));

function rendre(courante: number, etapes = ETAPES) {
  return render(
    <MemoryRouter>
      <Etapes etapes={etapes} courante={courante} />
    </MemoryRouter>,
  );
}

describe("Etapes", () => {
  it("affiche les six étapes dans l'ordre de la maquette", () => {
    rendre(0);
    const liste = within(screen.getByRole("list", { name: "Étapes du projet" }));
    expect(liste.getAllByRole("listitem").map((li) => li.textContent)).toEqual(["1Objets", "2Look", "3Fabrication", "4Validation", "5Essai", "6Jeu"]);
  });

  it("marque l'étape en cours, coche les précédentes et laisse les suivantes à venir", () => {
    rendre(3);
    const items = screen.getAllByRole("listitem");
    expect(items[3]).toHaveAttribute("aria-current", "step");
    expect(items.filter((li) => li.hasAttribute("aria-current"))).toHaveLength(1);
    expect(items[0]).toHaveTextContent("✓Objets (terminée)");
    expect(items[2]).toHaveTextContent("✓Fabrication (terminée)");
    expect(items[4]).toHaveTextContent("5Essai");
    expect(items[4]).not.toHaveTextContent("terminée");
  });

  it("affiche le détail de l'étape (« 2 à valider ») et lie les étapes atteintes seulement", () => {
    const etapes = ETAPES.map((e) => ({ ...e, lien: `/lots/1/${e.cle}`, detail: e.cle === "validation" ? "2 à valider" : undefined }));
    rendre(3, etapes);
    expect(screen.getByText("2 à valider")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Objets/ })).toHaveAttribute("href", "/lots/1/objets");
    expect(screen.getByRole("link", { name: /Validation/ })).toHaveAttribute("href", "/lots/1/validation");
    expect(screen.queryByRole("link", { name: /Essai/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Jeu/ })).not.toBeInTheDocument();
  });
});
