import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import type { DecisionObjet, MotifJet, ObjetValidation, ValidationVue } from "../../api/types";
import { Chargement, Erreur, EtatVide } from "../../components/Etats";
import type { OutilsScene } from "./Scene3D";
import { pluriel } from "./commun";
import "./Validation.css";

interface Props {
  lotId: number;
  /** Une décision change le projet (étape, compteurs) : l'en-tête se relit. */
  onChangement: () => void;
}

// La 3D (three.js) est lourde : elle ne se charge qu'à l'ouverture de la Validation, pas avec le reste de l'app.
const Scene3D = lazy(() => import("./Scene3D").then((m) => ({ default: m.Scene3D })));

const MOTIFS: Array<{ cle: MotifJet; nom: string }> = [
  { cle: "proportions", nom: "Proportions" },
  { cle: "details_flous", nom: "Détails flous" },
  { cle: "ne_ressemble_pas", nom: "Ne ressemble pas au look" },
  { cle: "hors_style", nom: "Hors du style" },
  { cle: "inutile", nom: "Inutile" },
];

const NOMS_VUES: Record<string, string> = { trois_quarts: "3/4", face: "Face", profil: "Profil", dos: "Dos", dessus: "Dessus" };
const BADGES: Record<string, string> = { garde: "✓", jete: "✕", look: "↻" };
const DEJA_FAIT: Record<string, string> = { garde: "Gardé", jete: "Jeté", look: "Retourné au Look" };

type Reponse = "oui" | "non";
type Question = "look" | "tour" | "taille";
type Panneau = "corriger" | "refaire" | "jeter" | null;
type Onglet = "vues" | "comparer" | "verifs" | "avis";

interface Notification {
  texte: string;
  annuler?: () => void;
  lien?: { vers: string; nom: string };
}

