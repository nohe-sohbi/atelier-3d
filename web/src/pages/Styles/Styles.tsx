import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import type { EstimationPlanche, StyleDetail, StyleResume, Styles as StylesApi } from "../../api/types";
import { Chargement, Erreur, EtatVide } from "../../components/Etats";
import { ModifierStyle } from "./ModifierStyle";
import { NouveauStyle } from "./NouveauStyle";
import { coutPlanche, dateCourte, formatNombre, libelleEtat, usageTexte } from "./commun";
import "./Styles.css";

type Fenetre = "aucune" | "nouveau" | "planche" | "modifier";

export function Styles() {
  const [params, setParams] = useSearchParams();
  const [liste, setListe] = useState<StyleResume[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [selection, setSelection] = useState<number | null>(null);
  const [detail, setDetail] = useState<StyleDetail | null>(null);
  const [erreurDetail, setErreurDetail] = useState<string | null>(null);
  const [fenetre, setFenetre] = useState<Fenetre>("aucune");
  const [message, setMessage] = useState<string | null>(null);
  const [codeInconnu, setCodeInconnu] = useState<string | null>(null);
  const [estimation, setEstimation] = useState<EstimationPlanche | null>(null);

  // Tarif de l'adaptateur Meshy : sans lui, les boutons donnent le nombre d'images sans chiffrer.
  useEffect(() => {
    api<EstimationPlanche>("/styles/estimation-planche")
      .then(setEstimation)
      .catch(() => setEstimation(null));
  }, []);

  const chargerListe = useCallback(async (): Promise<StyleResume[] | null> => {
    try {
      const r = await api<StylesApi>("/styles");
      setListe(r.styles);
      setErreur(null);
      return r.styles;
    } catch (e) {
      setErreur(messageErreur(e));
      setListe([]);
      return null;
    }
  }, []);

  const chargerDetail = useCallback(async (id: number) => {
    try {
      setDetail(await api<StyleDetail>(`/styles/${id}`));
      setErreurDetail(null);
    } catch (e) {
      setErreurDetail(messageErreur(e));
    }
  }, []);

  useEffect(() => {
    chargerListe();
  }, [chargerListe]);

  // Le style ouvert vient de l'URL (?style=code), sinon de la sélection, sinon du premier.
  useEffect(() => {
    if (!liste) return;
    const code = params.get("style");
    const parCode = code ? liste.find((s) => s.code === code) : undefined;
    setCodeInconnu(code && !parCode ? code : null);
    const courant = liste.find((s) => s.id === selection);
    const cible = parCode ?? courant ?? liste[0] ?? null;
    const id = cible?.id ?? null;
    if (id !== selection) setSelection(id);
  }, [liste, params, selection]);

  useEffect(() => {
    if (selection === null) {
      setDetail(null);
      return;
    }
    chargerDetail(selection);
  }, [selection, chargerDetail]);

  const choisir = (s: StyleResume) => {
    setSelection(s.id);
    setParams({ style: s.code }, { replace: true });
  };

  const rafraichir = async (idCible?: number) => {
    const l = await chargerListe();
    const id = idCible ?? selection;
    if (id === null || !l) return;
    const s = l.find((x) => x.id === id);
    if (!s) return;
    if (idCible !== undefined) {
      setSelection(id);
      setParams({ style: s.code }, { replace: true });
    }
    await chargerDetail(id);
  };

  const dupliquer = async () => {
    if (!detail) return;
    try {
      const v = await api<StyleDetail>(`/styles/${detail.id}/versions`, { method: "POST", body: JSON.stringify({ note: "" }) });
      setMessage(`Version ${v.code} créée : l'ancienne reste telle quelle pour les projets qui l'utilisent.`);
      await rafraichir(v.id);
    } catch (e) {
      setMessage(messageErreur(e));
    }
  };

  if (erreur && (!liste || liste.length === 0)) {
    return (
      <div className="styles">
        <Entete onNouveau={() => setFenetre("nouveau")} />
        <Erreur message={erreur} onReessayer={() => chargerListe()} />
      </div>
    );
  }
  if (liste === null) {
    return (
      <div className="styles">
        <Entete onNouveau={() => setFenetre("nouveau")} />
        <Chargement />
      </div>
    );
  }

  const prochaineVersion = detail ? Math.max(...detail.versions.map((v) => v.version), detail.version) + 1 : 1;
  // Un style validé ne montre que les images gardées ; un brouillon montre tout ce qui a été généré.
  const planche = detail ? (detail.etat === "valide" ? detail.planche.filter((i) => i.gardee) : detail.planche) : [];

  return (
    <div className="styles">
      <Entete onNouveau={() => setFenetre("nouveau")} />
      {message ? (
        <p role="status" className="secondaire">
          {message}
        </p>
      ) : null}
      {codeInconnu && liste.length > 0 ? (
        <p role="status" className="secondaire">
          Aucun style ne porte le code « {codeInconnu} » : voici {liste.find((s) => s.id === selection)?.nom ?? "le premier de la liste"}.
        </p>
      ) : null}
      {liste.length === 0 ? (
        <EtatVide
          titre="Aucun style pour l'instant"
          texte="Un style fixe la palette, les matériaux et les budgets de tous les projets qui l'utilisent."
          enfants={
            <button type="button" className="bouton bouton--primaire" onClick={() => setFenetre("nouveau")}>
              Nouveau style
            </button>
          }
        />
      ) : (
        <div className="styles__corps">
          <ul role="list" aria-label="Tes styles" className="styles__liste">
            {liste.map((s) => (
              <li key={s.id}>
                <button type="button" className="styles__carte" aria-pressed={s.id === selection} onClick={() => choisir(s)}>
                  <span className="styles__carte-ligne">
                    <span className="styles__carte-nom">{s.nom}</span>
                    <span className={`pastille ${s.etat === "valide" ? "pastille--succes" : "pastille--neutre"}`}>{libelleEtat(s.etat)}</span>
                  </span>
                  <span className="styles__code">{s.code}</span>
                  <span aria-hidden="true" className="styles__bande">
                    {s.palette.map((c) => (
                      <span key={c.nom} style={{ background: c.hex }} />
                    ))}
                  </span>
                  <span className="styles__usage">{s.erreur ? `Fichier illisible : ${s.erreur}` : usageTexte(s.usage)}</span>
                </button>
              </li>
            ))}
          </ul>

          <section aria-labelledby="sd-h" className="styles__detail">
            {erreurDetail ? <Erreur message={erreurDetail} onReessayer={() => selection !== null && chargerDetail(selection)} /> : null}
            {!detail && !erreurDetail ? <Chargement /> : null}
            {detail ? (
              <>
                <div className="styles__detail-entete">
                  <div>
                    <h2 id="sd-h">{detail.nom}</h2>
                    <div className="styles__detail-sous">
                      <span className="mono">{detail.code}</span> · {detail.etat === "valide" ? "créé" : "brouillon créé"} le {dateCourte(detail.cree_le)}
                      {detail.lots.length > 0 ? ` · utilisé par ${detail.lots.length > 1 ? `${detail.lots.length} projets` : "1 projet"}` : ""}
                    </div>
                  </div>
                  <div className="styles__actions">
                    <button type="button" className="bouton bouton--petit" onClick={dupliquer}>
                      Dupliquer en v{prochaineVersion}
                    </button>
                    <button
                      type="button"
                      className="bouton bouton--petit bouton--primaire"
                      onClick={() => setFenetre("modifier")}
                      disabled={!detail.peut_modifier}
                      title={detail.peut_modifier ? undefined : "Un projet utilise cette version : duplique-la pour la modifier"}
                    >
                      Modifier
                    </button>
                  </div>
                </div>
                {!detail.peut_modifier ? (
                  <p className="styles__legende">Un projet utilise cette version : elle ne change plus. « Dupliquer en v{prochaineVersion} » crée une version modifiable.</p>
                ) : null}

                <div>
                  <h3 className="styles__h3">Planche de référence</h3>
                  {planche.length === 0 ? (
                    <EtatVide
                      titre="Aucune image validée pour ce style"
                      texte="La planche est faite d'images générées dans ce style (Meshy, simulé par défaut) que tu gardes ou refais."
                      enfants={
                        <button type="button" className="bouton bouton--petit" onClick={() => setFenetre("planche")}>
                          Générer la planche · {coutPlanche(detail.images_planche, estimation)}
                        </button>
                      }
                    />
                  ) : (
                    <>
                      <ul role="list" aria-label="Images de la planche" className="styles__planche">
                        {planche.map((img) => (
                          <li key={img.id}>
                            <img src={img.url} alt={`${img.objet}${img.gardee ? " (gardée)" : ""}`} />
                            {img.simule ? <span className="pastille pastille--neutre styles__simule">simulé</span> : null}
                          </li>
                        ))}
                      </ul>
                      <p className="styles__legende">
                        Images validées à la main : elles servent d'entrée à la voie IA et de cible à la voie code.
                        {detail.etat === "brouillon" ? (
                          <>
                            {" "}
                            <button type="button" className="bouton bouton--petit" onClick={() => setFenetre("planche")}>
                              Compléter la planche et valider
                            </button>
                          </>
                        ) : null}
                      </p>
                    </>
                  )}
                </div>

                <div className="styles__colonnes">
                  <div className="styles__colonne">
                    <h3 className="styles__h3">Palette</h3>
                    <ul role="list" className="styles__palette">
                      {detail.palette.map((c) => (
                        <li key={c.nom}>
                          <span className="styles__nuance" style={{ background: c.hex }} />
                          <span>{c.nom.replace(/_/g, " ")}</span>
                          <span className="styles__hex">{c.hex}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="styles__colonne">
                    <h3 className="styles__h3">Matériaux partagés · voie code</h3>
                    <ul role="list">
                      {detail.materiaux.map((m) => (
                        <li key={m.nom} className="styles__ligne">
                          <span aria-hidden="true" className="styles__puce" style={{ background: m.hex }} />
                          <span className="styles__ligne-nom">{m.nom.replace(/_/g, " ")}</span>
                          {m.usage_assets === null ? null : (
                            <span className="styles__ligne-info">
                              {m.usage_assets === 0 ? "aucun asset code" : m.usage_assets > 1 ? `${formatNombre.format(m.usage_assets)} assets` : "1 asset"}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="styles__colonnes">
                  <div className="styles__colonne">
                    <h3 className="styles__h3">Budgets et échelle</h3>
                    <ul role="list">
                      {detail.budgets.map((b) => (
                        <li key={b.cle} className="styles__kv">
                          <span className="styles__kv-cle">{b.libelle}</span>
                          <span className="styles__kv-val">{b.tris === null ? "—" : `${formatNombre.format(b.tris)} tris`}</span>
                        </li>
                      ))}
                      <li className="styles__kv">
                        <span className="styles__kv-cle">Densité de texels</span>
                        <span className="styles__kv-val">{formatNombre.format(detail.texel_density)} px/m</span>
                      </li>
                      <li className="styles__kv">
                        <span className="styles__kv-cle">Unité</span>
                        <span className="styles__kv-val">{detail.unite}</span>
                      </li>
                    </ul>
                  </div>
                  <div className="styles__colonne">
                    <h3 className="styles__h3">Versions</h3>
                    <ol role="list">
                      {detail.versions.map((v) => (
                        <li key={v.id} className="styles__version">
                          <span className="styles__version-num">v{v.version}</span>
                          <div>
                            <div className="styles__version-note">
                              {v.note || "—"}
                              {v.id === detail.id ? " (ouverte)" : ""}
                            </div>
                            <div className="styles__version-date">{dateCourte(v.date)}</div>
                          </div>
                        </li>
                      ))}
                    </ol>
                    <p className="styles__legende">
                      Une nouvelle version ne touche aucun lot. Dans chaque lot, « Appliquer la v{prochaineVersion} » refait gratuitement les objets code et chiffre les
                      objets IA à régénérer avant de les lancer.
                    </p>
                  </div>
                </div>
              </>
            ) : null}
          </section>
        </div>
      )}

      <NouveauStyle
        ouverte={fenetre === "nouveau" || fenetre === "planche"}
        styles={liste}
        styleExistant={fenetre === "planche" ? detail : null}
        estimation={estimation}
        onFermer={() => {
          setFenetre("aucune");
          rafraichir();
        }}
        onTermine={(id) => {
          setFenetre("aucune");
          rafraichir(id);
        }}
      />
      {detail ? (
        <ModifierStyle
          ouverte={fenetre === "modifier"}
          style={detail}
          onFermer={() => setFenetre("aucune")}
          onModifie={(d) => {
            setDetail(d);
            setFenetre("aucune");
            chargerListe();
          }}
        />
      ) : null}
    </div>
  );
}

function Entete({ onNouveau }: { onNouveau: () => void }) {
  return (
    <div className="styles__entete">
      <div className="styles__entete-texte">
        <h1 className="page-titre">Styles</h1>
        <p className="page-sous-titre">
          Tes moodboards exécutables. Chaque projet en applique un. Un matériau partagé modifié se répercute sur les assets de la voie code ; les assets IA,
          eux, se régénèrent à partir de la planche.
        </p>
      </div>
      <button type="button" className="bouton" onClick={onNouveau}>
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
          <path d="M7 2 V12 M2 7 H12" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" }} />
        </svg>
        Nouveau style
      </button>
    </div>
  );
}
