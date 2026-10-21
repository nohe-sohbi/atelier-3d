import { useEffect, useMemo, useRef, useState } from "react";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import { ATTENTE_WORKER_MS, AttenteAbandonnee, attendreTache } from "../../api/taches";
import type { Couleur, EstimationPlanche, ImagePlanche, StyleDetail, StyleEnvoye, StyleResume, Tache, TacheLancee } from "../../api/types";
import { Fenetre } from "../../components/Fenetre";
import { coutPlanche, lireDimensions, pluriel, slug } from "./commun";

const CATEGORIES: Array<[string, string]> = [
  ["petit_prop", "Petit objet"],
  ["prop_moyen", "Objet moyen"],
  ["grand_prop", "Grand objet"],
  ["module_archi", "Module d'architecture"],
];

interface Props {
  ouverte: boolean;
  onFermer: () => void;
  /** Styles existants : palette et budgets « à reprendre ». */
  styles: StyleResume[];
  /** Un style déjà créé dont on complète la planche : la fenêtre s'ouvre à l'étape 2. */
  styleExistant: StyleDetail | null;
  /** Tarif de l'adaptateur Meshy (GET /api/styles/estimation-planche) ; null s'il n'a pas pu être lu. */
  estimation: EstimationPlanche | null;
  onTermine: (styleId: number) => void;
}

interface Ligne {
  nom: string;
  hex: string;
}

