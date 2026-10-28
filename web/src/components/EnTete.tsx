import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api/client";
import { surChangementEtPeriodique } from "../api/rafraichissement";
import type { Menu } from "../api/types";
import { BarreOnglets } from "./BarreOnglets";
import { BoutonTheme } from "./BoutonTheme";
import { Icone, LienMenu } from "./LienMenu";
import { ENTREES, valeurBadge } from "./navigation";
import { Notifications, RechercheGlobale } from "./RechercheEtNotifications";
import "./EnTete.css";

const formatNombre = new Intl.NumberFormat("fr-FR");

const ICONE_REGLAGES =
  "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z";
const ICONE_LOUPE = "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.3-4.3";

/** En-tête de toute l'app : logo, menu, recherche, crédits, thème, notifications, réglages. Sous 1000 px, le menu passe en barre d'onglets en bas. */
export function EnTete() {
  const [menu, setMenu] = useState<Menu | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [recherche, setRecherche] = useState(false);

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
    return surChangementEtPeriodique(charger);
  }, [charger]);

  const credits = menu?.credits;
  const pct = credits && credits.total > 0 ? Math.min(100, Math.round((credits.utilises / credits.total) * 100)) : 0;
  const infoCredits = erreur
    ? `Menu non chargé : ${erreur}`
    : menu && !credits
      ? "Solde Meshy non lu (voir Réglages)"
      : credits
        ? `Crédits Meshy du mois : ${formatNombre.format(credits.utilises)} utilisés sur ${formatNombre.format(credits.total)}${credits.renouvellement ? ` · ${credits.renouvellement}` : ""}${credits.mode === "simule" ? " · solde simulé" : ""}`
        : "Crédits en cours de lecture";

  const ouvrirRecherche = () => {
    setRecherche((o) => !o);
    setTimeout(() => document.getElementById("global-search")?.focus(), 0);
  };

  return (
    <>
      <header className="entete">
        <div className="entete__ligne">
          <Link to="/" className="entete__logo" aria-label="Atelier 3D, accueil">
            <span className="entete__logo-forme" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 16 16">
                <path d="M8 1.5 14 5v6L8 14.5 2 11V5z M2 5l6 3.5L14 5 M8 8.5v6" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.4, strokeLinejoin: "round" }} />
              </svg>
            </span>
            <span className="entete__logo-nom">Atelier 3D</span>
          </Link>

          <nav aria-label="Menu principal" className="entete__nav">
            {ENTREES.map((e) => {
              const valeur = valeurBadge(menu, e.badge);
              return (
                <LienMenu key={e.chemin} chemin={e.chemin} className="entete__lien">
                  {e.libelle}
                  {valeur > 0 ? (
                    <span className="entete__badge" aria-label={`${valeur}`}>
                      {valeur}
                    </span>
                  ) : null}
                </LienMenu>
              );
            })}
          </nav>

          <div className="entete__outils">
            <button type="button" className="entete__icone entete__loupe" aria-label="Rechercher" aria-expanded={recherche} onClick={ouvrirRecherche}>
              <Icone d={ICONE_LOUPE} taille={18} />
            </button>
            <BoutonTheme />
            <div className="entete__credits" title={infoCredits} aria-live="polite">
              <span>Crédits</span>
              <b>{credits ? formatNombre.format(credits.restants) : menu || erreur ? "—" : "…"}</b>
              <span
                className="entete__jauge"
                role="progressbar"
                aria-label="Crédits Meshy utilisés"
                aria-valuemin={0}
                aria-valuemax={credits?.total ?? 0}
                aria-valuenow={credits?.utilises ?? 0}
              >
                <i style={{ width: `${pct}%` }} />
              </span>
              <span className="visuellement-cache">{infoCredits}</span>
            </div>
            <Notifications />
            <Link to="/reglages" className="entete__icone" aria-label="Réglages" title="Réglages">
              <Icone d={ICONE_REGLAGES} taille={18} />
            </Link>
          </div>
        </div>
        <div className={`entete__recherche${recherche ? " entete__recherche--ouverte" : ""}`}>
          <RechercheGlobale />
        </div>
      </header>
      <BarreOnglets menu={menu} />
    </>
  );
}
