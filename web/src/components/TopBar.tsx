import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageErreur } from "../api/client";
import { surChangementEtPeriodique } from "../api/rafraichissement";
import type { Notification, Notifications, Recherche, ResultatRecherche } from "../api/types";
import "./TopBar.css";

const DELAI_RECHERCHE_MS = 200;

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const diffMin = Math.round((Date.now() - d.getTime()) / 60000);
  if (diffMin < 1) return "à l'instant";
  if (diffMin < 60) return `il y a ${diffMin} min`;
  const h = Math.round(diffMin / 60);
  if (h < 24) return `il y a ${h} h`;
  const j = Math.round(h / 24);
  if (j < 7) return `il y a ${j} j`;
  return d.toLocaleDateString("fr-FR");
}

/* ---------- Recherche globale ---------- */

function RechercheGlobale() {
  const [q, setQ] = useState("");
  const [resultats, setResultats] = useState<ResultatRecherche[] | null>(null);
  const [ouverte, setOuverte] = useState(false);
  const [actif, setActif] = useState(-1);
  const [erreur, setErreur] = useState<string | null>(null);
  const idListe = useId();
  const navigate = useNavigate();
  const refBloc = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const terme = q.trim();
    if (!terme) {
      setResultats(null);
      setOuverte(false);
      setErreur(null);
      return;
    }
    let annule = false;
    const t = setTimeout(() => {
      api<Recherche>(`/recherche?q=${encodeURIComponent(terme)}`)
        .then((r) => {
          if (annule) return;
          setResultats(r.resultats);
          setErreur(null);
          setOuverte(true);
          setActif(-1);
        })
        .catch((e) => {
          if (annule) return;
          setErreur(messageErreur(e));
          setResultats([]);
          setOuverte(true);
        });
    }, DELAI_RECHERCHE_MS);
    return () => {
      annule = true;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    if (!ouverte) return;
    const surClic = (e: MouseEvent) => {
      if (refBloc.current && !refBloc.current.contains(e.target as Node)) setOuverte(false);
    };
    document.addEventListener("mousedown", surClic);
    return () => document.removeEventListener("mousedown", surClic);
  }, [ouverte]);

  const surTouche = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!ouverte || !resultats) {
      if (e.key === "ArrowDown" && resultats && resultats.length > 0) setOuverte(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActif((a) => Math.min(resultats.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActif((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter" && actif >= 0) {
      e.preventDefault();
      const r = resultats[actif];
      if (r) {
        setOuverte(false);
        navigate(r.lien);
      }
    } else if (e.key === "Escape") {
      setOuverte(false);
    }
  };

  const idOption = (i: number) => `${idListe}-opt-${i}`;

  return (
    <div className="recherche" ref={refBloc}>
      <label htmlFor="global-search" className="visuellement-cache">
        Rechercher partout
      </label>
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="recherche__icone">
        <path
          d="M7 2.5 A4.5 4.5 0 1 0 7 11.5 A4.5 4.5 0 1 0 7 2.5 Z M10.5 10.5 L14 14"
          style={{ fill: "none", stroke: "var(--texte-secondaire)", strokeWidth: 1.6, strokeLinecap: "round" }}
        />
      </svg>
      <input
        id="global-search"
        type="search"
        className="recherche__champ"
        placeholder="Rechercher un asset, un lot, une étiquette…"
        autoComplete="off"
        role="combobox"
        aria-expanded={ouverte}
        aria-controls={idListe}
        aria-autocomplete="list"
        aria-activedescendant={ouverte && actif >= 0 ? idOption(actif) : undefined}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => {
          if (resultats) setOuverte(true);
        }}
        onKeyDown={surTouche}
      />
      {ouverte && resultats ? (
        <ul id={idListe} role="listbox" aria-label="Résultats de la recherche" className="recherche__liste">
          {erreur ? <li className="recherche__rien">Recherche impossible : {erreur}</li> : null}
          {!erreur && resultats.length === 0 ? <li className="recherche__rien">Aucun résultat</li> : null}
          {resultats.map((r, i) => (
            <li
              key={`${r.type}-${r.id}`}
              id={idOption(i)}
              role="option"
              aria-selected={i === actif}
              className="recherche__option"
              onMouseEnter={() => setActif(i)}
            >
              <Link to={r.lien} tabIndex={-1} onClick={() => setOuverte(false)}>
                <span className="recherche__type">{r.type}</span>
                <span>{r.titre}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/* ---------- Notifications ---------- */

function Notifications() {
  const [liste, setListe] = useState<Notification[]>([]);
  const [nonLues, setNonLues] = useState(0);
  const [erreur, setErreur] = useState<string | null>(null);
  const [ouvert, setOuvert] = useState(false);
  const refBloc = useRef<HTMLDivElement>(null);
  const refBouton = useRef<HTMLButtonElement>(null);
  const navigate = useNavigate();

  const charger = useCallback(() => {
    api<Notifications>("/notifications")
      .then((r) => {
        setListe(r.notifications);
        setNonLues(r.non_lues);
        setErreur(null);
      })
      .catch((e) => setErreur(messageErreur(e)));
  }, []);

  useEffect(() => {
    charger();
    return surChangementEtPeriodique(charger);
  }, [charger]);

  useEffect(() => {
    if (!ouvert) return;
    const surClic = (e: MouseEvent) => {
      if (refBloc.current && !refBloc.current.contains(e.target as Node)) setOuvert(false);
    };
    const surTouche = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        setOuvert(false);
        refBouton.current?.focus();
      }
    };
    document.addEventListener("mousedown", surClic);
    document.addEventListener("keydown", surTouche);
    return () => {
      document.removeEventListener("mousedown", surClic);
      document.removeEventListener("keydown", surTouche);
    };
  }, [ouvert]);

  const marquerLu = async (n: Notification) => {
    if (!n.lu) {
      setListe((l) => l.map((x) => (x.id === n.id ? { ...x, lu: true } : x)));
      setNonLues((v) => Math.max(0, v - 1));
      try {
        await api(`/notifications/${encodeURIComponent(String(n.id))}/lu`, { method: "POST" });
      } catch (e) {
        setErreur(messageErreur(e));
      }
      charger();
    }
    setOuvert(false);
    if (n.lien) navigate(n.lien);
  };

  const toutLu = async () => {
    setListe((l) => l.map((x) => ({ ...x, lu: true })));
    setNonLues(0);
    try {
      await api("/notifications/tout-lu", { method: "POST" });
    } catch (e) {
      setErreur(messageErreur(e));
    }
    charger();
  };

  const libelle =
    nonLues === 0 ? "Notifications : aucune nouvelle" : nonLues === 1 ? "Notifications : 1 nouvelle" : `Notifications : ${nonLues} nouvelles`;

  return (
    <div className="notifs" ref={refBloc}>
      <button
        ref={refBouton}
        type="button"
        className="notifs__bouton"
        aria-expanded={ouvert}
        aria-controls="notif-panel"
        aria-label={libelle}
        onClick={() => {
          setOuvert((o) => !o);
          if (!ouvert) charger();
        }}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
          <path
            d="M4.5 12.5 V8 Q4.5 3.5 9 3.5 Q13.5 3.5 13.5 8 V12.5 L15 14 H3 Z M7.5 15.5 Q9 17 10.5 15.5"
            style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinejoin: "round", strokeLinecap: "round" }}
          />
        </svg>
        {nonLues > 0 ? <span aria-hidden="true" className="notifs__point" /> : null}
      </button>
      {ouvert ? (
        <div id="notif-panel" role="region" aria-label="Notifications" className="notifs__panneau">
          <div className="notifs__entete">
            <span>{nonLues === 0 ? "Aucune nouvelle" : nonLues === 1 ? "1 nouvelle" : `${nonLues} nouvelles`}</span>
            {nonLues > 0 ? (
              <button type="button" className="notifs__tout-lu" onClick={toutLu}>
                Tout marquer lu
              </button>
            ) : null}
          </div>
          {erreur ? <p className="notifs__vide">Notifications non chargées : {erreur}</p> : null}
          {!erreur && liste.length === 0 ? <p className="notifs__vide">Aucune notification</p> : null}
          {liste.length > 0 ? (
            <ul role="list">
              {liste.map((n) => (
                <li key={n.id}>
                  <button type="button" className={`notif${n.lu ? " notif--lu" : ""}`} onClick={() => marquerLu(n)}>
                    <span aria-hidden="true" className={`notif__point${n.lu ? " notif__point--lu" : ""}`} />
                    <span className="notif__corps">
                      <span className="notif__titre">{n.titre}</span>
                      <span className="notif__texte">
                        {n.texte}
                        {n.texte ? " · " : ""}
                        {formatDate(n.date)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          <p className="notifs__note">Les notifications restent dans l'app ; rien n'est envoyé par mail.</p>
        </div>
      ) : null}
    </div>
  );
}

export function TopBar() {
  return (
    <header className="topbar">
      <div className="topbar__ligne">
        <RechercheGlobale />
        <Notifications />
      </div>
    </header>
  );
}
