import { useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api/client";
import { signalerChangement } from "../api/rafraichissement";
import type { EtatTache, EtatWorker, JournalTache, TacheVue } from "../api/types";
import "./Taches.css";

const ETATS: Record<EtatTache, { libelle: string; ton: string }> = {
  en_attente: { libelle: "En attente", ton: "idle" },
  en_cours: { libelle: "En cours", ton: "accent" },
  terminee: { libelle: "Terminée", ton: "good" },
  echouee: { libelle: "Échouée", ton: "warn" },
  annulee: { libelle: "Annulée", ton: "idle" },
};

function heure(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function depuis(iso: string | null): string {
  if (!iso) return "jamais";
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `il y a ${s} s`;
  if (s < 3600) return `il y a ${Math.round(s / 60)} min`;
  return new Date(iso).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Le worker tourne-t-il ? Sans lui, les tâches attendent : l'écran le dit au lieu d'attendre en silence. */
export function EtatDuWorker({ worker }: { worker: EtatWorker }) {
  if (worker.actif) {
    return (
      <p role="status" className="worker worker--actif">
        <span aria-hidden="true" className="worker__point" />
        Worker actif · {worker.en_cours} en cours · {worker.en_attente} en attente
      </p>
    );
  }
  return (
    <p role="status" className="worker worker--arrete">
      <span aria-hidden="true" className="worker__point" />
      Le worker ne tourne pas{worker.en_attente > 0 ? ` : ${worker.en_attente} tâche${worker.en_attente > 1 ? "s attendent" : " attend"}` : ""}. Il se lance
      avec l'app (<span className="mono">python dev.py</span>) · dernier signe de vie : {depuis(worker.battu_le)}.
    </p>
  );
}

/** Une liste de tâches de la file : état, tentatives, avancement, erreur, journal ; Relancer et Annuler. */
export function ListeTaches({ taches, onChangement, vide }: { taches: TacheVue[]; onChangement: () => void; vide: string }) {
  if (taches.length === 0) return <p className="secondaire taches__vide">{vide}</p>;
  return (
    <ul role="list" className="taches">
      {taches.map((t) => (
        <LigneTache key={t.id} tache={t} onChangement={onChangement} />
      ))}
    </ul>
  );
}

function LigneTache({ tache: t, onChangement }: { tache: TacheVue; onChangement: () => void }) {
  const [journal, setJournal] = useState<JournalTache | null>(null);
  const [ouvert, setOuvert] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);
  const etat = ETATS[t.etat];

  const agir = async (action: "relancer" | "annuler") => {
    setOccupe(true);
    setErreur(null);
    try {
      await api(`/taches/${t.id}/${action}`, { method: "POST" });
      signalerChangement();
      onChangement();
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  const basculerJournal = async () => {
    if (ouvert) {
      setOuvert(false);
      return;
    }
    setOuvert(true);
    try {
      setJournal(await api<JournalTache>(`/taches/${t.id}/journal`));
    } catch (e) {
      setErreur(messageErreur(e));
    }
  };

  return (
    <li className="tache">
      <div className="tache__ligne">
        <div className="tache__texte">
          <span className="tache__nom">{t.libelle}</span>
          <span className="tache__meta">
            {t.contexte ? (
              <>
                <Link to={t.contexte.lien}>{t.contexte.libelle}</Link> ·{" "}
              </>
            ) : null}
            file {t.libelle_file} · tentative {t.tentatives} sur {t.max_tentatives}
            {t.reprise_le && t.etat === "en_attente" ? ` · nouvel essai à ${heure(t.reprise_le)}` : ""}
          </span>
        </div>
        <span className={`ton ton--${etat.ton}`}>{etat.libelle}</span>
        <div className="tache__actions">
          <button type="button" className="tache__icone" aria-expanded={ouvert} aria-label={`Journal : ${t.libelle}`} title="Journal" onClick={basculerJournal}>
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 3.5 H13 M3 8 H13 M3 12.5 H9" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" }} />
            </svg>
          </button>
          {t.peut_relancer ? (
            <button type="button" className="bouton bouton--petit" onClick={() => agir("relancer")} disabled={occupe}>
              Relancer
            </button>
          ) : null}
          {t.peut_annuler ? (
            <button type="button" className="bouton bouton--petit" aria-label={`Annuler : ${t.libelle}`} onClick={() => agir("annuler")} disabled={occupe}>
              Annuler
            </button>
          ) : null}
        </div>
      </div>
      {t.progression && t.etat === "en_cours" ? (
        <div className="tache__progression">
          <div className="tache__barre" aria-hidden="true">
            <div style={{ width: `${t.progression.pct}%` }} />
          </div>
          <span>{t.progression.texte}</span>
        </div>
      ) : null}
      {t.erreur && t.etat !== "terminee" ? <p className="tache__erreur">{t.erreur}</p> : null}
      {erreur ? (
        <p role="alert" className="tache__erreur">
          {erreur}
        </p>
      ) : null}
      {ouvert ? (
        <ol role="list" aria-label={`Journal de la tâche ${t.id}`} className="tache__journal">
          {!journal ? <li className="secondaire">Chargement…</li> : null}
          {journal?.evenements.map((e) => (
            <li key={e.id} className={`tache__evenement tache__evenement--${e.niveau}`}>
              <time dateTime={e.date}>{heure(e.date)}</time>
              <span>
                {e.titre}
                {e.texte ? ` · ${e.texte}` : ""}
              </span>
            </li>
          ))}
        </ol>
      ) : null}
    </li>
  );
}
