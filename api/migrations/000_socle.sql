-- 000 · Socle : modèle de données A1, file de tâches, journal, coûts, recherche FTS5.
-- Dates en ISO 8601 UTC. Identifiants entiers, sauf assets.id (ex. ROM_PROP_Scutum_A).

CREATE TABLE IF NOT EXISTS styles (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nom         TEXT NOT NULL,
  theme       TEXT NOT NULL,
  version     INTEGER NOT NULL DEFAULT 0,
  chemin_yaml TEXT NOT NULL,
  cree_le     TEXT NOT NULL,
  parent_id   INTEGER REFERENCES styles(id) ON DELETE SET NULL,
  actif       INTEGER NOT NULL DEFAULT 1,
  UNIQUE (nom, version)
);

CREATE TABLE IF NOT EXISTS lots (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  nom       TEXT NOT NULL,
  theme     TEXT NOT NULL,
  besoin    TEXT NOT NULL DEFAULT '',
  direction TEXT NOT NULL DEFAULT '',
  style_id  INTEGER REFERENCES styles(id) ON DELETE SET NULL,
  etat      TEXT NOT NULL DEFAULT 'brouillon'
            CHECK (etat IN ('brouillon','en_cours','termine','archive')),
  cree_le   TEXT NOT NULL,
  maj_le    TEXT NOT NULL,
  dossier   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_lots_etat ON lots(etat);

CREATE TABLE IF NOT EXISTS objets (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id             INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
  nom                TEXT NOT NULL,
  type_objet         TEXT NOT NULL DEFAULT '',
  description        TEXT NOT NULL DEFAULT '',
  categorie          TEXT NOT NULL DEFAULT '',
  dimensions_json    TEXT,
  voie               TEXT NOT NULL DEFAULT 'a_creer'
                     CHECK (voie IN ('code','ia','mixte','cc0','a_creer')),
  generateur         TEXT,
  etape              TEXT NOT NULL DEFAULT 'brief'
                     CHECK (etape IN ('brief','references','generation','finition','tests',
                                      'rendus','revue','garde','rejete','archive')),
  retire             INTEGER NOT NULL DEFAULT 0,
  pieces_json        TEXT,
  reutilise_asset_id TEXT,
  ordre              INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_objets_lot ON objets(lot_id, ordre);
CREATE INDEX IF NOT EXISTS idx_objets_etape ON objets(etape);

CREATE TABLE IF NOT EXISTS essais (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  objet_id           INTEGER NOT NULL REFERENCES objets(id) ON DELETE CASCADE,
  numero             INTEGER NOT NULL DEFAULT 1,
  generateur         TEXT,
  params_json        TEXT,
  source_json        TEXT,
  etat               TEXT NOT NULL DEFAULT 'en_attente',
  dossier            TEXT NOT NULL DEFAULT '',
  cout_credits       INTEGER NOT NULL DEFAULT 0,
  cout_usd           REAL NOT NULL DEFAULT 0,
  debute_le          TEXT,
  fini_le            TEXT,
  erreur             TEXT,
  rapport_tests_json TEXT,
  avis_ia            TEXT,
  UNIQUE (objet_id, numero)
);

CREATE TABLE IF NOT EXISTS assets (
  id                TEXT PRIMARY KEY,
  lot_id            INTEGER REFERENCES lots(id) ON DELETE SET NULL,
  objet_id          INTEGER REFERENCES objets(id) ON DELETE SET NULL,
  nom               TEXT NOT NULL,
  theme             TEXT NOT NULL,
  categorie         TEXT NOT NULL DEFAULT '',
  voie              TEXT NOT NULL DEFAULT 'code',
  statut            TEXT NOT NULL DEFAULT 'revue' CHECK (statut IN ('revue','garde','archive')),
  favori            INTEGER NOT NULL DEFAULT 0,
  version_active_id INTEGER,
  cree_le           TEXT NOT NULL,
  maj_le            TEXT NOT NULL,
  notes             TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_assets_statut ON assets(statut);
CREATE INDEX IF NOT EXISTS idx_assets_lot ON assets(lot_id);

CREATE TABLE IF NOT EXISTS versions (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id  TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  essai_id  INTEGER REFERENCES essais(id) ON DELETE SET NULL,
  numero    INTEGER NOT NULL DEFAULT 1,
  meta_json TEXT,
  dossier   TEXT NOT NULL DEFAULT '',
  tris_lod0 INTEGER,
  cree_le   TEXT NOT NULL,
  UNIQUE (asset_id, numero)
);

CREATE TABLE IF NOT EXISTS collections (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nom         TEXT NOT NULL UNIQUE,
  couleur     TEXT NOT NULL DEFAULT '#2B50C8',
  epinglee    INTEGER NOT NULL DEFAULT 0,
  publication TEXT
);

CREATE TABLE IF NOT EXISTS collections_assets (
  collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  asset_id      TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  PRIMARY KEY (collection_id, asset_id)
);

CREATE TABLE IF NOT EXISTS etiquettes (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  nom  TEXT NOT NULL UNIQUE,
  auto INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS etiquettes_assets (
  etiquette_id INTEGER NOT NULL REFERENCES etiquettes(id) ON DELETE CASCADE,
  asset_id     TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  PRIMARY KEY (etiquette_id, asset_id)
);

CREATE TABLE IF NOT EXISTS generateurs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nom         TEXT NOT NULL UNIQUE,
  type        TEXT NOT NULL CHECK (type IN ('code','meshy','comfyui','cc0')),
  actif       INTEGER NOT NULL DEFAULT 1,
  params_json TEXT,
  stats_json  TEXT
);

CREATE TABLE IF NOT EXISTS regles_routage (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ordre           INTEGER NOT NULL DEFAULT 0,
  categorie_objet TEXT,
  type_objet      TEXT,
  voie            TEXT NOT NULL CHECK (voie IN ('code','ia','mixte','cc0','a_creer')),
  generateur      TEXT
);

CREATE TABLE IF NOT EXISTS taches (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  type           TEXT NOT NULL,
  file           TEXT NOT NULL CHECK (file IN ('gpu','meshy','blender','api')),
  etat           TEXT NOT NULL DEFAULT 'en_attente'
                 CHECK (etat IN ('en_attente','en_cours','terminee','echouee','annulee')),
  params_json    TEXT,
  resultat_json  TEXT,
  erreur         TEXT,
  tentatives     INTEGER NOT NULL DEFAULT 0,
  max_tentatives INTEGER NOT NULL DEFAULT 3,
  priorite       INTEGER NOT NULL DEFAULT 0,
  lot_id         INTEGER REFERENCES lots(id) ON DELETE SET NULL,
  objet_id       INTEGER REFERENCES objets(id) ON DELETE SET NULL,
  essai_id       INTEGER REFERENCES essais(id) ON DELETE SET NULL,
  cree_le        TEXT NOT NULL,
  debute_le      TEXT,
  fini_le        TEXT,
  verrou         TEXT,
  verrou_le      TEXT,
  reprise_le     TEXT
);
CREATE INDEX IF NOT EXISTS idx_taches_file_etat ON taches(file, etat, priorite, id);
CREATE INDEX IF NOT EXISTS idx_taches_lot ON taches(lot_id);

CREATE TABLE IF NOT EXISTS evenements (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  date         TEXT NOT NULL,
  type         TEXT NOT NULL,
  niveau       TEXT NOT NULL DEFAULT 'info' CHECK (niveau IN ('debug','info','succes','alerte','erreur')),
  titre        TEXT NOT NULL,
  texte        TEXT NOT NULL DEFAULT '',
  lien         TEXT,
  lot_id       INTEGER REFERENCES lots(id) ON DELETE SET NULL,
  objet_id     INTEGER REFERENCES objets(id) ON DELETE SET NULL,
  tache_id     INTEGER REFERENCES taches(id) ON DELETE SET NULL,
  notification INTEGER NOT NULL DEFAULT 0,
  lu           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_evenements_date ON evenements(date);
CREATE INDEX IF NOT EXISTS idx_evenements_notif ON evenements(notification, lu, date);
CREATE INDEX IF NOT EXISTS idx_evenements_lot ON evenements(lot_id, date);

CREATE TABLE IF NOT EXISTS couts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  date          TEXT NOT NULL,
  service       TEXT NOT NULL,
  tache_id      INTEGER REFERENCES taches(id) ON DELETE SET NULL,
  credits       INTEGER NOT NULL DEFAULT 0,
  usd           REAL NOT NULL DEFAULT 0,
  tokens_entree INTEGER NOT NULL DEFAULT 0,
  tokens_sortie INTEGER NOT NULL DEFAULT 0,
  detail        TEXT
);
CREATE INDEX IF NOT EXISTS idx_couts_service_date ON couts(service, date);

CREATE TABLE IF NOT EXISTS bancs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  nom           TEXT NOT NULL,
  generateur_a  TEXT NOT NULL,
  generateur_b  TEXT NOT NULL,
  objets_json   TEXT,
  etat          TEXT NOT NULL DEFAULT 'en_attente',
  resultat_json TEXT,
  cree_le       TEXT NOT NULL,
  fini_le       TEXT,
  decision      TEXT
);

CREATE TABLE IF NOT EXISTS publications (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL,
  pack          TEXT NOT NULL,
  canal         TEXT NOT NULL,
  version       TEXT NOT NULL,
  date          TEXT NOT NULL,
  etat          TEXT NOT NULL DEFAULT 'en_attente',
  detail_json   TEXT
);

CREATE TABLE IF NOT EXISTS publications_versions (
  publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
  version_id     INTEGER NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
  PRIMARY KEY (publication_id, version_id)
);

-- Recherche globale (barre du haut). type et ref_id ne sont pas indexés.
CREATE VIRTUAL TABLE IF NOT EXISTS recherche USING fts5(
  nom, etiquettes, notes, lot, type UNINDEXED, ref_id UNINDEXED,
  tokenize = 'unicode61 remove_diacritics 2'
);

-- Assets --------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS recherche_assets_ai AFTER INSERT ON assets BEGIN
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom || ' ' || new.id, '', new.notes,
          COALESCE((SELECT nom FROM lots WHERE id = new.lot_id), ''), 'asset', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_assets_au AFTER UPDATE ON assets BEGIN
  DELETE FROM recherche WHERE type = 'asset' AND ref_id = old.id;
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom || ' ' || new.id,
          COALESCE((SELECT group_concat(e.nom, ' ') FROM etiquettes e
                    JOIN etiquettes_assets ea ON ea.etiquette_id = e.id
                    WHERE ea.asset_id = new.id), ''),
          new.notes,
          COALESCE((SELECT nom FROM lots WHERE id = new.lot_id), ''), 'asset', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_assets_ad AFTER DELETE ON assets BEGIN
  DELETE FROM recherche WHERE type = 'asset' AND ref_id = old.id;
END;
CREATE TRIGGER IF NOT EXISTS recherche_etiquettes_assets_ai AFTER INSERT ON etiquettes_assets BEGIN
  UPDATE recherche SET etiquettes = COALESCE((SELECT group_concat(e.nom, ' ') FROM etiquettes e
      JOIN etiquettes_assets ea ON ea.etiquette_id = e.id WHERE ea.asset_id = new.asset_id), '')
  WHERE type = 'asset' AND ref_id = new.asset_id;
END;
CREATE TRIGGER IF NOT EXISTS recherche_etiquettes_assets_ad AFTER DELETE ON etiquettes_assets BEGIN
  UPDATE recherche SET etiquettes = COALESCE((SELECT group_concat(e.nom, ' ') FROM etiquettes e
      JOIN etiquettes_assets ea ON ea.etiquette_id = e.id WHERE ea.asset_id = old.asset_id), '')
  WHERE type = 'asset' AND ref_id = old.asset_id;
END;

-- Lots ----------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS recherche_lots_ai AFTER INSERT ON lots BEGIN
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom, new.theme, new.besoin, new.nom, 'lot', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_lots_au AFTER UPDATE ON lots BEGIN
  DELETE FROM recherche WHERE type = 'lot' AND ref_id = old.id;
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom, new.theme, new.besoin, new.nom, 'lot', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_lots_ad AFTER DELETE ON lots BEGIN
  DELETE FROM recherche WHERE type = 'lot' AND ref_id = old.id;
END;

-- Collections et étiquettes ------------------------------------------------
CREATE TRIGGER IF NOT EXISTS recherche_collections_ai AFTER INSERT ON collections BEGIN
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom, '', '', '', 'collection', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_collections_au AFTER UPDATE ON collections BEGIN
  DELETE FROM recherche WHERE type = 'collection' AND ref_id = old.id;
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom, '', '', '', 'collection', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_collections_ad AFTER DELETE ON collections BEGIN
  DELETE FROM recherche WHERE type = 'collection' AND ref_id = old.id;
END;
CREATE TRIGGER IF NOT EXISTS recherche_etiquettes_ai AFTER INSERT ON etiquettes BEGIN
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom, new.nom, '', '', 'etiquette', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_etiquettes_au AFTER UPDATE ON etiquettes BEGIN
  DELETE FROM recherche WHERE type = 'etiquette' AND ref_id = old.id;
  INSERT INTO recherche(nom, etiquettes, notes, lot, type, ref_id)
  VALUES (new.nom, new.nom, '', '', 'etiquette', new.id);
END;
CREATE TRIGGER IF NOT EXISTS recherche_etiquettes_ad AFTER DELETE ON etiquettes BEGIN
  DELETE FROM recherche WHERE type = 'etiquette' AND ref_id = old.id;
END;