const formatNombre = new Intl.NumberFormat("fr-FR");
const decimales = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Étape 4 · Validation : pour chaque objet fabriqué, un verdict en mots simples, trois questions, et quatre décisions. */
export function Validation({ lotId, onChangement }: Props) {
  const [donnees, setDonnees] = useState<ValidationVue | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [courantId, setCourantId] = useState<number | null>(null);
  const [notification, setNotification] = useState<Notification | null>(null);
  const [occupe, setOccupe] = useState(false);
  const [alerte, setAlerte] = useState<string | null>(null);
  const minuteur = useRef<ReturnType<typeof setTimeout> | null>(null);

  const charger = useCallback(async () => {
    try {
      const v = await api<ValidationVue>(`/lots/${lotId}/validation`);
      setDonnees(v);
      setCourantId((id) => (id !== null && v.objets.some((o) => o.id === id) ? id : (v.objets.find((o) => o.etat === "a_valider") ?? v.objets[0])?.id ?? null));
      setErreur(null);
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, [lotId]);

  useEffect(() => {
    charger();
  }, [charger]);

  useEffect(
    () => () => {
      if (minuteur.current) clearTimeout(minuteur.current);
    },
    [],
  );

  const annoncer = (n: Notification) => {
    setNotification(n);
    if (minuteur.current) clearTimeout(minuteur.current);
    minuteur.current = setTimeout(() => setNotification(null), 8000);
  };

  const decider = async (objet: ObjetValidation, decision: DecisionObjet, corps: { motif?: MotifJet; notes?: string[]; texte?: string } = {}) => {
    setOccupe(true);
    setAlerte(null);
    try {
      await api<ObjetValidation>(`/lots/${lotId}/objets/${objet.id}/decision`, { method: "POST", body: JSON.stringify({ decision, ...corps }) });
      signalerChangement();
      onChangement();
      const v = await api<ValidationVue>(`/lots/${lotId}/validation`);
      setDonnees(v);
      const prochain = v.objets.find((o) => o.etat === "a_valider" && o.id !== objet.id) ?? v.objets.find((o) => o.etat === "a_valider");
      if (decision === "annuler") {
        setCourantId(objet.id);
        setNotification(null);
      } else {
        setCourantId(prochain?.id ?? objet.id);
        if (decision === "garder") annoncer({ texte: `${objet.nom} gardé dans ${v.collection}`, annuler: () => void decider(objet, "annuler") });
        else if (decision === "jeter") annoncer({ texte: `${objet.nom} jeté`, annuler: () => void decider(objet, "annuler") });
        else
          annoncer({
            texte: decision === "corriger" ? `${objet.nom} : 4 nouveaux looks arrivent, avec tes remarques` : `${objet.nom} retourne au Look`,
            lien: { vers: `/lots/${lotId}/references`, nom: "Ouvrir le Look" },
          });
      }
    } catch (e) {
      setAlerte(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  if (erreur) return <Erreur message={erreur} onReessayer={charger} />;
  if (!donnees) return <Chargement />;
  if (donnees.objets.length === 0) {
    return <EtatVide titre="Rien à valider pour l'instant" texte="Les objets arrivent ici dès qu'ils sont fabriqués." enfants={<Link to={`/lots/${lotId}/generation`} className="bouton">Voir la fabrication</Link>} />;
  }

  const courant = donnees.objets.find((o) => o.id === courantId) ?? donnees.objets[0]!;
  const dansLaFile = donnees.objets.filter((o) => o.etat !== "en_fabrication");

  if (donnees.termine) {
    return (
      <div className="validation">
        <FinValidation donnees={donnees} lotId={lotId} onAnnuler={(o) => decider(o, "annuler")} occupe={occupe} />
        {notification ? <Toast n={notification} onFermer={() => setNotification(null)} /> : null}
      </div>
    );
  }

  const aller = (sens: 1 | -1) => {
    const i = dansLaFile.findIndex((o) => o.id === courant.id);
    setCourantId(dansLaFile[(i + sens + dansLaFile.length) % dansLaFile.length]!.id);
  };

  return (
    <div className="validation">
      <div className="validation__file">
        <ul role="list" aria-label="Objets à valider" className="validation__vignettes">
          {donnees.objets.map((o) => (
            <li key={o.id}>
              <button
                type="button"
                className={`validation__vignette${o.id === courant.id ? " est-courante" : ""}${o.etat !== "a_valider" ? " est-decidee" : ""}`}
                aria-label={`${o.nom}${o.etat === "a_valider" ? "" : ` : ${etatTexte(o)}`}`}
                aria-current={o.id === courant.id ? "true" : undefined}
                onClick={() => setCourantId(o.id)}
                disabled={o.etat === "en_fabrication"}
              >
                {vignette(o) ? <img src={vignette(o)!} alt="" /> : <span aria-hidden="true">{o.etat === "en_fabrication" ? "…" : "?"}</span>}
                {BADGES[o.etat] ? <i className={`validation__badge validation__badge--${o.etat}`}>{BADGES[o.etat]}</i> : null}
              </button>
            </li>
          ))}
        </ul>
        <p className="validation__restant" aria-live="polite">
          {donnees.resume.a_valider > 0 ? `${donnees.resume.a_valider} à valider` : "Rien d'autre à valider"}
          {donnees.resume.pas_prets > 0 ? ` · ${donnees.resume.pas_prets} pas encore prêt${donnees.resume.pas_prets > 1 ? "s" : ""}` : ""}
        </p>
        {dansLaFile.length > 1 ? (
          <div className="validation__navigation">
            <button type="button" className="bouton bouton--petit" onClick={() => aller(-1)}>
              ← Précédent
            </button>
            <button type="button" className="bouton bouton--petit" onClick={() => aller(1)}>
              Suivant →
            </button>
          </div>
        ) : null}
      </div>

      <FicheObjet key={courant.id} objet={courant} collection={donnees.collection} occupe={occupe} alerte={alerte} onDecider={(d, c) => decider(courant, d, c)} />
      {notification ? <Toast n={notification} onFermer={() => setNotification(null)} /> : null}
    </div>
  );
}

function vignette(o: ObjetValidation): string | null {
  return o.vues.find((v) => v.nom === "trois_quarts")?.url ?? o.vues[0]?.url ?? o.reference;
}

function etatTexte(o: ObjetValidation): string {
  return DEJA_FAIT[o.etat] ?? (o.etat === "en_fabrication" ? "en fabrication" : "à valider");
}

function Toast({ n, onFermer }: { n: Notification; onFermer: () => void }) {
  return (
    <div className="validation__toast" role="status">
      <span>{n.texte}</span>
      {n.annuler ? (
        <button
          type="button"
          className="validation__toast-action"
          onClick={() => {
            onFermer();
            n.annuler!();
          }}
        >
          Annuler
        </button>
      ) : null}
      {n.lien ? (
        <Link to={n.lien.vers} className="validation__toast-action">
          {n.lien.nom}
        </Link>
      ) : null}
    </div>
  );
}

/** Tout est décidé : le résumé, et la suite du parcours. */
function FinValidation({ donnees, lotId, onAnnuler, occupe }: { donnees: ValidationVue; lotId: number; onAnnuler: (o: ObjetValidation) => void; occupe: boolean }) {
  const { gardes, jetes, total } = donnees.resume;
  return (
    <section aria-labelledby="fin-valid" className="validation__fin">
      <h2 id="fin-valid" className="brief__titre">
        Tout est validé
      </h2>
      <p className="secondaire">
        {gardes === total ? `Les ${pluriel(total, "objet", "objets")} sont dans ta collection « ${donnees.collection} ».` : `${pluriel(gardes, "objet gardé", "objets gardés")}, ${pluriel(jetes, "jeté", "jetés")}.`}
      </p>
      <ul role="list" className="validation__bilan">
        {donnees.objets.map((o) => (
          <li key={o.id}>
            {vignette(o) ? <img src={vignette(o)!} alt="" /> : null}
            <span>
              {o.nom}
              <b>{DEJA_FAIT[o.etat]}</b>
            </span>
            <button type="button" className="bouton bouton--petit" disabled={occupe} onClick={() => onAnnuler(o)} aria-label={`Revenir sur la décision : ${o.nom}`}>
              Revenir dessus
            </button>
          </li>
        ))}
      </ul>
      <div className="validation__fin-actions">
        <Link to={`/lots/${lotId}/essai`} className="bouton bouton--primaire">
          Essayer les objets ensemble →
        </Link>
      </div>
    </section>
  );
}

interface FicheProps {
  objet: ObjetValidation;
  collection: string;
  occupe: boolean;
  alerte: string | null;
  onDecider: (d: DecisionObjet, corps?: { motif?: MotifJet; notes?: string[]; texte?: string }) => void;
}

/** Un objet : la 3D à gauche, le verdict et les décisions à droite. */
function FicheObjet({ objet, collection, occupe, alerte, onDecider }: FicheProps) {
  const [outils, setOutils] = useState<OutilsScene>({ reperes: false, personnage: false, tourner: false });
  const [pointage, setPointage] = useState(false);
  const [onglet, setOnglet] = useState<Onglet>("vues");
  const [panneau, setPanneau] = useState<Panneau>(null);
  const [reponses, setReponses] = useState<Partial<Record<Question, Reponse>>>({});
  const [notes, setNotes] = useState<string[]>([]);
  const [texte, setTexte] = useState("");
  const [motif, setMotif] = useState<MotifJet | null>(null);
  const panneauRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);

  const decide = objet.etat !== "a_valider";
  const verdict = objet.verdict;
  const executes = objet.controles.filter((c) => c.etat !== "non exécuté" && c.etat !== "non demandée");
  const tousOui = (["look", "tour", "taille"] as Question[]).every((q) => reponses[q] === "oui");
  const repondu = Object.keys(reponses).length === 3;

  const versScene = () => sceneRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  const ouvrir = (p: Panneau) => {
    setPanneau(p);
    setTimeout(() => panneauRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 0);
  };
  const repondre = (q: Question, r: Reponse) => setReponses((x) => ({ ...x, [q]: r }));
  const dimensions = objet.faits?.dimensions_m;

  const aide: Record<Question, () => void> = {
    look: () => {
      setOnglet("comparer");
      setTimeout(() => document.getElementById("valid-onglets")?.scrollIntoView({ behavior: "smooth", block: "center" }), 0);
    },
    tour: () => {
      setOutils((o) => ({ ...o, tourner: true }));
      versScene();
    },
    taille: () => {
      setOutils((o) => ({ ...o, personnage: true }));
      versScene();
    },
  };
  const suite: Record<Question, () => void> = {
    look: () => ouvrir("refaire"),
    tour: () => {
      versScene();
      setPointage(true);
    },
    taille: () => ouvrir("corriger"),
  };

  return (
    <div className="validation__fiche">
      <section aria-label={`${objet.nom} en 3D`} className="validation__visionneuse">
        <div ref={sceneRef}>
          {objet.modele ? (
            <Suspense fallback={<div className="scene3d scene3d--vide"><p className="scene3d__etat">Chargement de la 3D…</p></div>}>
            <Scene3D
              modele={objet.modele}
              nom={objet.nom}
              triangles={[objet.faits?.tris.lod0 ?? null, objet.faits?.tris.lod1 ?? null, objet.faits?.tris.lod2 ?? null]}
              outils={outils}
              onOutils={setOutils}
              pointage={pointage}
              onPointage={setPointage}
              onPastilleAjoutee={() => {
                setNotes((n) => [...n, ""]);
                setPanneau("corriger");
                setTimeout(() => panneauRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 0);
              }}
              onPastilleTouchee={() => ouvrir("corriger")}
            />
            </Suspense>
          ) : (
            <div className="scene3d scene3d--vide">
              <p className="scene3d__etat">Le fichier 3D de cet objet n'est pas disponible.</p>
            </div>
          )}
        </div>

        <div className="validation__onglets" id="valid-onglets">
          <div role="tablist" aria-label="Voir l'objet autrement" className="validation__tablist">
            {(
              [
                ["vues", `${pluriel(objet.vues.length, "vue", "vues")}`],
                ["comparer", "Comparer à ton look"],
                ["verifs", `Vérifications ${executes.filter((c) => c.ok).length}/${executes.length}`],
                ["avis", "Avis de l'IA"],
              ] as Array<[Onglet, string]>
            ).map(([cle, nom]) => (
              <button key={cle} type="button" role="tab" aria-selected={onglet === cle} className={onglet === cle ? "est-actif" : ""} onClick={() => setOnglet(cle)}>
                {nom}
              </button>
            ))}
          </div>
          <div role="tabpanel" className="validation__onglet">
            {onglet === "vues" ? (
              objet.vues.length ? (
                <ul role="list" className="validation__vues">
                  {objet.vues.map((v) => (
                    <li key={v.nom}>
                      <img src={v.url} alt={NOMS_VUES[v.nom] ?? v.nom} />
                      <small>{NOMS_VUES[v.nom] ?? v.nom}</small>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="secondaire">Aucune vue n'a été rendue pour cet objet.</p>
              )
            ) : null}
            {onglet === "comparer" ? (
              <div className="validation__comparer">
                <figure>
                  <figcaption>Ton look</figcaption>
                  {objet.reference ? <img src={objet.reference} alt="Le look que tu as choisi" /> : <p className="secondaire">Pas d'image de look pour cet objet.</p>}
                </figure>
                <figure>
                  <figcaption>Objet 3D</figcaption>
                  {vignette(objet) ? <img src={objet.vues[0] ? (objet.vues.find((v) => v.nom === "trois_quarts") ?? objet.vues[0]).url : vignette(objet)!} alt="L'objet fabriqué" /> : <p className="secondaire">Pas de vue.</p>}
                </figure>
              </div>
            ) : null}
            {onglet === "verifs" ? (
              <ul role="list" className="validation__verifs">
                {executes.map((c) => (
                  <li key={c.nom} className={c.ok ? "est-ok" : "est-ko"}>
                    <i aria-hidden="true">{c.ok ? "✓" : "!"}</i>
                    <span>
                      {c.nom}
                      {c.detail ? <small> · {c.detail}</small> : null}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
            {onglet === "avis" ? <p className="validation__avis">{objet.avis_ia ?? "Aucun avis de l'IA pour cet objet : tu es le seul juge, avec les vérifications automatiques."}</p> : null}
          </div>
        </div>
      </section>

      <section aria-labelledby={`objet-${objet.id}`} className="validation__decision" ref={panneauRef}>
        <div>
          <h2 id={`objet-${objet.id}`} className="brief__titre">
            {objet.nom}
          </h2>
          {objet.source ? <p className="secondaire">{objet.source}</p> : null}
        </div>

        {verdict ? (
          <div className={`verdict verdict--${verdict.etat}`}>
            <p className="verdict__titre">
              <i aria-hidden="true">{verdict.etat === "ok" ? "✓" : "!"}</i>
              {verdict.etat === "ok" ? "Prêt à garder" : "À regarder avant de garder"}
            </p>
            <ul role="list" className="verdict__raisons">
              {verdict.raisons.map((r) => (
                <li key={r.texte} className={r.ok ? "" : "est-ko"}>
                  {r.texte}
                </li>
              ))}
            </ul>
            {verdict.autres_ok > 0 ? <p className="verdict__autres">+ {pluriel(verdict.autres_ok, "autre vérification réussie", "autres vérifications réussies")}</p> : null}
          </div>
        ) : null}

        {decide ? (
          <div className="validation__deja">
            <p>
              <b>{DEJA_FAIT[objet.etat]}.</b> {objet.peut_annuler ? "Tu peux revenir sur ta décision." : ""}
            </p>
            {objet.peut_annuler ? (
              <button type="button" className="bouton" disabled={occupe} onClick={() => onDecider("annuler")}>
                Revenir sur ma décision
              </button>
            ) : null}
          </div>
        ) : (
          <>
            <div className="guide" role="group" aria-label="Regarde l'objet en 3 questions">
              <p className="guide__titre">Regarde-le en 3 questions</p>
              {(
                [
                  ["look", "Ressemble-t-il à ton image ?", "Voir côte à côte avec ton image", "Un autre look de la série collera peut-être mieux.", "Refaire avec un autre look"],
                  ["tour", "Tourne-le : tout est bien de chaque côté ?", "Le faire tourner tout seul", "Montre l'endroit : pointe le défaut sur l'objet, puis lance la correction.", "＋ Pointer un défaut"],
                  ["taille", "La taille te paraît juste ?", "Le voir à côté d'un personnage", "Dis-le dans tes remarques : l'app en tient compte pour redessiner l'objet.", "Écrire une remarque"],
                ] as Array<[Question, string, string, string, string]>
              ).map(([q, intitule, lienAide, texteSuite, boutonSuite]) => (
                <div key={q} className="guide__question">
                  <div className="guide__ligne">
                    <span id={`q-${q}`}>{intitule}</span>
                    <div role="group" aria-labelledby={`q-${q}`} className="guide__reponses">
                      <button type="button" aria-pressed={reponses[q] === "oui"} className={reponses[q] === "oui" ? "est-oui" : ""} onClick={() => repondre(q, "oui")}>
                        Oui
                      </button>
                      <button type="button" aria-pressed={reponses[q] === "non"} className={reponses[q] === "non" ? "est-non" : ""} onClick={() => repondre(q, "non")}>
                        Non
                      </button>
                    </div>
                  </div>
                  <button type="button" className="lien-bouton" onClick={aide[q]}>
                    {lienAide}
                  </button>
                  {reponses[q] === "non" ? (
                    <div className="guide__suite">
                      <p>{texteSuite}</p>
                      <button type="button" className="bouton bouton--petit" onClick={suite[q]}>
                        {boutonSuite}
                      </button>
                    </div>
                  ) : null}
                </div>
              ))}
              {repondu ? (
                <p className={`guide__bilan ${tousOui ? "est-bon" : "est-doute"}`}>
                  {tousOui ? "✓ Tout te paraît bon : tu peux le garder." : "Suis la suggestion en orange, ou garde-le quand même si ça te va."}
                </p>
              ) : null}
            </div>

            <details className="validation__details">
              <summary>Détails techniques</summary>
              <dl>
                <div>
                  <dt>Taille</dt>
                  <dd>{dimensions ? `${decimales.format(dimensions[0])} × ${decimales.format(dimensions[1])} × ${decimales.format(dimensions[2])} m` : "—"}</dd>
                </div>
                <div>
                  <dt>Finesse</dt>
                  <dd>{objet.faits?.tris.lod0 ? `${formatNombre.format(objet.faits.tris.lod0)} triangles · 3 détails` : "—"}</dd>
                </div>
                <div>
                  <dt>Coût</dt>
                  <dd>{objet.faits ? `${pluriel(objet.faits.credits, "crédit", "crédits")} · essai ${objet.faits.nombre_essais}` : "—"}</dd>
                </div>
              </dl>
            </details>

            <div className="validation__boutons">
              <button type="button" className={`bouton bouton--primaire validation__garder${tousOui ? " est-conseille" : ""}`} disabled={occupe} onClick={() => onDecider("garder")}>
                ✓ Garder dans {collection}
              </button>
              <div className="validation__deux">
                <button type="button" className="bouton" aria-expanded={panneau === "corriger"} onClick={() => ouvrir(panneau === "corriger" ? null : "corriger")}>
                  Corriger
                </button>
                <button type="button" className="bouton" aria-expanded={panneau === "refaire"} onClick={() => ouvrir(panneau === "refaire" ? null : "refaire")}>
                  Refaire
                </button>
              </div>

              {panneau === "corriger" ? (
                <div className="validation__sous" role="group" aria-label="Corriger">
                  {objet.peut_corriger ? (
                    <>
                      <p className="secondaire">
                        L'app redessine 4 nouveaux looks en tenant compte de tes remarques, puis tu choisis celui qui te plaît. {pluriel(objet.credits_correction, "crédit", "crédits")}.
                      </p>
                      {notes.length > 0 ? (
                        <ul role="list" className="validation__notes">
                          {notes.map((n, i) => (
                            <li key={i}>
                              <b aria-hidden="true">{i + 1}</b>
                              <input className="champ" aria-label={`Défaut ${i + 1}`} placeholder="Ce qui ne va pas ici…" value={n} onChange={(e) => setNotes((x) => x.map((v, k) => (k === i ? e.target.value : v)))} />
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="secondaire">Astuce : « ＋ Pointer un défaut » sur la vue 3D pour montrer où ça ne va pas.</p>
                      )}
                      <label className="validation__champ">
                        Tes remarques
                        <textarea className="champ" rows={3} value={texte} placeholder="Ex. terre cuite plus claire, anses plus épaisses" onChange={(e) => setTexte(e.target.value)} />
                      </label>
                      <button
                        type="button"
                        className="bouton bouton--primaire"
                        disabled={occupe || (!texte.trim() && !notes.some((n) => n.trim()))}
                        onClick={() => onDecider("corriger", { notes: notes.filter((n) => n.trim()), texte })}
                      >
                        Redessiner les looks
                      </button>
                    </>
                  ) : (
                    <p className="secondaire">Un objet fait par script se règle par ses variantes : utilise « Refaire » pour en choisir une autre.</p>
                  )}
                </div>
              ) : null}

              {panneau === "refaire" ? (
                <div className="validation__sous" role="group" aria-label="Refaire">
                  <p className="secondaire">Tu reviens au Look de cet objet pour choisir une autre image ou une autre version. Gratuit : rien n'est refait tant que tu n'as pas relancé la fabrication.</p>
                  <button type="button" className="bouton bouton--primaire" disabled={occupe} onClick={() => onDecider("refaire")}>
                    Revenir au Look
                  </button>
                </div>
              ) : null}

              <button type="button" className="bouton validation__jeter" aria-expanded={panneau === "jeter"} onClick={() => ouvrir(panneau === "jeter" ? null : "jeter")}>
                Jeter cet objet
              </button>
              {panneau === "jeter" ? (
                <div className="validation__sous" role="group" aria-label="Jeter">
                  <p className="secondaire">Pourquoi ? (ça améliore les prochaines propositions)</p>
                  <div className="validation__motifs">
                    {MOTIFS.map((m) => (
                      <button key={m.cle} type="button" aria-pressed={motif === m.cle} className={motif === m.cle ? "est-actif" : ""} onClick={() => setMotif(motif === m.cle ? null : m.cle)}>
                        {m.nom}
                      </button>
                    ))}
                  </div>
                  <button type="button" className="bouton validation__jeter" disabled={occupe} onClick={() => onDecider("jeter", motif ? { motif } : {})}>
                    Jeter l'objet
                  </button>
                </div>
              ) : null}
            </div>
          </>
        )}
        {alerte ? (
          <p role="alert" className="entete-lot__message">
            {alerte}
          </p>
        ) : null}
      </section>

      {!decide ? (
        <div className="validation__barre" role="group" aria-label="Décider">
          <button type="button" className="bouton validation__jeter" onClick={() => ouvrir("jeter")}>
            Jeter
          </button>
          <button type="button" className="bouton" onClick={() => ouvrir("refaire")}>
            Refaire
          </button>
          <button type="button" className="bouton" onClick={() => ouvrir("corriger")}>
            Corriger
          </button>
          <button type="button" className="bouton bouton--primaire" disabled={occupe} onClick={() => onDecider("garder")}>
            ✓ Garder
          </button>
        </div>
      ) : null}
    </div>
  );
}
