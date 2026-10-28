import { useEffect, useRef, useState } from "react";
import { creerAfficheur, type Afficheur, type ModeAffichage, type NiveauDetail } from "../../components/afficheur3d/afficheur";

export interface OutilsScene {
  reperes: boolean;
  personnage: boolean;
  tourner: boolean;
}

interface Props {
  /** Adresse du fichier .glb de l'objet. */
  modele: string;
  nom: string;
  /** Triangles de chaque niveau de détail, pour les boutons « Détail 1 · 3 816 ». */
  triangles: [number | null, number | null, number | null];
  outils: OutilsScene;
  onOutils: (o: OutilsScene) => void;
  pointage: boolean;
  onPointage: (actif: boolean) => void;
  /** Une pastille vient d'être posée sur l'objet (son numéro). */
  onPastilleAjoutee: (n: number) => void;
  /** On a touché une pastille déjà posée. */
  onPastilleTouchee: (n: number) => void;
}

const MODES: Array<{ cle: ModeAffichage; nom: string; aide: string }> = [
  { cle: "texture", nom: "Texturé", aide: "Tel qu'il sera dans le jeu" },
  { cle: "argile", nom: "Argile", aide: "Sans couleur : juge la forme seule" },
  { cle: "fil", nom: "Fil de fer", aide: "Montre le maillage, les triangles" },
  { cle: "surfaces", nom: "Surfaces", aide: "Couleur selon l'orientation ; du rouge = face à l'envers" },
  { cle: "damier", nom: "Damier", aide: "Montre si la texture est bien étalée" },
];

const LUMIERES: Array<{ nom: string; direction: number; hauteur: number }> = [
  { nom: "Studio", direction: 40, hauteur: 50 },
  { nom: "Rasante", direction: 40, hauteur: 10 },
  { nom: "Contre-jour", direction: 210, hauteur: 28 },
];

const formatNombre = new Intl.NumberFormat("fr-FR");

function Pictogramme({ d }: { d: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path d={d} style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" }} />
    </svg>
  );
}

const ICONES = {
  lumiere: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  reperes: "M4 20V5M4 20h15M4 20l6-6",
  personnage: "M12 3a2.2 2.2 0 1 0 0 4.4A2.2 2.2 0 0 0 12 3zM12 8v7M7.5 10.5 12 9l4.5 1.5M12 15l-3 6M12 15l3 6",
  tourner: "M20 12a8 8 0 1 1-2.6-5.9M20 4v4h-4",
  recentrer: "M4 9V5h4M20 9V5h-4M4 15v4h4M20 15v4h-4M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z",
};

