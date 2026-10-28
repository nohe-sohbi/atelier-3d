import type { Menu } from "../api/types";
import { Icone, LienMenu } from "./LienMenu";
import { ENTREES, valeurBadge } from "./navigation";
import "./BarreOnglets.css";

/** Menu du téléphone et de la tablette : quatre onglets en bas de l'écran, à portée du pouce. */
export function BarreOnglets({ menu }: { menu: Menu | null }) {
  return (
    <nav aria-label="Menu du téléphone" className="onglets-bas">
      {ENTREES.map((e) => {
        const valeur = valeurBadge(menu, e.badge);
        return (
          <LienMenu key={e.chemin} chemin={e.chemin} className="onglets-bas__lien">
            <span className="onglets-bas__icone">
              <Icone d={e.icone} />
              {valeur > 0 ? (
                <span className="onglets-bas__badge" aria-label={`${valeur}`}>
                  {valeur}
                </span>
              ) : null}
            </span>
            <span>{e.libelle}</span>
          </LienMenu>
        );
      })}
    </nav>
  );
}
