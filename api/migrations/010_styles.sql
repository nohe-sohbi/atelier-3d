-- 010 · Styles : code, description, état, famille de versions, planche de référence.
ALTER TABLE styles ADD COLUMN code TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_styles_code ON styles(code);
ALTER TABLE styles ADD COLUMN description TEXT NOT NULL DEFAULT '';
ALTER TABLE styles ADD COLUMN direction TEXT NOT NULL DEFAULT 'stylise';
ALTER TABLE styles ADD COLUMN note_version TEXT NOT NULL DEFAULT '';
ALTER TABLE styles ADD COLUMN etat TEXT NOT NULL DEFAULT 'brouillon';
ALTER TABLE styles ADD COLUMN valide_le TEXT;
ALTER TABLE styles ADD COLUMN racine_id INTEGER REFERENCES styles(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS planche_images (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  style_id        INTEGER NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
  fichier         TEXT NOT NULL,
  objet_generique TEXT NOT NULL DEFAULT '',
  gardee          INTEGER NOT NULL DEFAULT 0,
  tache_id        INTEGER,
  credits         INTEGER NOT NULL DEFAULT 0,
  simule          INTEGER NOT NULL DEFAULT 0,
  remplacee       INTEGER NOT NULL DEFAULT 0,  -- « Refaire » : l'image a été remplacée (fichier effacé, crédits comptés)
  cree_le         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_planche_style ON planche_images(style_id, id);