/** La 3D de l'objet : tourner, zoomer, changer d'affichage, éclairer, voir la taille, poser à côté d'un personnage, pointer un défaut. */
export function Scene3D({ modele, nom, triangles, outils, onOutils, pointage, onPointage, onPastilleAjoutee, onPastilleTouchee }: Props) {
  const racine = useRef<HTMLDivElement>(null);
  const afficheur = useRef<Afficheur | null>(null);
  const [etat, setEtat] = useState<"chargement" | "pret" | "erreur">("chargement");
  const [niveaux, setNiveaux] = useState(1);
  const [niveau, setNiveau] = useState<NiveauDetail>(0);
  const [mode, setMode] = useState<ModeAffichage>("texture");
  const [menu, setMenu] = useState<"affichage" | "lumiere" | null>(null);
  const [lumiere, setLumiere] = useState({ direction: 40, hauteur: 50 });
  // Les rappels changent à chaque rendu : l'afficheur appelle toujours la dernière version.
  const rappels = useRef({ onOutils, onPointage, onPastilleAjoutee, onPastilleTouchee, outils });
  rappels.current = { onOutils, onPointage, onPastilleAjoutee, onPastilleTouchee, outils };

  useEffect(() => {
    if (!racine.current) return;
    let a: Afficheur;
    try {
      a = creerAfficheur(racine.current);
    } catch {
      setEtat("erreur");
      return;
    }
    afficheur.current = a;
    a.surPointage = (n) => {
      rappels.current.onPastilleAjoutee(n);
      rappels.current.onPointage(false);
    };
    a.surPastille = (n) => rappels.current.onPastilleTouchee(n);
    a.surArretRotation = () => rappels.current.onOutils({ ...rappels.current.outils, tourner: false });
    let actif = true;
    a.charger(modele)
      .then((m) => {
        if (!actif) return;
        setNiveaux(Math.max(1, m.niveaux));
        setEtat("pret");
      })
      .catch(() => {
        if (actif) setEtat("erreur");
      });
    return () => {
      actif = false;
      a.detruire();
      afficheur.current = null;
    };
  }, [modele]);

  useEffect(() => afficheur.current?.niveau(niveau), [niveau, etat]);
  useEffect(() => afficheur.current?.mode(mode), [mode, etat]);
  useEffect(() => afficheur.current?.lumiere(lumiere), [lumiere, etat]);
  useEffect(() => afficheur.current?.reperes(outils.reperes), [outils.reperes, etat]);
  useEffect(() => afficheur.current?.personnage(outils.personnage), [outils.personnage, etat]);
  useEffect(() => afficheur.current?.tourner(outils.tourner), [outils.tourner, etat]);
  useEffect(() => afficheur.current?.pointage(pointage), [pointage, etat]);

  const basculer = (cle: keyof OutilsScene) => onOutils({ ...outils, [cle]: !outils[cle] });
  const modeActuel = MODES.find((m) => m.cle === mode)!;

  return (
    <div className={`scene3d${pointage ? " scene3d--pointage" : ""}${outils.personnage ? " scene3d--personnage" : ""}`}>
      <div ref={racine} className="scene3d__vue" role="img" aria-label={`${nom} en 3D : glisse pour tourner, pince pour zoomer`} />
      {etat === "chargement" ? <p className="scene3d__etat">Chargement de la 3D…</p> : null}
      {etat === "erreur" ? <p className="scene3d__etat">La 3D ne peut pas s'afficher ici. Les vues et les vérifications restent disponibles.</p> : null}

      {etat === "pret" ? (
        <>
          <div className="scene3d__barre">
            {niveaux > 1 ? (
              <div className="scene3d__segment" role="group" aria-label="Niveau de détail">
                {([0, 1, 2] as const).map((n) => (
                  <button key={n} type="button" aria-pressed={niveau === n} className={niveau === n ? "est-actif" : ""} onClick={() => setNiveau(n)}>
                    Détail {n + 1}
                    {triangles[n] !== null ? <small> · {formatNombre.format(triangles[n]!)}</small> : null}
                  </button>
                ))}
              </div>
            ) : (
              <span />
            )}
            <button type="button" className="bouton bouton--petit scene3d__affichage" aria-haspopup="true" aria-expanded={menu === "affichage"} onClick={() => setMenu(menu === "affichage" ? null : "affichage")}>
              {modeActuel.nom} ▾
            </button>
          </div>

          {menu === "affichage" ? (
            <div className="scene3d__menu scene3d__menu--affichage" role="menu" aria-label="Affichage">
              {MODES.map((m) => (
                <button
                  key={m.cle}
                  type="button"
                  role="menuitemradio"
                  aria-checked={mode === m.cle}
                  className={mode === m.cle ? "est-actif" : ""}
                  onClick={() => {
                    setMode(m.cle);
                    setMenu(null);
                  }}
                >
                  <b>{m.nom}</b>
                  <small>{m.aide}</small>
                </button>
              ))}
            </div>
          ) : null}

          <div className="scene3d__outils" role="group" aria-label="Outils 3D">
            <button type="button" aria-label="Lumière" title="Lumière" aria-pressed={menu === "lumiere"} className={menu === "lumiere" ? "est-actif" : ""} onClick={() => setMenu(menu === "lumiere" ? null : "lumiere")}>
              <Pictogramme d={ICONES.lumiere} />
            </button>
            <button type="button" aria-label="Taille et point d'ancrage" title="Taille et point d'ancrage" aria-pressed={outils.reperes} className={outils.reperes ? "est-actif" : ""} onClick={() => basculer("reperes")}>
              <Pictogramme d={ICONES.reperes} />
            </button>
            <button type="button" aria-label="Voir à côté d'un personnage" title="Voir à côté d'un personnage" aria-pressed={outils.personnage} className={outils.personnage ? "est-actif" : ""} onClick={() => basculer("personnage")}>
              <Pictogramme d={ICONES.personnage} />
            </button>
            <button type="button" aria-label="Tourner tout seul" title="Tourner tout seul" aria-pressed={outils.tourner} className={outils.tourner ? "est-actif" : ""} onClick={() => basculer("tourner")}>
              <Pictogramme d={ICONES.tourner} />
            </button>
            <button type="button" aria-label="Recentrer la vue" title="Recentrer la vue" onClick={() => afficheur.current?.recentrer()}>
              <Pictogramme d={ICONES.recentrer} />
            </button>
          </div>

          {menu === "lumiere" ? (
            <div className="scene3d__menu scene3d__menu--lumiere" role="group" aria-label="Lumière">
              <b>Lumière</b>
              <label>
                Direction
                <input type="range" min={0} max={360} value={lumiere.direction} onChange={(e) => setLumiere({ ...lumiere, direction: Number(e.target.value) })} />
              </label>
              <label>
                Hauteur
                <input type="range" min={5} max={85} value={lumiere.hauteur} onChange={(e) => setLumiere({ ...lumiere, hauteur: Number(e.target.value) })} />
              </label>
              <div className="scene3d__choix">
                {LUMIERES.map((l) => (
                  <button
                    key={l.nom}
                    type="button"
                    aria-pressed={lumiere.direction === l.direction && lumiere.hauteur === l.hauteur}
                    onClick={() => setLumiere({ direction: l.direction, hauteur: l.hauteur })}
                  >
                    {l.nom}
                  </button>
                ))}
              </div>
              <small>La lumière rasante fait ressortir les bosses et les creux.</small>
            </div>
          ) : null}

          <button type="button" className="bouton bouton--petit scene3d__pointer" aria-pressed={pointage} onClick={() => onPointage(!pointage)}>
            {pointage ? "Annuler" : "＋ Pointer un défaut"}
          </button>
          {pointage ? <p className="scene3d__consigne">Touche l'objet, là où ça ne va pas</p> : null}
        </>
      ) : null}
    </div>
  );
}
