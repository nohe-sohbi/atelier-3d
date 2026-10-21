import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import type { Generation as GenerationApi } from "../../api/types";
import { Chargement, Erreur } from "../../components/Etats";
import { EtatDuWorker, ListeTaches } from "../../components/Taches";
import { formatNombre, pluriel } from "./commun";

/** Relecture toutes les 2 s quand quelque chose tourne, toutes les 15 s sinon. */
const RAPIDE_MS = 2000;
const LENT_MS = 15000;

interface Props {
  lotId: number;
  /** Le lot a changé (une tâche relancée, annulée) : l'en-tête se relit. */
  onChangement: () => void;
}

/** Lot · 3 Génération (Generation.dc.html) : ce qui se fabrique, ce qui tourne, ce que ça coûte. */
export function Generation({ lotId, onChangement }: Props) {
  const [g, setG] = useState<GenerationApi | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [alerte, setAlerte] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);
  const minuteur = useRef<number | null>(null);
  const naviguer = useNavigate();

  const avancement = useRef<string | null>(null);

  const charger = useCallback(async () => {
    try {
      const lu = await api<GenerationApi>(`/lots/${lotId}/generation`);
      setG(lu);
      setErreur(null);
      // Le worker fait avancer le lot sans l'écran : l'en-tête (étapes, ligne d'état) se relit quand l'avancement change.
      const signature = lu.objets.map((o) => `${o.id}:${o.statut}`).join("|");
      if (avancement.current !== null && avancement.current !== signature) onChangement();
      avancement.current = signature;
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, [lotId, onChangement]);

  useEffect(() => {
    charger();
  }, [charger]);

  // Tant que des tâches tournent ou attendent, l'écran suit ; sinon il se relit lentement.
  useEffect(() => {
    if (!g) return;
    const actif = g.taches.some((t) => t.etat === "en_cours" || t.etat === "en_attente") || g.tuiles.en_cours > 0;
    minuteur.current = window.setTimeout(charger, actif ? RAPIDE_MS : LENT_MS);
    return () => {
      if (minuteur.current !== null) window.clearTimeout(minuteur.current);
    };
  }, [g, charger]);

  const changement = useCallback(() => {
    charger();
    onChangement();
  }, [charger, onChangement]);

  const agir = async (action: () => Promise<void>) => {
    setAlerte(null);
    setOccupe(true);
    try {
      await action();
    } catch (e) {
      setAlerte(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  /** « Refaire » : un nouvel essai du même objet, avec la même référence (utile si l'échec venait de la machine). */
  const refaire = (objetId: number) =>
    agir(async () => {
      await api(`/lots/${lotId}/fabriquer`, { method: "POST", body: JSON.stringify({ objet_id: objetId }) });
      signalerChangement();
      changement();
    });

  /** « Choisir une autre version » (code) ou « une autre image » (IA) : l'objet revient aux Références. */
  const rechoisir = (objetId: number) =>
    agir(async () => {
      await api(`/lots/${lotId}/objets/${objetId}/rouvrir`, { method: "POST" });
      signalerChangement();
      onChangement();
      naviguer(`/lots/${lotId}/references`);
    });

  if (erreur && !g) return <Erreur message={erreur} onReessayer={charger} />;
  if (!g) return <Chargement />;

  const t = g.tuiles;
  return (
    <div className="generation">
      <div className="generation__principal">
        <div>
          <h2 className="brief__titre">Génération</h2>
          <p className="brief__texte">
            Rien à faire ici : finition, tests et relances sont automatiques. Une notification arrive quand la revue est prête.
          </p>
        </div>

        <ul role="list" aria-label="Où en est la fabrication" className="generation__tuiles">
          <li className="generation__tuile">
            <span className="generation__tuile-titre">Prêts pour la revue</span>
            <span className="generation__chiffre generation__chiffre--succes">
              {t.prets_revue}
              <span className="generation__sur"> / {t.fabriques}</span>
            </span>
          </li>
          <li className="generation__tuile">
            <span className="generation__tuile-titre">En cours</span>
            <span className="generation__chiffre">{t.en_cours}</span>
          </li>
          <li className="generation__tuile">
            <span className="generation__tuile-titre">Relances auto</span>
            <span className={`generation__chiffre${t.relances > 0 ? " generation__chiffre--alerte" : ""}`}>{t.relances}</span>
          </li>
          <li className="generation__tuile">
            <span className="generation__tuile-titre">Crédits Meshy du lot</span>
            <span className="generation__chiffre">
              {formatNombre.format(t.credits_utilises)}
              <span className="generation__sur"> utilisés{t.credits_simules ? " · simulé" : ""}</span>
            </span>
            <span className="generation__tuile-note">{pluriel(t.credits_prevus, "prévu", "prévus")} à la validation du brief</span>
          </li>
        </ul>

        <EtatDuWorker worker={g.worker} />

        <section aria-labelledby="file-lot-h" className="generation__carte">
          <h2 id="file-lot-h" className="generation__h">
            File du lot
          </h2>
          <p className="generation__texte">
            Trois files tournent en parallèle : Blender ({g.limites_files.blender ?? "?"} à la fois), Meshy ({g.limites_files.meshy ?? "?"}) et ta carte
            graphique ({g.limites_files.gpu ?? "?"}). Les tâches sont enregistrées : si l'ordinateur s'éteint, elles reprennent au redémarrage.
            {g.reutilises.length > 0 ? ` Réutilisés depuis ta bibliothèque, rien à fabriquer : ${g.reutilises.join(", ")}.` : ""}
          </p>
          {g.fabrication.autres_voies > 0 ? <p className="generation__a-venir">{g.fabrication.raison_ia}.</p> : null}
          {alerte ? (
            <div role="alert" className="brief__alerte">
              {alerte}
            </div>
          ) : null}
          {g.objets.length === 0 ? (
            <p className="secondaire">Aucun objet à fabriquer dans ce lot : valide le brief, puis choisis les références.</p>
          ) : (
            <ul role="list" aria-label="Objets du lot" className="generation__objets">
              {g.objets.map((o) => (
                <li key={o.id} className="generation__objet">
                  <div className="generation__vignette">
                    {o.vignette ? <img src={o.vignette} alt={`Vignette de ${o.nom}`} width={56} height={56} /> : null}
                  </div>
                  <div className="generation__objet-texte">
                    <span className="generation__objet-nom">{o.nom}</span>
                    <span className="generation__fournisseur mono">{o.fournisseur}</span>
                  </div>
                  <ol role="list" aria-label={`Étapes de ${o.nom}`} className="generation__puces">
                    {o.etapes.map((p) => (
                      <li key={p.cle} className={`generation__puce generation__puce--${p.etat}`}>
                        {p.libelle}
                        <span className="visuellement-cache">
                          {" "}
                          : {p.etat === "fait" ? "fait" : p.etat === "en_cours" ? "en cours" : p.etat === "echec" ? "en échec" : "à faire"}
                        </span>
                      </li>
                    ))}
                  </ol>
                  <div className="generation__statut">
                    <span className={`generation__statut-texte generation__statut-texte--${o.ton}`}>{o.statut}</span>
                    <div className="generation__barre" aria-hidden="true">
                      <div className={`generation__barre-plein generation__barre-plein--${o.ton}`} style={{ width: `${o.pct}%` }} />
                    </div>
                    <div className="generation__liens">
                      {o.planche ? (
                        <a href={o.planche} target="_blank" rel="noreferrer">
                          Voir la planche
                        </a>
                      ) : null}
                      {o.asset_id ? <span className="mono secondaire">{o.asset_id}</span> : null}
                      {o.peut_rechoisir ? (
                        <button type="button" className="bouton bouton--petit" onClick={() => rechoisir(o.id)} disabled={occupe}>
                          {o.voie === "ia" ? "Choisir une autre image" : "Choisir une autre version"}
                        </button>
                      ) : null}
                      {o.peut_fabriquer && o.essai ? (
                        <button type="button" className="bouton bouton--petit" onClick={() => refaire(o.id)} disabled={occupe}>
                          Refaire (essai {o.essai.numero + 1})
                        </button>
                      ) : null}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="taches-lot-h" className="generation__carte">
          <h2 id="taches-lot-h" className="generation__h">
            Tâches du lot
          </h2>
          <ListeTaches taches={g.taches} onChangement={changement} vide="Aucune tâche pour ce lot pour l'instant." />
        </section>

        <div className="generation__pied">
          <Link to={`/lots/${lotId}/references`} className="bouton">
            Retour aux références
          </Link>
          {t.prets_revue > 0 ? (
            <Link to={`/lots/${lotId}/revue`} className="bouton bouton--primaire">
              Ouvrir la revue · {pluriel(t.prets_revue, "prêt", "prêts")}
            </Link>
          ) : (
            <button type="button" className="bouton bouton--primaire" disabled title="Aucun objet prêt pour la revue">
              Ouvrir la revue · 0 prêt
            </button>
          )}
        </div>
      </div>

      <aside aria-labelledby="generateurs-h" className="generation__carte generation__cote">
        <div>
          <h2 id="generateurs-h" className="generation__h">
            Générateurs branchés
          </h2>
          <p className="generation__texte">Chacun est un adaptateur interchangeable. Tu en changes sans toucher au style, aux tests ni à la bibliothèque.</p>
        </div>
        <ul role="list" className="generation__generateurs">
          {g.generateurs.map((x) => (
            <li key={x.nom} className="generation__generateur">
              <div>
                <span className="generation__objet-nom">{x.nom}</span>
                <span className="generation__fournisseur">{x.detail}</span>
              </div>
              <span className={`ton ton--${x.ton}`}>{x.etat}</span>
            </li>
          ))}
        </ul>
        <Link to="/generateurs" className="bouton">
          Gérer les générateurs
        </Link>
      </aside>
    </div>
  );
}
