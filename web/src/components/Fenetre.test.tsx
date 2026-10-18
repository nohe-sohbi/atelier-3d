import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Fenetre } from "./Fenetre";

function Demo() {
  const [ouverte, setOuverte] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOuverte(true)}>
        Ouvrir
      </button>
      <Fenetre ouverte={ouverte} titre="Fenêtre d'essai" onFermer={() => setOuverte(false)}>
        <p>Contenu</p>
        <button type="button">Valider</button>
      </Fenetre>
    </>
  );
}

describe("Fenetre", () => {
  it("s'ouvre avec un rôle dialog, se ferme avec Échap et rend le focus au bouton d'ouverture", async () => {
    const utilisateur = userEvent.setup();
    render(<Demo />);
    const ouvrir = screen.getByRole("button", { name: "Ouvrir" });
    await utilisateur.click(ouvrir);

    const dialog = screen.getByRole("dialog", { name: "Fenêtre d'essai" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("button", { name: "Fermer" })).toHaveFocus();

    await utilisateur.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(ouvrir).toHaveFocus();
  });

  it("le bouton Fermer ferme aussi et rend le focus", async () => {
    const utilisateur = userEvent.setup();
    render(<Demo />);
    const ouvrir = screen.getByRole("button", { name: "Ouvrir" });
    await utilisateur.click(ouvrir);
    await utilisateur.click(screen.getByRole("button", { name: "Fermer" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(ouvrir).toHaveFocus();
  });

  it("Tab reste dans la fenêtre", async () => {
    const utilisateur = userEvent.setup();
    render(<Demo />);
    await utilisateur.click(screen.getByRole("button", { name: "Ouvrir" }));
    const fermer = screen.getByRole("button", { name: "Fermer" });
    const valider = screen.getByRole("button", { name: "Valider" });
    expect(fermer).toHaveFocus();
    await utilisateur.tab();
    expect(valider).toHaveFocus();
    await utilisateur.tab();
    expect(fermer).toHaveFocus();
  });
});
