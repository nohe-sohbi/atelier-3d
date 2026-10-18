import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

/** Rend l'application complète sur un chemin donné. */
export function rendreApp(chemin = "/") {
  return render(
    <MemoryRouter initialEntries={[chemin]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>,
  );
}
