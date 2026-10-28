import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import type { Lancement, ObjetReferences, Proposition, References as ReferencesApi } from "../../api/types";
import { Chargement, Erreur } from "../../components/Etats";
import { LIBELLES_VOIES, pluriel } from "./commun";

/** Relecture toutes les 2 s pendant qu'une préparation tourne, toutes les 15 s sinon. */
const RAPIDE_MS = 2000;
const LENT_MS = 15000;

interface Props {
  lotId: number;
  /** Le lot a changé (un choix, un lancement) : l'en-tête se relit. */
  onChangement: () => void;
}

function IconeRefaire() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M13 3 V6.5 H9.5 M12.6 6.2 A5 5 0 1 0 13 9.5" className="references__trait" />
    </svg>
  );
}

function IconeCrayon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M3 13 L3.6 10.4 L10.8 3.2 L12.8 5.2 L5.6 12.4 Z M9.6 4.4 L11.6 6.4" className="references__trait" />
    </svg>
  );
}

function IconeImage() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M2.5 3.5 H13.5 V12.5 H2.5 Z M2.5 10.5 L6 7.5 L9 10 L11 8.5 L13.5 10.5 M10.5 6 A1 1 0 1 0 10.49 6" className="references__trait" />
    </svg>
  );
}

function IconeChoisie() {
  return (
    <span className="references__coche" aria-hidden="true">
      <svg width="12" height="12" viewBox="0 0 12 12">
        <path d="M2.5 6.2 L5 8.5 L9.5 3.5" />
      </svg>
    </span>
  );
}

/** Ce que reçoit l'objet : « 4 images · 12 crédits », « 4 versions du générateur · gratuites ». */
function texteGenre(o: ObjetReferences, credits: number): string {
  if (o.genre === "variantes") return "4 versions du générateur · gratuites";
  const images = `4 images · ${pluriel(credits, "crédit", "crédits")}`;
  return o.piece_ia ? `Pièce IA seulement (${o.piece_ia}) · ${images}` : images;
}

function libelleTuile(o: ObjetReferences, p: Proposition, i: number, n: number): string {
  if (p.genre === "perso") return `Ton image pour ${o.nom}`;
  if (p.genre === "variante") return `Version ${i + 1} sur ${n} pour ${o.nom} : ${p.legende}`;
  return `Image ${i + 1} sur ${n} pour ${o.nom}`;
}

interface CarteProps {
  lotId: number;
  o: ObjetReferences;
  credits: number;
  onObjet: (o: ObjetReferences) => void;
  onRecharger: () => void;
}

