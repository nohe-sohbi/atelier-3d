import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import type { GroupeLots, Lots as LotsApi } from "../../api/types";
import { Chargement, Erreur, EtatVide } from "../../components/Etats";
import { ilYA, nomDuLot, pluriel } from "./commun";
import "./Lots.css";

const FILTRES: Array<{ groupe: GroupeLots; libelle: string; vide: string }> = [
  { groupe: "tous", libelle: "Tous", vide: "Aucun projet pour l'instant" },
  { groupe: "en_cours", libelle: "En cours", vide: "Aucun projet en cours" },
  { groupe: "termines", libelle: "Terminés", vide: "Aucun projet terminé" },
  { groupe: "brouillons", libelle: "Brouillons", vide: "Aucun brouillon" },
];

function groupeDepuis(valeur: string | null): GroupeLots {
  return FILTRES.some((f) => f.groupe === valeur) ? (valeur as GroupeLots) : "tous";
}

export function Lots() {
  const [params, setParams] = useSearchParams();
  const groupe = groupeDepuis(params.get("groupe"));
  const [donnees, setDonnees] = useState<LotsApi | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(async () => {
    try {
      setDonnees(await api<LotsApi>(`/lots?groupe=${groupe}`));
      setErreur(null);
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, [groupe]);

  useEffect(() => {
    charger();
  }, [charger]);

  const filtre = FILTRES.find((f) => f.groupe === groupe)!;

  return (
    <div className="lots">
      <div className="lots__entete">
        <div>
          <h1 className="page-titre">Projets</h1>
          <p className="page-sous-titre">Un projet, c'est une demande, une liste d'objets et six étapes. Il s'ouvre sur l'étape où il en est.</p>
        </div>
        <Link to="/" className="bouton bouton--primaire">
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
            <path d="M7 2 V12 M2 7 H12" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" }} />
          </svg>
          Nouveau projet
        </Link>
      </div>

      <div role="group" aria-label="Filtrer les projets" className="lots__filtres">
        {FILTRES.map((f) => (
          <button
            key={f.groupe}
            type="button"
            className="lots__filtre"
            aria-pressed={f.groupe === groupe}
            onClick={() => setParams(f.groupe === "tous" ? {} : { groupe: f.groupe }, { replace: true })}
          >
            {f.libelle}
            {donnees ? ` · ${donnees.compteurs[f.groupe]}` : ""}
          </button>
        ))}
      </div>

      {erreur ? <Erreur message={erreur} onReessayer={charger} /> : null}
      {!donnees && !erreur ? <Chargement /> : null}
      {donnees && donnees.lots.length === 0 ? (
        <EtatVide
          titre={filtre.vide}
          texte={groupe === "tous" ? "Un projet part d'une phrase et d'un style : l'app propose la liste d'objets à fabriquer." : undefined}
          enfants={
            groupe === "tous" ? (
              <Link to="/" className="bouton bouton--primaire">
                Nouveau projet
              </Link>
            ) : undefined
          }
        />
      ) : null}
      {donnees && donnees.lots.length > 0 ? (
        <div className="lots__cadre">
          <table className="lots__table" aria-label="Projets">
            <thead>
              <tr>
                <th scope="col">Projet</th>
                <th scope="col">Style</th>
                <th scope="col">Étape</th>
                <th scope="col">Où il en est</th>
                <th scope="col">Mis à jour</th>
                <th scope="col">
                  <span className="visuellement-cache">Action</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {donnees.lots.map((l) => (
                <tr key={l.id}>
                  <td>
                    <Link to={l.lien} className="lots__nom">
                      {nomDuLot(l.nom)}
                    </Link>
                    <div className="lots__theme">{[l.theme, pluriel(l.nb_objets, "objet", "objets")].filter(Boolean).join(" · ")}</div>
                  </td>
                  <td className="lots__style mono">{l.style ? l.style.code : "—"}</td>
                  <td>
                    <span aria-hidden="true" className="lots__segments">
                      {[1, 2, 3, 4, 5, 6].map((i) => (
                        <span key={i} className={`lots__segment${i < l.etape ? " lots__segment--fait" : i === l.etape ? " lots__segment--courant" : ""}`} />
                      ))}
                    </span>
                    <span className="lots__etape">{l.libelle_etape}</span>
                  </td>
                  <td>
                    <span className="lots__ou">
                      <span className={`ton ton--${l.ton}`}>{l.statut}</span>
                      <span className="lots__detail">{l.detail}</span>
                    </span>
                  </td>
                  <td className="lots__date">
                    <time dateTime={l.maj_le}>{ilYA(l.maj_le)}</time>
                  </td>
                  <td className="lots__action">
                    <Link to={l.lien} className="bouton bouton--petit" aria-label={`${l.action} : ${nomDuLot(l.nom)}`}>
                      {l.action}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
