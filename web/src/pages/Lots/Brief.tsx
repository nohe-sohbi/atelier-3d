import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import { ATTENTE_WORKER_MS, AttenteAbandonnee, attendreTache } from "../../api/taches";
import type { EnTeteLot, ObjetLot, ObjetsLot, StyleResume, Styles, Tache } from "../../api/types";
import { Chargement, Erreur, EtatVide } from "../../components/Etats";
import { DemandeClaudeCode } from "./DemandeClaudeCode";
import { LIBELLES_VOIES, pluriel, texteDimensions, texteResume } from "./commun";

interface Props {
  lotId: number;
  /** Le lot a changé (champs, liste, choix) : l'en-tête se relit. */
  onChangement: () => void;
}

/** Projet · 1 Objets : thème, style, demande ; Claude propose la liste, le routage choisit les voies, tu coches. */
export function Brief({ lotId, onChangement }: Props) {
  const naviguer = useNavigate();
  const [lot, setLot] = useState<EnTeteLot | null>(null);
  const [styles, setStyles] = useState<StyleResume[]>([]);
  const [objets, setObjets] = useState<ObjetsLot | null>(null);
  const [theme, setTheme] = useState("");
  const [besoin, setBesoin] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [alerte, setAlerte] = useState<string | null>(null);
  const [tache, setTache] = useState<Tache | null>(null);
  const [enAttenteMs, setEnAttenteMs] = useState(0);
  const [occupe, setOccupe] = useState(false);
  const [demande, setDemande] = useState<ObjetLot | null>(null);
  const attente = useRef<AbortController | null>(null);
  // Le thème et le besoin déjà envoyés, et l'enregistrement en cours : la proposition l'attend et ne renvoie rien en double.
  const envoye = useRef({ theme: "", besoin: "" });
  const sauvegarde = useRef<Promise<unknown>>(Promise.resolve());

  const changer = useCallback(() => {
    onChangement();
    signalerChangement();
  }, [onChangement]);

  const suivre = useCallback(
    async (tacheId: number) => {
      attente.current?.abort();
      const controle = new AbortController();
      attente.current = controle;
      setOccupe(true);
      try {
        const t = await attendreTache(
          tacheId,
          (lue, ms) => {
            setTache(lue);
            setEnAttenteMs(ms);
          },
          { signal: controle.signal },
        );
        if (t.etat !== "terminee") setAlerte(t.erreur ?? `La proposition est ${t.etat}.`);
        setObjets(await api<ObjetsLot>(`/lots/${lotId}/objets`, { signal: controle.signal }));
        setLot(await api<EnTeteLot>(`/lots/${lotId}`, { signal: controle.signal }));
        changer();
      } catch (e) {
        if (e instanceof AttenteAbandonnee || controle.signal.aborted) return;
        setAlerte(messageErreur(e));
      } finally {
        if (!controle.signal.aborted) {
          setTache(null);
          setEnAttenteMs(0);
          setOccupe(false);
        }
      }
    },
    [lotId, changer],
  );

  const charger = useCallback(async () => {
    try {
      const [l, s, o] = await Promise.all([api<EnTeteLot>(`/lots/${lotId}`), api<Styles>("/styles"), api<ObjetsLot>(`/lots/${lotId}/objets`)]);
      setLot(l);
      setTheme(l.theme);
      setBesoin(l.besoin);
      envoye.current = { theme: l.theme, besoin: l.besoin };
      setStyles(s.styles);
      setObjets(o);
      setErreur(null);
      // Une proposition partie avant (écran quitté, rechargé) : on reprend son suivi.
      if (o.proposition && (o.proposition.etat === "en_attente" || o.proposition.etat === "en_cours")) suivre(o.proposition.id);
      else if (o.proposition?.etat === "echouee") setAlerte(o.proposition.erreur ?? "La dernière proposition a échoué.");
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, [lotId, suivre]);

  useEffect(() => {
    charger();
    return () => attente.current?.abort();
  }, [charger]);

  const enregistrer = (champs: { theme?: string; besoin?: string; style_id?: number }) => {
    envoye.current = { ...envoye.current, ...Object.fromEntries(Object.entries(champs).filter(([k]) => k !== "style_id")) };
    const envoi = sauvegarde.current
      .catch(() => undefined)
      .then(() => api<EnTeteLot>(`/lots/${lotId}`, { method: "PATCH", body: JSON.stringify(champs) }))
      .then((l) => {
        setLot(l);
        changer();
      });
    sauvegarde.current = envoi;
    return envoi;
  };

  const enregistrerChamp = async (champs: { theme?: string; besoin?: string; style_id?: number }) => {
    try {
      await enregistrer(champs);
    } catch (e) {
      setAlerte(messageErreur(e));
    }
  };

  const proposer = async () => {
    if (!lot) return;
    setAlerte(null);
    setOccupe(true);
    try {
      // Ce qui est tapé et pas encore enregistré part avant la demande ; un enregistrement en cours est attendu.
      if (theme !== envoye.current.theme || besoin !== envoye.current.besoin) enregistrer({ theme, besoin });
      await sauvegarde.current;
      const { tache_id } = await api<{ tache_id: number }>(`/lots/${lotId}/proposition`, { method: "POST" });
      await suivre(tache_id);
    } catch (e) {
      setAlerte(messageErreur(e));
      setOccupe(false);
    }
  };

  const basculer = async (o: ObjetLot) => {
    setAlerte(null);
    const poser = (retire: boolean) =>
      setObjets((avant) => avant && { ...avant, objets: avant.objets.map((x) => (x.id === o.id ? { ...x, retire } : x)) });
    // La case répond tout de suite ; la réponse de l'API (compteur, résumé) suit, ou l'annule.
    poser(!o.retire);
    try {
      setObjets(await api<ObjetsLot>(`/lots/${lotId}/objets/${o.id}`, { method: "PATCH", body: JSON.stringify({ retenu: o.retire }) }));
      changer();
    } catch (e) {
      poser(o.retire);
      setAlerte(messageErreur(e));
    }
  };

  const valider = async () => {
    setAlerte(null);
    setOccupe(true);
    try {
      await api<EnTeteLot>(`/lots/${lotId}/valider-brief`, { method: "POST" });
      signalerChangement();
      naviguer(`/lots/${lotId}/references`);
    } catch (e) {
      setAlerte(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  const fermerDemande = useCallback(() => setDemande(null), []);
  const voieChangee = useCallback(async () => {
    setObjets(await api<ObjetsLot>(`/lots/${lotId}/objets`));
    changer();
  }, [lotId, changer]);

  if (erreur) return <Erreur message={erreur} onReessayer={charger} />;
  if (!lot || !objets) return <Chargement />;

  const resume = objets.resume;
  const aDesObjets = objets.objets.length > 0;

  return (
    <div className="brief">
      <section aria-labelledby="brief-titre" className="brief__panneau brief__panneau--champs">
        <div>
          <h2 id="brief-titre" className="brief__titre">
            Ta demande
          </h2>
          <p className="brief__texte">Un thème, un style, une phrase. Claude propose la liste d'objets à fabriquer.</p>
        </div>
        <div className="brief__champ">
          <label htmlFor="brief-theme">Thème</label>
          <input
            id="brief-theme"
            type="text"
            className="champ brief__saisie"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            onBlur={() => theme !== envoye.current.theme && enregistrerChamp({ theme })}
          />
        </div>
        <div className="brief__champ">
          <label htmlFor="brief-style">Style</label>
          <select
            id="brief-style"
            className="champ brief__saisie"
            value={lot.style ? String(lot.style.id) : ""}
            onChange={(e) => e.target.value && enregistrerChamp({ style_id: Number(e.target.value) })}
          >
            {lot.style ? null : <option value="">Choisis un style</option>}
            {styles.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nom} ({s.code}){s.etat === "brouillon" ? " · brouillon" : ""}
              </option>
            ))}
          </select>
          <p className="brief__aide">
            Le style fixe la palette, les matériaux et les budgets de tout le projet. <Link to="/styles">Voir les styles</Link>
          </p>
        </div>
        <div className="brief__champ">
          <label htmlFor="brief-besoin">Ce que tu veux</label>
          <textarea
            id="brief-besoin"
            rows={4}
            className="brief__saisie"
            value={besoin}
            onChange={(e) => setBesoin(e.target.value)}
            onBlur={() => besoin !== envoye.current.besoin && enregistrerChamp({ besoin })}
          />
        </div>
        <button type="button" className="bouton" onClick={proposer} disabled={occupe}>
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M13 3 V6.5 H9.5 M12.6 6.2 A5 5 0 1 0 13 9.5" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round" }} />
          </svg>
          {aDesObjets ? "Reproposer la liste" : "Proposer la liste"}
        </button>
        {tache ? (
          <p role="status" className="brief__progression">
            {tache.etat === "en_cours" ? "Claude prépare la liste…" : "Demande envoyée…"}
            {enAttenteMs >= ATTENTE_WORKER_MS
              ? ` En attente depuis ${Math.round(enAttenteMs / 1000)} s : le worker la prendra dès qu'il tourne (python dev.py le lance avec l'API).`
              : ""}
          </p>
        ) : null}
      </section>

      <section aria-labelledby="liste-titre" className="brief__panneau brief__panneau--liste">
        <div className="brief__liste-entete">
          <h2 id="liste-titre" className="brief__titre brief__titre--liste">
            Liste proposée
          </h2>
          <span className="secondaire">{pluriel(resume.retenus, "objet retenu", "objets retenus")}</span>
        </div>
        <p className="brief__texte">
          Claude classe chaque objet, puis les règles de routage choisissent sa voie : ta bibliothèque d'abord, puis un équivalent CC0, le code pour le
          géométrique, l'IA pour l'ornemental. Un objet géométrique sans générateur est marqué « À créer ».
        </p>
        {objets.simule ? (
          <p className="brief__simule">
            <span className="pastille pastille--neutre">simulé</span> Liste simulée : l'API Claude est en mode simulé (Réglages). Ces objets servent à essayer
            l'écran.
          </p>
        ) : null}
        {alerte ? (
          <div role="alert" className="brief__alerte">
            {alerte}
          </div>
        ) : null}

        {aDesObjets ? (
          <ul role="list" aria-label="Objets proposés" className="brief__objets">
            {objets.objets.map((o) => (
              <li key={o.id} className={`brief__objet${o.retire ? " brief__objet--retire" : ""}`}>
                <input
                  type="checkbox"
                  id={`objet-${o.id}`}
                  className="brief__case"
                  checked={!o.retire}
                  disabled={o.voie === "hors_perimetre"}
                  onChange={() => basculer(o)}
                />
                <div className="brief__objet-texte">
                  <label htmlFor={`objet-${o.id}`} className="brief__objet-nom">
                    {o.nom}
                  </label>
                  {o.description ? <div className="brief__objet-desc">{o.description}</div> : null}
                  {o.pieces.length > 0 ? (
                    <div className="brief__objet-desc">
                      {pluriel(o.pieces.length, "pièce", "pièces")} : {o.pieces.map((p) => `${p.nom} (${LIBELLES_VOIES[p.voie]})`).join(" · ")}
                    </div>
                  ) : null}
                  {o.raison_voie ? <div className="brief__objet-raison">{o.raison_voie}</div> : null}
                  {o.voie === "a_creer" ? (
                    <button type="button" className="brief__lien" onClick={() => setDemande(o)}>
                      Préparer la demande pour Claude Code
                    </button>
                  ) : null}
                </div>
                <span className={`voie voie--${o.voie}`}>{LIBELLES_VOIES[o.voie]}</span>
                <span
                  className="brief__dimensions mono"
                  title={o.dimensions ? (o.dimensions.source === "style" ? "Dimensions du style" : "Dimensions proposées par Claude") : undefined}
                >
                  {texteDimensions(o.dimensions)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EtatVide
            titre="Aucune liste pour l'instant"
            texte="Écris ce que tu veux, puis « Proposer la liste » : Claude propose les objets, les règles de routage choisissent leur voie."
          />
        )}

        {aDesObjets ? (
          <div className="brief__pied">
            <p className="brief__resume">{texteResume(resume)}</p>
            <button type="button" className="bouton bouton--primaire" onClick={valider} disabled={occupe || resume.retenus === 0}>
              Choisir les looks →
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                <path d="M3 8 H13 M9 4 L13 8 L9 12" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" }} />
              </svg>
            </button>
          </div>
        ) : null}
      </section>

      <DemandeClaudeCode lotId={lotId} objet={demande} onFermer={fermerDemande} onVoieChangee={voieChangee} />
    </div>
  );
}