/** Un objet : ses propositions, « 4 autres », sa consigne et ton image (objets IA). */
function CarteObjet({ lotId, o, credits, onObjet, onRecharger }: CarteProps) {
  const [alerte, setAlerte] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);
  const [edition, setEdition] = useState<string | null>(null);
  const refFichier = useRef<HTMLInputElement>(null);
  const base = `/lots/${lotId}/objets/${o.id}`;
  const prepare = o.preparation !== null;
  const actif = o.peut_changer && !occupe;

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

  const choisir = (p: Proposition) =>
    agir(async () => {
      onObjet(await api<ObjetReferences>(`${base}/reference`, { method: "PUT", body: JSON.stringify({ proposition_id: p.id }) }));
      signalerChangement();
    });

  const quatreAutres = (modeleId?: number) =>
    agir(async () => {
      const r = await api<{ objet: ObjetReferences }>(`${base}/propositions`, {
        method: "POST",
        body: JSON.stringify(modeleId === undefined ? {} : { modele_id: modeleId }),
      });
      onObjet(r.objet);
    });

  const enregistrerConsigne = (texte: string) =>
    agir(async () => {
      await api<ObjetReferences>(`${base}/consigne`, { method: "PUT", body: JSON.stringify({ consigne: texte }) });
      const r = await api<{ objet: ObjetReferences }>(`${base}/propositions`, { method: "POST", body: JSON.stringify({}) });
      onObjet(r.objet);
      setEdition(null);
    });

  const revenirConsigneApp = () =>
    agir(async () => {
      const r = await api<ObjetReferences>(`${base}/consigne`, { method: "PUT", body: JSON.stringify({ consigne: "" }) });
      onObjet(r);
      setEdition(r.consigne ?? "");
    });

  const envoyerImage = (fichier: File) =>
    agir(async () => {
      const fd = new FormData();
      fd.append("fichier", fichier);
      onObjet(await api<ObjetReferences>(`${base}/image`, { method: "POST", body: fd }));
      signalerChangement();
    });

  const reessayer = (tacheId: number) =>
    agir(async () => {
      await api(`/taches/${tacheId}/relancer`, { method: "POST" });
      onRecharger();
    });

  // Pendant une préparation, la série en cours remplace la précédente ; ton image et le choix restent visibles.
  const visibles = prepare ? o.propositions.filter((p) => p.genre === "perso" || p.choisie) : o.propositions;
  const serie = visibles.filter((p) => p.genre !== "perso");
  const choisie = o.propositions.find((p) => p.choisie);

  return (
    <section aria-labelledby={`ref-${o.id}`} className="references__carte">
      <div className="references__entete">
        <h3 id={`ref-${o.id}`} className="references__nom">
          {o.nom}
        </h3>
        <span className={`voie voie--${o.voie}`}>{LIBELLES_VOIES[o.voie]}</span>
        <span className="references__genre">{texteGenre(o, credits)}</span>
        {o.peut_changer ? (
          <div className="references__actions">
            {o.genre === "images" ? (
              <>
                <button
                  type="button"
                  className="references__icone"
                  aria-label={`Modifier la consigne de ${o.nom}`}
                  title="Modifier la consigne envoyée à l'IA"
                  aria-expanded={edition !== null}
                  onClick={() => setEdition(edition === null ? (o.consigne ?? "") : null)}
                  disabled={!actif}
                >
                  <IconeCrayon />
                </button>
                <input
                  ref={refFichier}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="visuellement-cache"
                  aria-label={`Choisir ton image pour ${o.nom}`}
                  tabIndex={-1}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    e.target.value = "";
                    if (f) envoyerImage(f);
                  }}
                />
                <button
                  type="button"
                  className="references__icone"
                  aria-label={`Ajouter ton image pour ${o.nom}`}
                  title="Ajouter ta propre image (photo, dessin)"
                  onClick={() => refFichier.current?.click()}
                  disabled={!actif}
                >
                  <IconeImage />
                </button>
              </>
            ) : null}
            <button type="button" className="references__autres" onClick={() => quatreAutres()} disabled={!actif || prepare}>
              <IconeRefaire />
              {o.genre === "images" ? `4 autres · ${pluriel(credits, "crédit", "crédits")}` : "4 autres versions"}
            </button>
          </div>
        ) : null}
      </div>

      {edition !== null ? (
        <div className="references__consigne">
          <label htmlFor={`consigne-${o.id}`} className="references__consigne-titre">
            Consigne envoyée à l'IA
          </label>
          <textarea id={`consigne-${o.id}`} rows={4} className="brief__saisie" value={edition} onChange={(e) => setEdition(e.target.value)} />
          <p className="references__aide">Décris ce que tu veux voir : forme, matières, détails. Les 4 prochaines images suivront cette phrase.</p>
          <div className="references__consigne-boutons">
            <button
              type="button"
              className="bouton bouton--primaire bouton--petit"
              onClick={() => enregistrerConsigne(edition)}
              disabled={occupe || prepare || !edition.trim()}
            >
              Refaire 4 images avec cette consigne · {pluriel(credits, "crédit", "crédits")}
            </button>
            <button type="button" className="bouton bouton--petit" onClick={() => setEdition(null)} disabled={occupe}>
              Annuler
            </button>
            {o.consigne_modifiee ? (
              <button type="button" className="brief__lien" onClick={revenirConsigneApp} disabled={occupe}>
                Revenir à la consigne de l'app
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {o.erreur && !prepare ? (
        <div role="alert" className="references__erreur">
          <span>Préparation en échec : {o.erreur.message}</span>
          {o.erreur.peut_relancer && o.peut_changer ? (
            <button type="button" className="bouton bouton--petit" onClick={() => reessayer(o.erreur!.tache_id)} disabled={occupe}>
              Réessayer
            </button>
          ) : null}
        </div>
      ) : null}

      <ul role="list" aria-label={`Propositions pour ${o.nom}`} className="references__tuiles">
        {prepare
          ? [0, 1, 2, 3].map((i) => (
              <li key={`attente-${i}`} className="references__tuile references__tuile--attente">
                <span className="references__attente">
                  {i === 0 ? (o.preparation!.etat === "en_attente" ? "En attente…" : (o.preparation!.texte ?? "En préparation…")) : ""}
                </span>
              </li>
            ))
          : null}
        {visibles.map((p) => (
          <li key={p.id} className="references__case">
            <button
              type="button"
              className={`references__tuile${p.choisie ? " references__tuile--choisie" : ""}`}
              aria-pressed={p.choisie}
              aria-label={libelleTuile(o, p, serie.indexOf(p), serie.length)}
              onClick={() => choisir(p)}
              disabled={!actif}
            >
              <img src={p.url} alt="" className="references__image" />
              {p.choisie ? <IconeChoisie /> : null}
              {p.simule ? <span className="pastille pastille--neutre references__simule">simulé</span> : null}
              {p.legende ? <span className="references__legende">{p.legende}</span> : null}
            </button>
          </li>
        ))}
        {!prepare && visibles.length === 0 && !o.erreur && o.peut_changer ? (
          <li className="references__vide">
            <button type="button" className="bouton bouton--petit" onClick={() => quatreAutres()} disabled={!actif}>
              Préparer 4 propositions
            </button>
          </li>
        ) : null}
      </ul>

      {choisie?.genre === "perso" && o.peut_changer ? (
        <div className="references__perso">
          <span className="secondaire">Ton image servira telle quelle. Tu peux aussi en tirer 4 images dans ton style.</span>
          <button type="button" className="bouton bouton--petit" onClick={() => quatreAutres(choisie.id)} disabled={!actif || prepare}>
            4 images d'après ton image · {pluriel(credits, "crédit", "crédits")}
          </button>
        </div>
      ) : null}
      {!o.peut_changer ? <p className="secondaire">Lancé : son look ne change plus. Suis-le dans Fabrication.</p> : null}
      {alerte ? (
        <div role="alert" className="brief__alerte">
          {alerte}
        </div>
      ) : null}
    </section>
  );
}

/** Projet · 2 Look : un look par objet, puis « Lancer la fabrication 3D ». */
export function References({ lotId, onChangement }: Props) {
  const [r, setR] = useState<ReferencesApi | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [alerte, setAlerte] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);
  const naviguer = useNavigate();

  const charger = useCallback(async () => {
    try {
      setR(await api<ReferencesApi>(`/lots/${lotId}/references`));
      setErreur(null);
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, [lotId]);

  useEffect(() => {
    charger();
  }, [charger]);

  useEffect(() => {
    if (!r) return;
    const actif = r.objets.some((o) => o.preparation !== null);
    const minuteur = window.setTimeout(charger, actif ? RAPIDE_MS : LENT_MS);
    return () => window.clearTimeout(minuteur);
  }, [r, charger]);

  /** Un objet a changé (choix, consigne, 4 autres, image) : on le remplace, puis on relit le tout (compteurs). */
  const objetChange = useCallback(
    (o: ObjetReferences) => {
      setR((prec) => (prec ? { ...prec, objets: prec.objets.map((x) => (x.id === o.id ? o : x)) } : prec));
      charger();
      onChangement();
    },
    [charger, onChangement],
  );

  const lancer = async () => {
    setAlerte(null);
    setOccupe(true);
    try {
      await api<Lancement>(`/lots/${lotId}/lancer`, { method: "POST" });
      signalerChangement();
      onChangement();
      naviguer(`/lots/${lotId}/generation`);
    } catch (e) {
      setAlerte(messageErreur(e));
      setOccupe(false);
    }
  };

  if (erreur && !r) return <Erreur message={erreur} onReessayer={charger} />;
  if (!r) return <Chargement />;

  const pct = r.a_choisir ? Math.round((100 * r.choisies) / r.a_choisir) : 100;
  const s = r.style;
  return (
    <div className="references">
      <div className="references__principal">
        <div className="references__titre-ligne">
          <div className="references__intro">
            <h2 className="brief__titre">Choisis un look par objet</h2>
            <p className="brief__texte">
              Objets faits par IA : 4 images dans ton style ({pluriel(r.credits_serie, "crédit", "crédits")} la série), ta consigne si tu la réécris, ou ta
              propre image. Objets faits par code : 4 versions rendues par Blender, gratuites. Ton choix sert d'entrée à la fabrication.
            </p>
          </div>
          {r.a_choisir > 0 ? (
            <div className="references__progression">
              <span>
                {r.choisies} sur {r.a_choisir} {r.a_choisir > 1 ? "choisies" : "choisie"}
              </span>
              <div className="references__barre" aria-hidden="true">
                <div className="references__barre-plein" style={{ width: `${pct}%` }} />
              </div>
            </div>
          ) : null}
        </div>

        {r.meshy_simule ? (
          <p className="brief__simule">
            <span className="pastille pastille--neutre">simulé</span> Images simulées : Meshy est en mode simulé (Réglages). Elles servent à essayer
            l'écran, sans dépenser de crédits.
          </p>
        ) : null}

        {r.objets.length === 0 ? (
          <p className="secondaire">Aucun objet n'attend de look : valide d'abord la liste d'objets.</p>
        ) : (
          <div className="references__grille">
            {r.objets.map((o) => (
              <CarteObjet key={o.id} lotId={lotId} o={o} credits={r.credits_serie} onObjet={objetChange} onRecharger={charger} />
            ))}
          </div>
        )}

        {alerte ? (
          <div role="alert" className="brief__alerte">
            {alerte}
          </div>
        ) : null}

        <div className="references__pied">
          <Link to={`/lots/${lotId}/brief`} className="bouton">
            Retour au brief
          </Link>
          <div className="references__lancer">
            {r.sans_choix.length > 0 ? (
              <span className="references__manque">
                {pluriel(r.sans_choix.length, "objet", "objets")} sans look : {r.sans_choix.join(", ")}
                {r.sans_choix.length > 1 ? " seront mis de côté" : " sera mis de côté"}
              </span>
            ) : null}
            {r.sans_reference.length > 0 ? <span className="secondaire">Sans look à choisir : {r.sans_reference.join(", ")}</span> : null}
            <button type="button" className="bouton bouton--primaire" onClick={lancer} disabled={occupe || !r.peut_lancer}>
              Lancer la fabrication 3D
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                <path d="M3 8 H13 M9 4 L13 8 L9 12" className="references__trait" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <aside aria-labelledby="style-lot-h" className="generation__carte references__style">
        <div>
          <h2 id="style-lot-h" className="generation__h">
            Style du projet
          </h2>
          <p className="mono secondaire references__code">{s.code}</p>
          <p className="generation__texte">Ton moodboard, sous forme de règles : palette et budgets pour tout le projet, matériaux partagés pour la voie code.</p>
        </div>
        <div>
          <h3 className="references__h3">Palette</h3>
          <ul role="list" className="references__palette">
            {s.palette.map((c) => (
              <li key={c.nom}>
                <span className="references__pastille-couleur" style={{ background: c.hex }} />
                <span className="secondaire">{c.nom.replace(/_/g, " ")}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="references__h3">Matériaux partagés · voie code</h3>
          <ul role="list" className="references__materiaux">
            {s.materiaux.map((m) => (
              <li key={m}>{m.replace(/_/g, " ")}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="references__h3">Budgets et échelle</h3>
          <dl className="references__budgets">
            {s.budgets.map((b) => (
              <div key={b.libelle}>
                <dt>{b.libelle}</dt>
                <dd className="mono">{b.tris === null ? "—" : `${b.tris.toLocaleString("fr-FR")} tris`}</dd>
              </div>
            ))}
            <div>
              <dt>Densité de texels</dt>
              <dd className="mono">{s.texel_density} px/m</dd>
            </div>
            <div>
              <dt>Unité</dt>
              <dd className="mono">{s.unite}</dd>
            </div>
          </dl>
        </div>
        <Link to={`/styles?style=${s.code}`} className="bouton">
          Modifier le style
        </Link>
      </aside>
    </div>
  );
}
