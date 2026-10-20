-- 050 · Références (étape 6) : les propositions faites pour chaque objet (images Meshy, variantes Blender,
-- image donnée par l'utilisateur), la proposition choisie et la consigne réécrite à la main.
CREATE TABLE IF NOT EXISTS propositions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  objet_id    INTEGER NOT NULL REFERENCES objets(id) ON DELETE CASCADE,
  serie       INTEGER NOT NULL DEFAULT 0,       -- 1 : la première série de 4, 2 : « 4 autres »… ; 0 : image donnée
  rang        INTEGER NOT NULL DEFAULT 0,       -- place dans la série (0 à 3)
  genre       TEXT NOT NULL CHECK (genre IN ('image', 'variante', 'perso')),
  fichier     TEXT NOT NULL,                    -- dans lots/<lot>/<objet>/references/
  legende     TEXT NOT NULL DEFAULT '',
  params_json TEXT,                             -- variante : paramètres du générateur ; image : consigne et modèle
  credits     INTEGER NOT NULL DEFAULT 0,
  simule      INTEGER NOT NULL DEFAULT 0,
  tache_id    INTEGER,
  cree_le     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_propositions_objet ON propositions(objet_id, serie, rang);

ALTER TABLE objets ADD COLUMN reference_id INTEGER REFERENCES propositions(id) ON DELETE SET NULL;
ALTER TABLE objets ADD COLUMN consigne TEXT;  -- NULL : la consigne écrite par l'app
