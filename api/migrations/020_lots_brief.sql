-- 020 · Lots et Brief : lots (duplication, proposition, crédits prévus), objets (nature, voie forcée,
-- raison, voies réutilisé et hors périmètre), pièces des objets mixtes, règles de routage ordonnées,
-- demandes de générateurs pour Claude Code.
ALTER TABLE lots ADD COLUMN duplique_de_id INTEGER REFERENCES lots(id) ON DELETE SET NULL;
ALTER TABLE lots ADD COLUMN proposition_tache_id INTEGER;
ALTER TABLE lots ADD COLUMN credits_prevus INTEGER NOT NULL DEFAULT 0;
ALTER TABLE lots ADD COLUMN nom_propose TEXT NOT NULL DEFAULT '';

-- SQLite ne modifie pas une contrainte CHECK : la table objets (vide à ce stade) est recréée.
CREATE TABLE objets_v2 (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id             INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
  nom                TEXT NOT NULL,
  type_objet         TEXT NOT NULL DEFAULT '',
  description        TEXT NOT NULL DEFAULT '',
  categorie          TEXT NOT NULL DEFAULT '',
  nature             TEXT NOT NULL DEFAULT '',
  dimensions_json    TEXT,
  voie               TEXT NOT NULL DEFAULT 'a_creer'
                     CHECK (voie IN ('code','ia','mixte','cc0','a_creer','reutilise','hors_perimetre')),
  voie_forcee        INTEGER NOT NULL DEFAULT 0,
  raison_voie        TEXT NOT NULL DEFAULT '',
  regle_id           INTEGER,
  generateur         TEXT,
  etape              TEXT NOT NULL DEFAULT 'brief'
                     CHECK (etape IN ('brief','references','generation','finition','tests',
                                      'rendus','revue','garde','rejete','archive')),
  retire             INTEGER NOT NULL DEFAULT 0,
  pieces_json        TEXT,
  reutilise_asset_id TEXT,
  symetrique         INTEGER,
  famille            TEXT NOT NULL DEFAULT '',
  materiaux_json     TEXT,
  parametres_json    TEXT,
  cc0_ref            TEXT,
  ordre              INTEGER NOT NULL DEFAULT 0
);
INSERT INTO objets_v2 (id, lot_id, nom, type_objet, description, categorie, dimensions_json, voie, generateur,
                       etape, retire, pieces_json, reutilise_asset_id, ordre)
  SELECT id, lot_id, nom, type_objet, description, categorie, dimensions_json, voie, generateur,
         etape, retire, pieces_json, reutilise_asset_id, ordre FROM objets;
DROP TABLE objets;
ALTER TABLE objets_v2 RENAME TO objets;
CREATE INDEX IF NOT EXISTS idx_objets_lot ON objets(lot_id, ordre);
CREATE INDEX IF NOT EXISTS idx_objets_etape ON objets(etape);

CREATE TABLE IF NOT EXISTS pieces (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  objet_id   INTEGER NOT NULL REFERENCES objets(id) ON DELETE CASCADE,
  ordre      INTEGER NOT NULL DEFAULT 0,
  nom        TEXT NOT NULL,
  nature     TEXT NOT NULL DEFAULT '',
  type_objet TEXT NOT NULL DEFAULT '',
  voie       TEXT NOT NULL DEFAULT 'a_creer'
             CHECK (voie IN ('code','ia','mixte','cc0','a_creer','reutilise','hors_perimetre')),
  generateur TEXT,
  etape      TEXT NOT NULL DEFAULT 'brief'
);
CREATE INDEX IF NOT EXISTS idx_pieces_objet ON pieces(objet_id, ordre);

-- Les 7 règles de routage, dans l'ordre de la maquette (Générateurs). Modifiables à l'étape 11.
DROP TABLE regles_routage;
CREATE TABLE regles_routage (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  ordre              INTEGER NOT NULL DEFAULT 0,
  condition          TEXT NOT NULL,
  libelle_quand      TEXT NOT NULL,
  libelle_alors      TEXT NOT NULL,
  voie               TEXT NOT NULL CHECK (voie IN ('code','ia','mixte','cc0','a_creer','reutilise','hors_perimetre')),
  generateur         TEXT,
  generateur_secours TEXT,
  actif              INTEGER NOT NULL DEFAULT 1
);
INSERT INTO regles_routage (ordre, condition, libelle_quand, libelle_alors, voie, generateur, generateur_secours) VALUES
  (1, 'deja_en_bibliotheque', 'Déjà dans ta bibliothèque', 'Réutiliser, rien à fabriquer', 'reutilise', NULL, NULL),
  (2, 'equivalent_cc0', 'Équivalent CC0 déjà disponible', 'Catalogue CC0, puis finition, tests et revue', 'cc0', 'cc0', NULL),
  (3, 'geometrique_avec_generateur', 'Géométrique, symétrique ou fin, avec un générateur écrit : bouclier, arme, mobilier simple', 'Générateurs par code', 'code', 'code', NULL),
  (4, 'geometrique_ornemental', 'Géométrique avec une partie ornementale : colonne à chapiteau', 'Mixte : code + Meshy 6', 'mixte', 'meshy', NULL),
  (5, 'ornemental', 'Ornemental ou organique non déformable', 'Meshy 6', 'ia', 'meshy', NULL),
  (6, 'geometrique_sans_generateur', 'Géométrique sans générateur écrit', 'À créer avec Claude Code, ou voie IA', 'a_creer', NULL, 'meshy'),
  (7, 'personnage', 'Personnage ou créature', 'Hors périmètre pour l''instant', 'hors_perimetre', NULL, NULL);

CREATE TABLE IF NOT EXISTS demandes_generateurs (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  type_objet         TEXT NOT NULL UNIQUE,
  lot_id             INTEGER REFERENCES lots(id) ON DELETE SET NULL,
  objet_id           INTEGER REFERENCES objets(id) ON DELETE SET NULL,
  chemin_md          TEXT NOT NULL,
  ecrite_le          TEXT,
  script_detecte_le  TEXT,
  generateur         TEXT,
  etat               TEXT NOT NULL DEFAULT 'a_ecrire'
                     CHECK (etat IN ('a_ecrire','ecrite','script_detecte'))
);
