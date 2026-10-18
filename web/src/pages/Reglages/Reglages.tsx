import { useCallback, useEffect, useRef, useState } from "react";
import { api, messageErreur } from "../../api/client";
import type {
  AlertePct,
  ModeleClaude,
  PresenceOutils,
  Reglages as ReglagesApi,
  ReglagesEnvoyes,
  RenouvellementJour,
  ResultatTest,
  ServiceTestable,
} from "../../api/types";
import { Chargement, Erreur } from "../../components/Etats";
import { ChampCle, Interrupteur, Ligne, Pastille, type EtatPastille } from "./Composants";
import "./Reglages.css";

type ServiceAvecCle = "meshy" | "claude" | "itchio";
type Brouillon = Omit<ReglagesApi, "etat">;

interface EtatService {
  etat: EtatPastille;
  message: string;
  ok: boolean | null;
}

const SERVICES_TESTABLES: ServiceTestable[] = ["meshy", "claude", "comfyui", "itchio", "blender", "gltf_validator", "butler", "git_lfs"];
const OUTILS = ["blender", "gltf_validator", "butler", "git_lfs"] as const;
const ETAT_INITIAL: EtatService = { etat: "Non testé", message: "", ok: null };

/** À l'ouverture : « Non testé », sauf un outil absent de la machine, dit « Introuvable » tout de suite. */
function testsInitiaux(presence: PresenceOutils | undefined): Record<ServiceTestable, EtatService> {
  const base = Object.fromEntries(SERVICES_TESTABLES.map((s) => [s, ETAT_INITIAL])) as Record<ServiceTestable, EtatService>;
  if (presence) {
    for (const outil of OUTILS) {
      if (!presence[outil].present) base[outil] = { etat: "Introuvable", message: "", ok: false };
    }
  }
  return base;
}
const DUREE_CONFIRMATION_MS = 4000;

const formatNombre = new Intl.NumberFormat("fr-FR");

function sansEtat(r: ReglagesApi): Brouillon {
  // Copie profonde : le brouillon ne doit jamais modifier l'objet chargé.
  const copie = JSON.parse(JSON.stringify(r)) as Partial<ReglagesApi>;
  delete copie.etat;
  return copie as Brouillon;
}

function pluriel(n: number, singulier: string, plurielMot: string): string {
  return `${formatNombre.format(n)} ${n > 1 ? plurielMot : singulier}`;
}

/** Options d'un select numérique ; la valeur courante est toujours proposée, même hors liste. */
function optionsTaches(valeurs: number[], courante: number) {
  const liste = valeurs.includes(courante) ? valeurs : [courante, ...valeurs];
  return liste.map((v) => (
    <option key={v} value={v}>
      {v > 1 ? `${v} tâches à la fois` : "1 tâche à la fois"}
    </option>
  ));
}

