import { useCallback, useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { api, messageErreur } from "../api/client";
import type { Menu } from "../api/types";
import "./Sidebar.css";

type CleBadge = keyof Menu["badges"];

interface Entree {
  libelle: string;
  chemin: string;
  icone: string;
  badge?: CleBadge;
  ton?: "accent" | "neutre";
}

/* Icônes et ordre repris de Sidebar.dc.html. */
const ENTREES: Entree[] = [
  { libelle: "Accueil", chemin: "/", icone: "M3 8.5 L9 3.5 L15 8.5 V15 H11 V11 H7 V15 H3 Z" },
  {
    libelle: "Lots",
    chemin: "/lots",
    icone: "M9 2.5 L16 6 L9 9.5 L2 6 Z M2 9.5 L9 13 L16 9.5 M2 12.5 L9 16 L16 12.5",
    badge: "lots",
    ton: "accent",
  },
  {
    libelle: "Bibliothèque",
    chemin: "/bibliotheque",
    icone: "M3 3 H8 V8 H3 Z M10 3 H15 V8 H10 Z M3 10 H8 V15 H3 Z M10 10 H15 V15 H10 Z",
    badge: "bibliotheque",
    ton: "neutre",
  },
  {
    libelle: "Générateurs",
    chemin: "/generateurs",
    icone: "M6.5 2.5 V6 M11.5 2.5 V6 M4 6 H14 V9 Q14 13 9 13 Q4 13 4 9 Z M9 13 V16",
    badge: "generateurs",
    ton: "accent",
  },
  {
    libelle: "Styles",
    chemin: "/styles",
    icone:
      "M9 2.5 Q15.5 2.5 15.5 8.5 Q15.5 11 13 11 H11.5 Q10 11 10.6 12.5 Q11.5 15.5 9 15.5 Q2.5 15.5 2.5 9 Q2.5 2.5 9 2.5 Z M6 7.5 L6 7.5 M9 5.5 L9 5.5 M12 7.5 L12 7.5",
  },
];

const ICONE_REGLAGES =
  "M9 6.5 A2.5 2.5 0 1 0 9 11.5 A2.5 2.5 0 1 0 9 6.5 Z M9 1.8 V4 M9 14 V16.2 M1.8 9 H4 M14 9 H16.2 M3.9 3.9 L5.5 5.5 M12.5 12.5 L14.1 14.1 M3.9 14.1 L5.5 12.5 M12.5 5.5 L14.1 3.9";

const formatNombre = new Intl.NumberFormat("fr-FR");

function Icone({ d }: { d: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        d={d}
        style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round" }}
      />
    </svg>
  );
}

export function Sidebar() {
  const [menu, setMenu] = useState<Menu | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    api<Menu>("/menu")
      .then((m) => {
        setMenu(m);
        setErreur(null);
      })
      .catch((e) => setErreur(messageErreur(e)));
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  const credits = menu?.credits;
  const pct = credits && credits.total > 0 ? Math.min(100, Math.round((credits.utilises / credits.total) * 100)) : 0;

  return (
    <aside className="sidebar">
      <Link to="/" className="sidebar__logo">
        <svg width="26" height="26" viewBox="0 0 28 28" aria-hidden="true" style={{ display: "block" }}>
          <path
            d="M14 3 L24 8.5 V19.5 L14 25 L4 19.5 V8.5 Z M4 8.5 L14 14 L24 8.5 M14 14 V25"
            style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinejoin: "round" }}
          />
        </svg>
        <span>Atelier 3D</span>
      </Link>

      <Link to="/lots" className="sidebar__nouveau">
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
          <path d="M7 2 V12 M2 7 H12" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" }} />
        </svg>
        Nouveau lot
      </Link>

      <nav aria-label="Menu principal">
        <ul role="list" className="sidebar__liste">
          {ENTREES.map((e) => {
            const valeur = e.badge && menu ? menu.badges[e.badge] : 0;
            return (
              <li key={e.chemin}>
                <NavLink to={e.chemin} end={e.chemin === "/"} className="sidebar__lien">
                  <Icone d={e.icone} />
                  <span className="sidebar__libelle">{e.libelle}</span>
                  {valeur > 0 ? (
                    <span className={`sidebar__badge sidebar__badge--${e.ton ?? "neutre"}`} aria-label={`${valeur}`}>
                      {valeur}
                    </span>
                  ) : null}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      <section aria-labelledby="sb-cols">
        <h2 id="sb-cols" className="sidebar__section-titre">
          Collections
        </h2>
        {menu && menu.collections.length > 0 ? (
          <ul role="list">
            {menu.collections.map((c) => (
              <li key={c.id}>
                <Link to={`/bibliotheque?collection=${encodeURIComponent(String(c.id))}`} className="sidebar__collection">
                  <span aria-hidden="true" className="sidebar__pastille-couleur" style={{ background: c.couleur }} />
                  <span className="sidebar__libelle">{c.nom}</span>
                  <span className="sidebar__nombre">{formatNombre.format(c.nombre)}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="sidebar__vide">{menu || erreur ? "Aucune collection épinglée" : "…"}</p>
        )}
      </section>

      <div className="sidebar__pied">
        <div className="sidebar__credits" aria-live="polite">
          <div className="sidebar__credits-ligne">
            <span>Crédits Meshy{credits?.mode === "simule" ? <span className="sidebar__simule"> · simulé</span> : null}</span>
            <span className="sidebar__nombre">
              {credits ? `${formatNombre.format(credits.utilises)} / ${formatNombre.format(credits.total)}` : menu || erreur ? "—" : "…"}
            </span>
          </div>
          <div
            className="sidebar__jauge"
            role="progressbar"
            aria-label="Crédits Meshy utilisés"
            aria-valuemin={0}
            aria-valuemax={credits?.total ?? 0}
            aria-valuenow={credits?.utilises ?? 0}
          >
            <div className="sidebar__jauge-barre" style={{ width: `${pct}%` }} />
          </div>
          {credits?.renouvellement ? <div className="sidebar__credits-note">{credits.renouvellement}</div> : null}
          {menu && !credits ? <div className="sidebar__credits-note">Solde Meshy non lu (voir Réglages)</div> : null}
          {erreur ? <div className="sidebar__credits-note">Menu non chargé : {erreur}</div> : null}
        </div>
        <NavLink to="/reglages" className="sidebar__lien">
          <Icone d={ICONE_REGLAGES} />
          Réglages
        </NavLink>
      </div>
    </aside>
  );
}
