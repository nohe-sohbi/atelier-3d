import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageErreur } from "../../api/client";
import { signalerChangement } from "../../api/rafraichissement";
import type { CleEtapeLot, EnTeteLot as EnTeteApi, EstimationAppliquerStyle } from "../../api/types";
import { Erreur } from "../../components/Etats";
import { Etapes } from "../../components/Etapes";
import { Fenetre } from "../../components/Fenetre";
import { nomDuLot, pluriel } from "./commun";

interface Props {
  lotId: number;
  etape: CleEtapeLot;
  /** Change quand l'écran du dessous a modifié le lot : l'en-tête se relit. */
  version: number;
}

/** En-tête des écrans d'un projet : fil d'Ariane, nom, thème, style, ligne d'état, les six étapes. */
export function EnTeteLot({ lotId, etape, version }: Props) {
  const naviguer = useNavigate();
  const [lot, setLot] = useState<EnTeteApi | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [renommer, setRenommer] = useState(false);
  const [nom, setNom] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [appliquer, setAppliquer] = useState(false);
  const fermerAppliquer = useCallback(() => setAppliquer(false), []);

  const charger = useCallback(async () => {
    try {
      setLot(await api<EnTeteApi>(`/lots/${lotId}?etape=${etape}`));
      setErreur(null);
    } catch (e) {
      setErreur(messageErreur(e));
    }
  }, [lotId, etape]);

  useEffect(() => {
    charger();
  }, [charger, version]);

  const enregistrerNom = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setLot(await api<EnTeteApi>(`/lots/${lotId}`, { method: "PATCH", body: JSON.stringify({ nom: nom.trim() }) }));
      setRenommer(false);
      signalerChangement();
    } catch (err) {
      setMessage(messageErreur(err));
    }
  };

  const dupliquer = async () => {
    try {
      const copie = await api<EnTeteApi>(`/lots/${lotId}/dupliquer`, { method: "POST" });
      signalerChangement();
      naviguer(`/lots/${copie.id}/brief`);
    } catch (e) {
      setMessage(messageErreur(e));
    }
  };

  if (erreur) return <Erreur message={erreur} onReessayer={charger} />;
  if (!lot) return <div className="entete-lot entete-lot--chargement" aria-busy="true" />;

  return (
    <div className="entete-lot">
      <nav aria-label="Fil d'Ariane" className="entete-lot__ariane">
        <Link to="/lots">
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
            <path d="M9 3 L5 7 L9 11" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" }} />
          </svg>
          Projets
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{nomDuLot(lot.nom)}</span>
      </nav>

      <div className="entete-lot__ligne">
        {renommer ? (
          <form className="entete-lot__renommer" onSubmit={enregistrerNom}>
            <label htmlFor="entete-lot-nom" className="visuellement-cache">
              Nom du projet
            </label>
            <input
              id="entete-lot-nom"
              className="champ"
              value={nom}
              autoFocus
              onChange={(e) => setNom(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setRenommer(false);
              }}
            />
            <button type="submit" className="bouton bouton--petit bouton--primaire">
              Enregistrer
            </button>
            <button type="button" className="bouton bouton--petit" onClick={() => setRenommer(false)}>
              Annuler
            </button>
          </form>
        ) : (
          <>
            <h1 className="entete-lot__titre">{nomDuLot(lot.nom)}</h1>
            <button
              type="button"
              className="entete-lot__icone"
              aria-label="Renommer le projet"
              title="Renommer le projet"
              onClick={() => {
                setNom(lot.nom);
                setRenommer(true);
              }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                <path d="M3 13 L3.6 10.4 L10.8 3.2 L12.8 5.2 L5.6 12.4 Z M9.6 4.4 L11.6 6.4" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinejoin: "round" }} />
              </svg>
            </button>
          </>
        )}
        {lot.theme ? <span className="entete-lot__puce">{lot.theme}</span> : null}
        {lot.style ? (
          <Link to={`/styles?style=${encodeURIComponent(lot.style.code)}`} className="entete-lot__puce mono" title={`Style ${lot.style.nom}`}>
            {lot.style.code}
          </Link>
        ) : (
          <span className="entete-lot__puce">sans style</span>
        )}
        <span className="entete-lot__etat">{lot.ligne_etat}</span>
        <div className="entete-lot__actions">
          {lot.style_plus_recent ? (
            <button type="button" className="bouton bouton--petit" onClick={() => setAppliquer(true)}>
              Appliquer la v{lot.style_plus_recent.version}
            </button>
          ) : null}
          <button type="button" className="bouton bouton--petit" onClick={dupliquer}>
            Dupliquer le projet
          </button>
        </div>
      </div>
      {message ? (
        <p role="alert" className="entete-lot__message">
          {message}
        </p>
      ) : null}

      <Etapes
        etapes={lot.etapes.map((e) => ({ cle: e.cle, libelle: e.libelle, lien: e.lien, faite: e.faite, atteinte: e.atteinte }))}
        courante={Math.max(0, lot.etapes.findIndex((e) => e.cle === etape))}
      />

      {lot.style_plus_recent ? (
        <AppliquerStyle ouverte={appliquer} lotId={lotId} cible={lot.style_plus_recent} onFermer={fermerAppliquer} />
      ) : null}
    </div>
  );
}

/** « Appliquer la vN » (correction 11, dessiné nulle part) : l'estimation seulement ; le lancement attend la fabrication. */
function AppliquerStyle({
  ouverte,
  lotId,
  cible,
  onFermer,
}: {
  ouverte: boolean;
  lotId: number;
  cible: { id: number; code: string; version: number };
  onFermer: () => void;
}) {
  const [estimation, setEstimation] = useState<EstimationAppliquerStyle | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (!ouverte) return;
    setEstimation(null);
    api<EstimationAppliquerStyle>(`/lots/${lotId}/appliquer-style?style_id=${cible.id}`)
      .then(setEstimation)
      .catch((e) => setErreur(messageErreur(e)));
  }, [ouverte, lotId, cible.id]);

  return (
    <Fenetre ouverte={ouverte} titre={`Appliquer la v${cible.version} · ${cible.code}`} onFermer={onFermer}>
      <div className="fenetre-lot__corps">
        {erreur ? <Erreur message={erreur} /> : null}
        {estimation ? (
          <>
            <p>
              Une nouvelle version du style ne touche aucun projet : ici, tu choisis de la reprendre. Les objets code sont refaits gratuitement, les objets IA se
              régénèrent.
            </p>
            {estimation.objets_code.length + estimation.objets_ia.length === 0 ? (
              <p className="secondaire">Aucun objet fabriqué dans ce projet pour l'instant : rien à refaire.</p>
            ) : (
              <ul role="list" className="fenetre-lot__liste">
                <li>
                  {pluriel(estimation.objets_code.length, "objet code refait", "objets code refaits")} gratuitement
                  {estimation.objets_code.length ? ` : ${estimation.objets_code.join(", ")}` : ""}
                </li>
                <li>
                  {pluriel(estimation.objets_ia.length, "objet IA à régénérer", "objets IA à régénérer")} · ≈ {pluriel(estimation.credits, "crédit", "crédits")} Meshy
                  {estimation.objets_ia.length ? ` : ${estimation.objets_ia.join(", ")}` : ""}
                </li>
              </ul>
            )}
            {!estimation.lancement_possible ? <p role="status" className="fenetre-lot__note">{estimation.raison}.</p> : null}
          </>
        ) : null}
      </div>
    </Fenetre>
  );
}
