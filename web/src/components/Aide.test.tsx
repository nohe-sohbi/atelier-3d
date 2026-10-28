import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Aide } from "./Aide";

beforeEach(() => localStorage.clear());
afterEach(() => localStorage.clear());

describe("Aide", () => {
  it("dit en une phrase ce que l'utilisateur fait ici", () => {
    render(
      <Aide cle="objets" titre="Ici, tu choisis ce qui sera fabriqué.">
        Décoche ce dont tu n'as pas besoin.
      </Aide>,
    );
    expect(screen.getByRole("complementary", { name: "Aide de cet écran" })).toHaveTextContent("Ici, tu choisis ce qui sera fabriqué. Décoche ce dont tu n'as pas besoin.");
  });

  it("se ferme avec la croix et ne revient pas à la visite suivante", async () => {
    const utilisateur = userEvent.setup();
    const { unmount } = render(<Aide cle="look" titre="Ici, tu choisis le look.">Une phrase.</Aide>);
    await utilisateur.click(screen.getByRole("button", { name: "Masquer cette aide" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    unmount();
    render(<Aide cle="look" titre="Ici, tu choisis le look.">Une phrase.</Aide>);
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("une aide fermée n'en ferme pas une autre", async () => {
    const utilisateur = userEvent.setup();
    const { unmount } = render(<Aide cle="look" titre="A.">x</Aide>);
    await utilisateur.click(screen.getByRole("button", { name: "Masquer cette aide" }));
    unmount();
    render(<Aide cle="fabrication" titre="B.">y</Aide>);
    expect(screen.getByRole("complementary")).toBeInTheDocument();
  });
});
