import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import type { EnTeteLot, LotResume, Lots, StyleResume, Styles } from "../../api/types";
import { Erreur } from "../../components/Etats";
import { nomDuLot } from "../Lots/commun";
import "./Creer.css";

/** « À toi » : les projets qui attendent une action de l'utilisateur (un look à choisir, des objets à valider…). */
const TONS_A_TOI = new Set(["warn", "accent"]);

/**
 * Créer (la page d'accueil) : une phrase, un style, et l'app propose la liste des objets.
 * Les projets qui t'attendent passent avant le formulaire.
 */
export function Creer() {
  const naviguer = useNavigate();
  const [besoin, setBesoin] = useState("");
  const [styles, setStyles] = useState<StyleResume[] | null>(null);
  const [styleId, setStyleId] = useState<number | null>(null);
  const [attente, setAttente] = useState<LotResume[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);

  const charger = useCallback(async () => {
    try {
      const [s, l] = await Promise.all([api<Styles>("/styles"), api<Lots>("/lots?groupe=en_cours")]);
      const prets = s.styles.filter((x) => x.etat === "valide");
      setStyles(prets);
      setStyleId((courant) => courant ?? prets[0]?.id ?? null);
      setAttente(l.lots.filter((x) => TONS_A_TOI.has(x.ton)).slice(0, 3));
      setErreur(null);
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  const proposer = async (e: FormEvent) => {
    e.preventDefault();
    if (!besoin.trim() || styleId === null || occupe) return;
    setOccupe(true);
    setErreur(null);
    try {
      const lot = await api<EnTeteLot>("/lots", { method: "POST", body: JSON.stringify({ besoin: besoin.trim(), style_id: styleId }) });
      await api(`/lots/${lot.id}/proposition`, { method: "POST" });
      signalerChangement();
      naviguer(`/lots/${lot.id}/brief`);
    } catch (err) {
      setErreur(messageErreur(err));
      setOccupe(false);
    }
  };

  const sansStyle = styles !== null && styles.length === 0;

  return (
    <div className="creer">
      {attente.length > 0 ? (
        <section aria-labelledby="creer-a-toi" className="creer__a-toi">
          <h2 id="creer-a-toi" className="creer__titre-section">
            À toi de jouer
          </h2>
          <ul role="list" className="creer__projets">
            {attente.map((p) => (
              <li key={p.id}>
                <Link to={p.lien} className="creer__projet">
                  <span className="creer__projet-nom">{nomDuLot(p.nom)}</span>
                  <span className="creer__projet-detail">{p.detail}</span>
                  <span className={`ton ton--${p.ton}`}>{p.statut}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <form className="creer__carte" onSubmit={proposer} aria-labelledby="creer-titre">
        <div>
          <h1 id="creer-titre" className="page-titre">
            Que veux-tu créer ?
          </h1>
          <p className="page-sous-titre">Décris-le en une phrase. L'app propose les objets, tu choisis leur look, elle fabrique, tu valides.</p>
        </div>

        <div className="creer__champ">
          <label htmlFor="creer-besoin" className="creer__etiquette">
            Ta demande
          </label>
          <textarea
            id="creer-besoin"
            className="creer__saisie"
            rows={3}
            value={besoin}
            placeholder="Ex. des tonneaux, des caisses et une lanterne pour un petit port de pêche, un peu usés"
            onChange={(e) => setBesoin(e.target.value)}
          />
        </div>

        <fieldset className="creer__champ creer__styles" disabled={sansStyle}>
          <legend className="creer__etiquette">Style</legend>
          {styles === null ? <p className="creer__note">Chargement des styles…</p> : null}
          {sansStyle ? (
            <p className="creer__note">
              Aucun style prêt. <Link to="/styles">Crée ou valide un style</Link> pour commencer.
            </p>
          ) : null}
          <div className="creer__liste-styles" role="radiogroup" aria-label="Style">
            {(styles ?? []).map((s) => (
              <label key={s.id} className={`creer__style${s.id === styleId ? " creer__style--choisi" : ""}`}>
                <input type="radio" name="style" className="visuellement-cache" checked={s.id === styleId} onChange={() => setStyleId(s.id)} />
                <span aria-hidden="true" className="creer__palette">
                  {s.palette.slice(0, 5).map((c) => (
                    <i key={c.hex} style={{ background: c.hex }} />
                  ))}
                </span>
                <span className="creer__style-nom">{s.nom}</span>
                {s.description ? <span className="creer__style-texte">{s.description}</span> : null}
              </label>
            ))}
          </div>
        </fieldset>

        {erreur ? <Erreur message={erreur} onReessayer={occupe ? undefined : charger} /> : null}

        <div className="creer__action">
          <button type="submit" className="bouton bouton--primaire" disabled={!besoin.trim() || styleId === null || occupe}>
            {occupe ? "Préparation…" : "Proposer les objets →"}
          </button>
          <span className="creer__note">L'app lit ta phrase et te propose une liste d'objets : tu la valides à l'étape suivante.</span>
        </div>
      </form>
    </div>
  );
}