export function NouveauStyle({ ouverte, onFermer, styles, styleExistant, estimation, onTermine }: Props) {
  const [etape, setEtape] = useState<1 | 2>(1);
  const [nom, setNom] = useState("");
  const [code, setCode] = useState("");
  const [codeModifie, setCodeModifie] = useState(false);
  const [description, setDescription] = useState("");
  const [refId, setRefId] = useState<number | null>(null);
  const [palette, setPalette] = useState<Ligne[]>([]);
  const [paletteTouchee, setPaletteTouchee] = useState(false);
  const [budgets, setBudgets] = useState<Record<string, string>>({});
  const [texel, setTexel] = useState("");
  const [dimensions, setDimensions] = useState("");
  const [fichiers, setFichiers] = useState<File[]>([]);
  /** La palette vient de tes images : combien, ou null (reprise d'un style). */
  const [paletteDesImages, setPaletteDesImages] = useState<number | null>(null);
  const [lecture, setLecture] = useState(false);
  const [cree, setCree] = useState<StyleDetail | null>(null);
  const [tache, setTache] = useState<Tache | null>(null);
  const [enAttenteMs, setEnAttenteMs] = useState(0);
  const [occupe, setOccupe] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const refFichiers = useRef<HTMLInputElement>(null);
  const attente = useRef<AbortController | null>(null);

  // Fenêtre fermée ou écran quitté : on cesse d'interroger la tâche (elle continue dans le worker).
  useEffect(() => {
    if (ouverte) return;
    attente.current?.abort();
  }, [ouverte]);
  useEffect(() => () => attente.current?.abort(), []);

  // Ouverture : repart à zéro, ou à l'étape 2 pour un style existant.
  useEffect(() => {
    if (!ouverte) return;
    setErreur(null);
    setTache(null);
    setOccupe(false);
    if (styleExistant) {
      setCree(styleExistant);
      setEtape(2);
      return;
    }
    const premier = styles[0] ?? null;
    setCree(null);
    setEtape(1);
    setNom("");
    setCode("");
    setCodeModifie(false);
    setDescription("");
    setRefId(premier ? premier.id : null);
    setPalette(premier ? premier.palette.map(copie) : []);
    setPaletteTouchee(false);
    setBudgets({});
    setTexel("");
    setDimensions("");
    setFichiers([]);
    setPaletteDesImages(null);
  }, [ouverte, styleExistant, styles]);

  // Changer de style de référence recharge la palette tant qu'elle n'a pas été retouchée.
  useEffect(() => {
    if (paletteTouchee || etape !== 1) return;
    const ref = styles.find((s) => s.id === refId);
    setPalette(ref ? ref.palette.map(copie) : []);
  }, [refId, styles, paletteTouchee, etape]);

  const codeAuto = useMemo(() => `${slug(nom)}-v0`, [nom]);
  const codeEffectif = codeModifie ? code : codeAuto;
  const manuel = refId === null;
  const credits = cree?.credits_planche ?? 0;
  const maxImages = estimation?.images_max ?? 6;
  const ref = styles.find((s) => s.id === refId);
  // Une image par objet à dessiner : les types saisis à la main, ou ceux du style de référence.
  const imagesAvant = manuel ? Math.min(maxImages, Object.keys(lireDimensions(dimensions)).length) : (ref?.images_planche ?? 0);
  const imagesPlanche = cree?.images_planche ?? imagesAvant;
  const gardees = cree?.planche.filter((i) => i.gardee).length ?? 0;
  const titre = styleExistant ? `Planche de style · ${styleExistant.nom}` : "Nouveau style";

  /** Tes images d'inspiration proposent la palette : leurs couleurs dominantes, nommées, à retoucher. */
  const choisirImages = async (choisies: File[]) => {
    setFichiers(choisies);
    if (choisies.length === 0) return;
    setErreur(null);
    setLecture(true);
    try {
      const fd = new FormData();
      choisies.forEach((f) => fd.append("fichiers", f));
      const r = await api<{ palette: Ligne[]; images: number }>("/styles/palette", { method: "POST", body: fd });
      setPalette(r.palette);
      setPaletteTouchee(true); // changer de style de référence ne l'écrase plus
      setPaletteDesImages(r.images);
    } catch (e) {
      setErreur(`Palette non tirée des images : ${messageErreur(e)}`);
    } finally {
      setLecture(false);
    }
  };

  const soumettre = async () => {
    setErreur(null);
    const corps: StyleEnvoye = {
      nom: nom.trim(),
      code: codeModifie ? code.trim() : undefined,
      description: description.trim(),
      palette: Object.fromEntries(palette.filter((c) => c.nom.trim()).map((c) => [c.nom.trim(), c.hex])),
      budgets_depuis: refId,
    };
    if (manuel) {
      corps.budgets = Object.fromEntries(CATEGORIES.map(([cle]) => [cle, Number(budgets[cle] ?? 0)]));
      corps.texel_density = Number(texel);
      corps.dimensions_m = lireDimensions(dimensions);
    }
    setOccupe(true);
    try {
      const d = await api<StyleDetail>("/styles", { method: "POST", body: JSON.stringify(corps) });
      if (fichiers.length > 0) {
        const fd = new FormData();
        fichiers.forEach((f) => fd.append("fichiers", f));
        await api(`/styles/${d.id}/inspirations`, { method: "POST", body: fd });
      }
      setCree(d);
      setEtape(2);
      await lancer(d.id, `/styles/${d.id}/planche`);
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  const lancer = async (styleId: number, chemin: string) => {
    setErreur(null);
    setOccupe(true);
    attente.current?.abort();
    const controle = new AbortController();
    attente.current = controle;
    try {
      const { tache_id } = await api<TacheLancee>(chemin, { method: "POST" });
      const t = await attendreTache(
        tache_id,
        (lue, ms) => {
          setTache(lue);
          setEnAttenteMs(ms);
        },
        { signal: controle.signal },
      );
      if (t.etat !== "terminee") setErreur(t.erreur ?? `tâche ${t.etat}`);
      setCree(await api<StyleDetail>(`/styles/${styleId}`, { signal: controle.signal }));
      signalerChangement();
    } catch (e) {
      if (e instanceof AttenteAbandonnee || controle.signal.aborted) return;
      setErreur(messageErreur(e));
    } finally {
      if (!controle.signal.aborted) {
        setTache(null);
        setEnAttenteMs(0);
        setOccupe(false);
      }
    }
  };

  const garder = async (img: ImagePlanche) => {
    if (!cree) return;
    try {
      setCree(await api<StyleDetail>(`/styles/${cree.id}/planche/${img.id}`, { method: "PUT", body: JSON.stringify({ gardee: !img.gardee }) }));
    } catch (e) {
      setErreur(messageErreur(e));
    }
  };

  const valider = async () => {
    if (!cree) return;
    setOccupe(true);
    try {
      await api<StyleDetail>(`/styles/${cree.id}/valider`, { method: "POST" });
      signalerChangement();
      onTermine(cree.id);
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  return (
    <Fenetre ouverte={ouverte} titre={titre} onFermer={onFermer}>
      <p className="fenetre-style__sous-titre">
        {etape === 1
          ? "Un style fixe la palette, les matériaux et les budgets de tous les lots qui l'utilisent."
          : `${cree?.nom ?? nom} · ${pluriel(credits, "crédit dépensé", "crédits dépensés")} sur cette planche`}
      </p>
      <ol role="list" aria-label="Étapes" className="fenetre-style__etapes">
        {(["Définir", "Planche de style"] as const).map((libelle, i) => {
          const n = (i + 1) as 1 | 2;
          return (
            <li key={libelle} aria-current={n === etape ? "step" : undefined} className={`fenetre-style__etape${n < etape ? " fenetre-style__etape--faite" : ""}`}>
              <span className="fenetre-style__point">{n}</span>
              {libelle}
            </li>
          );
        })}
      </ol>

      {erreur ? (
        <div role="alert" className="fenetre-style__alerte" style={{ margin: "16px 24px 0" }}>
          {erreur}
        </div>
      ) : null}

      {etape === 1 ? (
        <>
          <div className="fenetre-style__corps">
            <div className="fenetre-style__grille2">
              <div className="fenetre-style__champ">
                <label htmlFor="ns-nom">Nom</label>
                <input id="ns-nom" type="text" className="champ" placeholder="Ex. : Science-fiction propre" value={nom} onChange={(e) => setNom(e.target.value)} />
              </div>
              <div className="fenetre-style__champ">
                <label htmlFor="ns-code">Code</label>
                <input
                  id="ns-code"
                  type="text"
                  className="champ champ--mono"
                  value={codeEffectif}
                  onChange={(e) => {
                    setCode(e.target.value);
                    setCodeModifie(true);
                  }}
                />
                <span className="fenetre-style__aide">Rempli depuis le nom ; il apparaît dans le meta.json de chaque asset.</span>
              </div>
            </div>
            <div className="fenetre-style__champ">
              <label htmlFor="ns-desc">Description</label>
              <textarea id="ns-desc" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
              <span className="fenetre-style__aide">Claude s'en sert pour écrire les consignes d'image de chaque objet.</span>
            </div>
            <div className="fenetre-style__champ">
              <span className="fenetre-style__legende-champ">
                Images d'inspiration <span className="secondaire">· facultatif</span>
              </span>
              <input
                ref={refFichiers}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                multiple
                className="visuellement-cache"
                aria-label="Choisir des images d'inspiration"
                onChange={(e) => choisirImages(Array.from(e.target.files ?? []))}
              />
              <button type="button" className="fenetre-style__depot" onClick={() => refFichiers.current?.click()}>
                {fichiers.length === 0
                  ? "Choisis des images sur ta machine · elles donnent la palette et guident la planche, elles ne sont pas publiées"
                  : `${pluriel(fichiers.length, "image choisie", "images choisies")} : ${fichiers.map((f) => f.name).join(", ")}`}
              </button>
            </div>
            <div className="fenetre-style__champ">
              <span className="fenetre-style__legende-champ" id="ns-palette">
                Palette <span className="secondaire">· 8 à 12 couleurs nommées</span>
              </span>
              {lecture ? (
                <span role="status" className="fenetre-style__aide">
                  Lecture des couleurs de tes images…
                </span>
              ) : paletteDesImages !== null ? (
                <span role="status" className="fenetre-style__aide">
                  Tirée de {paletteDesImages === 1 ? "ton image" : `tes ${paletteDesImages} images`} : retouche une couleur, renomme-la, ajoute-en ou
                  retire-en.
                </span>
              ) : null}
              <ul role="list" aria-labelledby="ns-palette" className="fenetre-style__pastilles">
                {palette.map((c, i) => (
                  <li key={i} className="fenetre-style__couleur">
                    <input
                      type="color"
                      aria-label={`Couleur ${c.nom || i + 1}`}
                      value={c.hex}
                      onChange={(e) => {
                        setPaletteTouchee(true);
                        setPalette(palette.map((x, j) => (j === i ? { ...x, hex: e.target.value.toUpperCase() } : x)));
                      }}
                    />
                    <input
                      type="text"
                      aria-label={`Nom de la couleur ${i + 1}`}
                      value={c.nom}
                      onChange={(e) => {
                        setPaletteTouchee(true);
                        setPalette(palette.map((x, j) => (j === i ? { ...x, nom: e.target.value } : x)));
                      }}
                    />
                    <button
                      type="button"
                      className="bouton bouton--petit"
                      aria-label={`Retirer ${c.nom || `la couleur ${i + 1}`}`}
                      onClick={() => {
                        setPaletteTouchee(true);
                        setPalette(palette.filter((_, j) => j !== i));
                      }}
                    >
                      ×
                    </button>
                  </li>
                ))}
                <li>
                  <button
                    type="button"
                    className="fenetre-style__ajout"
                    onClick={() => {
                      setPaletteTouchee(true);
                      // Une palette vide : la valeur native d'un champ couleur (noir), à choisir ensuite.
                      setPalette([...palette, { nom: "", hex: palette[palette.length - 1]?.hex ?? "#000000" }]);
                    }}
                  >
                    Ajouter une couleur
                  </button>
                </li>
              </ul>
            </div>
            <div className="fenetre-style__champ">
              <label htmlFor="ns-budget">Budgets et échelle</label>
              <select id="ns-budget" className="champ" value={refId === null ? "vide" : String(refId)} onChange={(e) => setRefId(e.target.value === "vide" ? null : Number(e.target.value))}>
                {styles.map((s) => (
                  <option key={s.id} value={s.id}>
                    Reprendre ceux de {s.nom} ({s.code})
                  </option>
                ))}
                <option value="vide">Les saisir à la main</option>
              </select>
              {!manuel ? <span className="fenetre-style__aide">Budgets, tolérances, dimensions par type et gabarits de consignes du style choisi. Modifiables ensuite dans Styles.</span> : null}
            </div>
            {manuel ? (
              <div className="fenetre-style__grille2">
                {CATEGORIES.map(([cle, libelle]) => (
                  <div key={cle} className="fenetre-style__champ">
                    <label htmlFor={`ns-budget-${cle}`}>{libelle} (tris)</label>
                    <input id={`ns-budget-${cle}`} type="number" min={1} className="champ" value={budgets[cle] ?? ""} onChange={(e) => setBudgets({ ...budgets, [cle]: e.target.value })} />
                  </div>
                ))}
                <div className="fenetre-style__champ">
                  <label htmlFor="ns-texel">Densité de texels (px/m)</label>
                  <input id="ns-texel" type="number" min={1} className="champ" value={texel} onChange={(e) => setTexel(e.target.value)} />
                </div>
                <div className="fenetre-style__champ">
                  <label htmlFor="ns-dimensions">Dimensions réelles par type</label>
                  <textarea id="ns-dimensions" rows={3} placeholder={"caisse 0.6 0.4 0.4\nlampe 0.12 0.08 0.06"} value={dimensions} onChange={(e) => setDimensions(e.target.value)} />
                  <span className="fenetre-style__aide">
                    Une ligne par type : nom, largeur, profondeur, hauteur en mètres. Les {maxImages} premiers servent à la planche, une image chacun.
                  </span>
                </div>
              </div>
            ) : null}
          </div>
          <div className="fenetre-style__pied">
            <button type="button" className="bouton" onClick={onFermer}>
              Annuler
            </button>
            <span className="fenetre-style__espace" />
            <button type="button" className="bouton bouton--primaire" onClick={soumettre} disabled={occupe || !nom.trim() || imagesAvant === 0}>
              Générer la première planche · {coutPlanche(imagesAvant, estimation)}
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="fenetre-style__corps">
            <p className="secondaire" style={{ fontSize: "13.5px", lineHeight: 1.5 }}>
              {pluriel(imagesPlanche, "objet générique dessiné", "objets génériques dessinés")} dans ce style. Garde ceux qui te ressemblent ; « Refaire » relance
              {estimation ? ` une image à ${pluriel(estimation.credits_par_image, "crédit", "crédits")}` : " une image"}. Les images gardées servent de référence
              de style à chaque lot.
            </p>
            {tache ? (
              <p role="status" className="fenetre-style__progression">
                {tache.resultat?.progression?.texte || ETATS_TACHE[tache.etat]}
                {enAttenteMs >= ATTENTE_WORKER_MS
                  ? ` · en attente depuis ${Math.round(enAttenteMs / 1000)} s : le worker la prendra dès qu'il tourne (python dev.py le lance avec l'API).`
                  : ""}
              </p>
            ) : null}
            {cree && cree.planche.length === 0 && !tache ? (
              <div className="fenetre-style__progression">
                Aucune image pour l'instant.{" "}
                <button type="button" className="bouton bouton--petit" onClick={() => lancer(cree.id, `/styles/${cree.id}/planche`)} disabled={occupe}>
                  Générer la planche · {coutPlanche(imagesPlanche, estimation)}
                </button>
              </div>
            ) : null}
            {cree && cree.planche.length > 0 ? (
              <ul role="list" aria-label="Images de la planche" className="fenetre-style__tuiles">
                {cree.planche.map((img) => (
                  <li key={img.id} className={`fenetre-style__tuile${img.gardee ? " fenetre-style__tuile--gardee" : ""}`}>
                    <div className="fenetre-style__tuile-image">
                      <img src={img.url} alt={img.objet} />
                      {img.simule ? <span className="pastille pastille--neutre styles__simule">simulé</span> : null}
                    </div>
                    <div className="fenetre-style__tuile-bas">
                      <span className="fenetre-style__tuile-nom">{img.objet.replace(/_/g, " ")}</span>
                      <button type="button" className={`bouton bouton--petit${img.gardee ? " bouton--garde" : ""}`} aria-pressed={img.gardee} onClick={() => garder(img)} disabled={occupe}>
                        {img.gardee ? "Gardée" : "Garder"}
                      </button>
                      <button type="button" className="bouton bouton--petit" onClick={() => lancer(cree.id, `/styles/${cree.id}/planche/${img.id}/refaire`)} disabled={occupe}>
                        Refaire
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          <div className="fenetre-style__pied">
            <span>
              {pluriel(gardees, "image gardée", "images gardées")} sur {cree?.planche.length ?? 0}
            </span>
            <span className="fenetre-style__espace" />
            <button type="button" className="bouton" onClick={onFermer}>
              Plus tard
            </button>
            <button type="button" className="bouton bouton--primaire" onClick={valider} disabled={occupe || gardees === 0}>
              Valider le style
            </button>
          </div>
        </>
      )}
    </Fenetre>
  );
}

const ETATS_TACHE: Record<Tache["etat"], string> = {
  en_attente: "En attente",
  en_cours: "En cours",
  terminee: "Terminée",
  echouee: "Échouée",
  annulee: "Annulée",
};

function copie(c: Couleur): Ligne {
  return { nom: c.nom, hex: c.hex };
}