export function Reglages() {
  const [charge, setCharge] = useState<ReglagesApi | null>(null);
  const [brouillon, setBrouillon] = useState<Brouillon | null>(null);
  const [erreurChargement, setErreurChargement] = useState<string | null>(null);
  const [erreurEnregistrement, setErreurEnregistrement] = useState<string | null>(null);
  const [cles, setCles] = useState<Record<ServiceAvecCle, string>>({ meshy: "", claude: "", itchio: "" });
  const [effacees, setEffacees] = useState<Record<ServiceAvecCle, boolean>>({ meshy: false, claude: false, itchio: false });
  const [tests, setTests] = useState<Record<ServiceTestable, EtatService>>(() => testsInitiaux(undefined));
  const [enregistrement, setEnregistrement] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const refMinuteur = useRef<number | undefined>(undefined);

  const charger = useCallback(async () => {
    setErreurChargement(null);
    try {
      const r = await api<ReglagesApi>("/reglages");
      setCharge(r);
      setBrouillon(sansEtat(r));
      setCles({ meshy: "", claude: "", itchio: "" });
      setEffacees({ meshy: false, claude: false, itchio: false });
      setTests(testsInitiaux(r.etat.outils));
    } catch (e) {
      setErreurChargement(messageErreur(e));
    }
  }, []);

  useEffect(() => {
    charger();
    return () => window.clearTimeout(refMinuteur.current);
  }, [charger]);

  const modifier = (fn: (b: Brouillon) => void) => {
    setBrouillon((b) => {
      if (!b) return b;
      const copie = JSON.parse(JSON.stringify(b)) as Brouillon;
      fn(copie);
      return copie;
    });
  };

  const cleEnvoyee = (s: ServiceAvecCle): { cle_api?: string | null } => {
    if (effacees[s]) return { cle_api: null };
    const v = cles[s];
    return v ? { cle_api: v } : {};
  };

  const enregistrer = async () => {
    if (!brouillon) return;
    const corps: ReglagesEnvoyes = {
      services: {
        meshy: { ...brouillon.services.meshy, ...cleEnvoyee("meshy") },
        claude: { ...brouillon.services.claude, ...cleEnvoyee("claude") },
        comfyui: { ...brouillon.services.comfyui },
        itchio: { ...brouillon.services.itchio, ...cleEnvoyee("itchio") },
      },
      outils: brouillon.outils,
      bibliotheque: brouillon.bibliotheque,
      files: brouillon.files,
      notifications: brouillon.notifications,
    };
    setEnregistrement(true);
    setErreurEnregistrement(null);
    try {
      const r = await api<ReglagesApi>("/reglages", { method: "PUT", body: JSON.stringify(corps) });
      setCharge(r);
      setBrouillon(sansEtat(r));
      setCles({ meshy: "", claude: "", itchio: "" });
      setEffacees({ meshy: false, claude: false, itchio: false });
      setConfirmation("Réglages enregistrés");
      window.clearTimeout(refMinuteur.current);
      refMinuteur.current = window.setTimeout(() => setConfirmation(null), DUREE_CONFIRMATION_MS);
    } catch (e) {
      setErreurEnregistrement(messageErreur(e));
    } finally {
      setEnregistrement(false);
    }
  };

  const tester = async (service: ServiceTestable) => {
    setTests((t) => ({ ...t, [service]: { etat: "Test en cours…", message: "", ok: null } }));
    try {
      const r = await api<ResultatTest>(`/reglages/tester/${service}`, { method: "POST" });
      setTests((t) => ({ ...t, [service]: { etat: r.etat, message: r.message, ok: r.ok } }));
    } catch (e) {
      setTests((t) => ({ ...t, [service]: { etat: "Erreur", message: messageErreur(e), ok: false } }));
    }
  };

  if (erreurChargement) {
    return (
      <div className="reglages">
        <Entete />
        <Erreur message={erreurChargement} onReessayer={charger} />
      </div>
    );
  }
  if (!charge || !brouillon) {
    return (
      <div className="reglages">
        <Entete />
        <Chargement texte="Lecture des réglages…" />
      </div>
    );
  }

  const { services, outils, bibliotheque, files, notifications } = brouillon;
  const { etat } = charge;
  const solde = etat.meshy_solde;

  const messageTest = (service: ServiceTestable) => {
    const t = tests[service];
    if (!t.message) return null;
    return <span className={`reglages__message-test${t.ok === false ? " reglages__message-test--erreur" : ""}`}>{t.message}</span>;
  };

  return (
    <form
      className="reglages"
      onSubmit={(e) => {
        e.preventDefault();
        enregistrer();
      }}
    >
      <Entete />

      {/* ---------- Services en ligne ---------- */}
      <section aria-labelledby="svc-h" className="reglages__section">
        <h2 id="svc-h" className="reglages__h2">
          Services en ligne
        </h2>

        <div className="reglages__carte">
          <div className="reglages__entete">
            <h3>Meshy</h3>
            <Pastille etat={tests.meshy.etat} />
            <span className="reglages__description">Voie IA et images de référence</span>
            <Interrupteur nom="meshy" libelle="Mode Meshy" valeur={services.meshy.mode} onChange={(m) => modifier((b) => (b.services.meshy.mode = m))} />
            <button type="button" className="bouton bouton--petit" onClick={() => tester("meshy")} disabled={tests.meshy.etat === "Test en cours…"}>
              Tester la connexion
            </button>
            {messageTest("meshy")}
          </div>
          <dl className="reglages__dl">
            <Ligne libelle="Clé API" htmlFor="meshy-key">
              <ChampCle
                id="meshy-key"
                definie={services.meshy.cle_api_definie}
                apercu={services.meshy.cle_api_apercu}
                valeur={cles.meshy}
                effacee={effacees.meshy}
                note="Jamais écrite dans la bibliothèque"
                onChange={(v) => setCles((c) => ({ ...c, meshy: v }))}
                onEffacer={(v) => setEffacees((e) => ({ ...e, meshy: v }))}
              />
            </Ligne>
            <Ligne libelle="Solde">
              {solde ? (
                <span>
                  <span className="mono">
                    {formatNombre.format(solde.restants)} / {formatNombre.format(solde.total)}
                  </span>{" "}
                  crédits restants <span className="secondaire">· lu par l'API à l'ouverture de l'app</span>
                </span>
              ) : (
                <span className="secondaire">Solde non lu</span>
              )}
            </Ligne>
            <Ligne libelle="Crédits mensuels" htmlFor="meshy-credits">
              <input
                id="meshy-credits"
                type="number"
                min={0}
                className="champ champ--nombre"
                value={services.meshy.credits_mensuels}
                onChange={(e) => modifier((b) => (b.services.meshy.credits_mensuels = Number(e.target.value)))}
              />
              <span className="note">Total de ton offre : base de la jauge du menu et de l'alerte.</span>
            </Ligne>
            <Ligne libelle="Renouvellement" htmlFor="meshy-renew">
              <select
                id="meshy-renew"
                className="champ"
                value={services.meshy.renouvellement_jour}
                onChange={(e) => modifier((b) => (b.services.meshy.renouvellement_jour = Number(e.target.value) as RenouvellementJour))}
              >
                <option value={1}>Le 1er de chaque mois</option>
                <option value={15}>Le 15 de chaque mois</option>
              </select>
              <span className="note">L'API donne le solde, pas la date : elle se règle ici.</span>
            </Ligne>
            <Ligne libelle="Alerte" htmlFor="meshy-alert">
              <select
                id="meshy-alert"
                className="champ"
                value={services.meshy.alerte_pct}
                onChange={(e) => modifier((b) => (b.services.meshy.alerte_pct = Number(e.target.value) as AlertePct))}
              >
                <option value={80}>Prévenir à 80 % des crédits du mois</option>
                <option value={90}>Prévenir à 90 %</option>
                <option value={0}>Ne pas prévenir</option>
              </select>
            </Ligne>
          </dl>
        </div>

        <div className="reglages__carte">
          <div className="reglages__entete">
            <h3>API Claude</h3>
            <Pastille etat={tests.claude.etat} />
            <span className="reglages__description">Liste du brief et avis IA ; distincte de ton abonnement Claude Code</span>
            <Interrupteur nom="claude" libelle="Mode API Claude" valeur={services.claude.mode} onChange={(m) => modifier((b) => (b.services.claude.mode = m))} />
            <button type="button" className="bouton bouton--petit" onClick={() => tester("claude")} disabled={tests.claude.etat === "Test en cours…"}>
              Tester la connexion
            </button>
            {messageTest("claude")}
          </div>
          <dl className="reglages__dl">
            <Ligne libelle="Clé API" htmlFor="claude-key">
              <ChampCle
                id="claude-key"
                definie={services.claude.cle_api_definie}
                apercu={services.claude.cle_api_apercu}
                valeur={cles.claude}
                effacee={effacees.claude}
                note="Créée dans la Console Anthropic"
                onChange={(v) => setCles((c) => ({ ...c, claude: v }))}
                onEffacer={(v) => setEffacees((e) => ({ ...e, claude: v }))}
              />
            </Ligne>
            <Ligne libelle="Modèle" htmlFor="claude-model">
              <select
                id="claude-model"
                className="champ"
                value={services.claude.modele}
                onChange={(e) => modifier((b) => (b.services.claude.modele = e.target.value as ModeleClaude))}
              >
                <option value="claude-sonnet-5-5">Sonnet 5.5</option>
                <option value="claude-haiku-5-5">Haiku 5.5</option>
              </select>
            </Ligne>
            <Ligne libelle="Plafond mensuel" htmlFor="claude-cap">
              <input
                id="claude-cap"
                type="number"
                min={1}
                step="0.5"
                className="champ champ--nombre"
                value={services.claude.plafond_mensuel_usd}
                onChange={(e) => modifier((b) => (b.services.claude.plafond_mensuel_usd = Number(e.target.value)))}
              />
              <span>$</span>
              <span className="note">Règle le même plafond dans la Console : c'est elle qui bloque vraiment.</span>
            </Ligne>
            <Ligne libelle="Dépensé ce mois">
              <span className="secondaire">Suivi des dépenses : arrive à l'étape 4 du plan.</span>
            </Ligne>
          </dl>
        </div>

        <div className="reglages__carte">
          <div className="reglages__entete">
            <h3>itch.io</h3>
            <Pastille etat={tests.itchio.etat} />
            <span className="reglages__description">Publication des packs avec butler</span>
            <Interrupteur nom="itchio" libelle="Mode itch.io" valeur={services.itchio.mode} onChange={(m) => modifier((b) => (b.services.itchio.mode = m))} />
            <button type="button" className="bouton bouton--petit" onClick={() => tester("itchio")} disabled={tests.itchio.etat === "Test en cours…"}>
              Tester butler
            </button>
            {messageTest("itchio")}
          </div>
          <dl className="reglages__dl">
            <Ligne libelle="Clé API" htmlFor="itch-key">
              <ChampCle
                id="itch-key"
                definie={services.itchio.cle_api_definie}
                apercu={services.itchio.cle_api_apercu}
                valeur={cles.itchio}
                effacee={effacees.itchio}
                note="Clé butler, créée sur itch.io"
                onChange={(v) => setCles((c) => ({ ...c, itchio: v }))}
                onEffacer={(v) => setEffacees((e) => ({ ...e, itchio: v }))}
              />
            </Ligne>
            <Ligne libelle="Compte itch.io" htmlFor="itch-project">
              <input
                id="itch-project"
                type="text"
                className="champ champ--mono champ--large"
                value={services.itchio.compte}
                onChange={(e) => modifier((b) => (b.services.itchio.compte = e.target.value))}
              />
              <span className="note">Chaque pack a sa propre page : {services.itchio.compte || "ton-compte"}/nom-du-pack</span>
            </Ligne>
            <Ligne libelle="Canal" htmlFor="itch-channel">
              <input
                id="itch-channel"
                type="text"
                className="champ champ--mono champ--canal"
                value={services.itchio.canal}
                onChange={(e) => modifier((b) => (b.services.itchio.canal = e.target.value))}
              />
              <span className="note">Le dossier part sur ce canal à chaque publication</span>
            </Ligne>
            <Ligne libelle="butler" htmlFor="butler-path">
              <input
                id="butler-path"
                type="text"
                className="champ champ--mono champ--large"
                value={outils.butler.chemin}
                onChange={(e) => modifier((b) => (b.outils.butler.chemin = e.target.value))}
              />
              <span className="note">Exécutable butler sur ta machine</span>
            </Ligne>
            <Ligne libelle="Déclaration IA">
              <span>
                Faite à la main sur la page itch.io <span className="secondaire">· à revoir si un pack contient un nouveau générateur</span>
              </span>
            </Ligne>
          </dl>
        </div>
      </section>

      {/* ---------- Outils sur ta machine ---------- */}
      <section aria-labelledby="tools-h" className="reglages__section">
        <h2 id="tools-h" className="reglages__h2">
          Outils sur ta machine
        </h2>
        <div className="reglages__grille">
          <div className="reglages__carte reglages__carte--outil">
            <div className="reglages__entete reglages__entete--outil">
              <h3>Blender</h3>
              <Pastille etat={tests.blender.etat} />
              <button type="button" className="bouton bouton--petit" onClick={() => tester("blender")} disabled={tests.blender.etat === "Test en cours…"}>
                Tester
              </button>
              {messageTest("blender")}
            </div>
            <label htmlFor="blender-path" className="reglages__etiquette">
              Exécutable
            </label>
            <input
              id="blender-path"
              type="text"
              className="champ champ--mono"
              value={outils.blender.chemin}
              onChange={(e) => modifier((b) => (b.outils.blender.chemin = e.target.value))}
            />
            {!outils.blender.chemin && etat.outils.blender.suggestion ? (
              <button
                type="button"
                className="bouton bouton--petit"
                onClick={() => modifier((b) => (b.outils.blender.chemin = etat.outils.blender.suggestion ?? ""))}
              >
                Utiliser ce chemin : <span className="mono">{etat.outils.blender.suggestion}</span>
              </button>
            ) : null}
            <p className="note">Générateurs code, finition, tests, rendus et export FBX. Version figée : tous les lots passent par le même Blender.</p>
          </div>

          <div className="reglages__carte reglages__carte--outil">
            <div className="reglages__entete reglages__entete--outil">
              <h3>ComfyUI</h3>
              <Pastille etat={tests.comfyui.etat} />
              <Interrupteur nom="comfyui" libelle="Mode ComfyUI" valeur={services.comfyui.mode} onChange={(m) => modifier((b) => (b.services.comfyui.mode = m))} />
              <button type="button" className="bouton bouton--petit" onClick={() => tester("comfyui")} disabled={tests.comfyui.etat === "Test en cours…"}>
                Tester
              </button>
              {messageTest("comfyui")}
            </div>
            <label htmlFor="comfy-url" className="reglages__etiquette">
              Adresse
            </label>
            <input
              id="comfy-url"
              type="text"
              className="champ champ--mono"
              value={services.comfyui.url}
              onChange={(e) => modifier((b) => (b.services.comfyui.url = e.target.value))}
            />
            <p className="note">Les workflows disponibles, la carte graphique et sa mémoire sont lus au test de connexion.</p>
          </div>

          <div className="reglages__carte reglages__carte--outil">
            <div className="reglages__entete reglages__entete--outil">
              <h3>glTF-Validator</h3>
              <Pastille etat={tests.gltf_validator.etat} />
              <button
                type="button"
                className="bouton bouton--petit"
                onClick={() => tester("gltf_validator")}
                disabled={tests.gltf_validator.etat === "Test en cours…"}
              >
                Tester
              </button>
              {messageTest("gltf_validator")}
            </div>
            <label htmlFor="validator-path" className="reglages__etiquette">
              Exécutable
            </label>
            <input
              id="validator-path"
              type="text"
              className="champ champ--mono"
              value={outils.gltf_validator.chemin}
              onChange={(e) => modifier((b) => (b.outils.gltf_validator.chemin = e.target.value))}
            />
            <p className="note">Vérifie chaque GLB contre la norme glTF 2.0 ; son rapport JSON alimente les tests.</p>
          </div>

          <div className="reglages__carte reglages__carte--outil">
            <div className="reglages__entete reglages__entete--outil">
              <h3>Bibliothèque</h3>
              <Pastille etat={tests.git_lfs.etat} />
              <button type="button" className="bouton bouton--petit" onClick={() => tester("git_lfs")} disabled={tests.git_lfs.etat === "Test en cours…"}>
                Tester Git LFS
              </button>
              {messageTest("git_lfs")}
            </div>
            <label htmlFor="lib-path" className="reglages__etiquette">
              Dossier
            </label>
            <input
              id="lib-path"
              type="text"
              className="champ champ--mono"
              value={bibliotheque.dossier}
              onChange={(e) => modifier((b) => (b.bibliotheque.dossier = e.target.value))}
            />
            <label htmlFor="lib-purge" className="reglages__etiquette">
              Effacer les fichiers des essais rejetés après (jours)
            </label>
            <input
              id="lib-purge"
              type="number"
              min={0}
              className="champ champ--nombre"
              value={bibliotheque.purge_rejets_jours}
              onChange={(e) => modifier((b) => (b.bibliotheque.purge_rejets_jours = Number(e.target.value)))}
            />
            <p className="note">
              Relatif au dossier du projet. Seules les versions gardées passent par Git LFS. Les fichiers des essais rejetés restent en local et sont
              effacés après {pluriel(bibliotheque.purge_rejets_jours, "jour", "jours")} ; leur motif et leur image sont conservés.
            </p>
          </div>
        </div>
      </section>

      {/* ---------- File de tâches ---------- */}
      <section aria-labelledby="queue-h" className="reglages__carte">
        <h2 id="queue-h" className="reglages__h2">
          File de tâches
        </h2>
        <dl className="reglages__dl">
          <Ligne libelle="File carte graphique" htmlFor="q-gpu">
            <select id="q-gpu" className="champ" value={files.gpu} onChange={(e) => modifier((b) => (b.files.gpu = Number(e.target.value)))}>
              {optionsTaches([1], files.gpu)}
            </select>
            <span className="note">ComfyUI : ta carte ne fait tourner qu'un modèle à la fois.</span>
          </Ligne>
          <Ligne libelle="File Meshy" htmlFor="q-meshy">
            <select id="q-meshy" className="champ" value={files.meshy} onChange={(e) => modifier((b) => (b.files.meshy = Number(e.target.value)))}>
              {optionsTaches([1, 3, 5], files.meshy)}
            </select>
            <span className="note">Les calculs se font chez Meshy ; reste sous la limite de ton offre.</span>
          </Ligne>
          <Ligne libelle="File Blender" htmlFor="q-blender">
            <select id="q-blender" className="champ" value={files.blender} onChange={(e) => modifier((b) => (b.files.blender = Number(e.target.value)))}>
              {optionsTaches([1, 2], files.blender)}
            </select>
            <span className="note">Générateurs code, finition, tests et rendus, sur ton processeur.</span>
          </Ligne>
          <Ligne libelle="Relances automatiques" htmlFor="q-retries">
            <input
              id="q-retries"
              type="number"
              min={0}
              max={5}
              className="champ champ--nombre"
              value={files.relances_max}
              onChange={(e) => modifier((b) => (b.files.relances_max = Number(e.target.value)))}
            />
            <span className="note">par objet, seulement quand la finition ne peut pas corriger</span>
          </Ligne>
          <Ligne libelle="Notifications" colonne>
            <label className="case">
              <input type="checkbox" checked={notifications.app} onChange={(e) => modifier((b) => (b.notifications.app = e.target.checked))} />
              Dans l'app : revue prête, échec après {pluriel(files.relances_max, "relance", "relances")}, banc terminé, crédits à{" "}
              {services.meshy.alerte_pct > 0 ? `${services.meshy.alerte_pct} %` : "l'alerte réglée"}
            </label>
            <label className="case">
              <input type="checkbox" checked={notifications.bureau} onChange={(e) => modifier((b) => (b.notifications.bureau = e.target.checked))} />
              Aussi en notification de l'ordinateur, même onglet fermé : revue prête, échec après {pluriel(files.relances_max, "relance", "relances")}
            </label>
          </Ligne>
        </dl>
      </section>

      {erreurEnregistrement ? <Erreur message={erreurEnregistrement} /> : null}

      <div className="reglages__barre">
        {confirmation ? (
          <span className="reglages__confirmation" role="status" aria-live="polite">
            {confirmation}
          </span>
        ) : null}
        <button type="button" className="bouton" onClick={charger} disabled={enregistrement}>
          Annuler
        </button>
        <button type="submit" className="bouton bouton--primaire" disabled={enregistrement}>
          {enregistrement ? "Enregistrement…" : "Enregistrer"}
        </button>
      </div>
    </form>
  );
}

function Entete() {
  return (
    <div>
      <h1 className="page-titre">Réglages</h1>
      <p className="page-sous-titre">
        Les clés des services, les outils de ta machine et les limites que l'app respecte. Tout est rangé dans un fichier de configuration local,
        hors de la bibliothèque et de Git.
      </p>
    </div>
  );
}
