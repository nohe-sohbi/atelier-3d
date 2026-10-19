-- 030 · File de tâches et coûts (étape 4) : coûts typés, rattachés au lot et marqués « simulé » ;
-- battement du worker (l'écran sait s'il tourne).
ALTER TABLE couts ADD COLUMN type TEXT NOT NULL DEFAULT '';
ALTER TABLE couts ADD COLUMN lot_id INTEGER REFERENCES lots(id) ON DELETE SET NULL;
ALTER TABLE couts ADD COLUMN simule INTEGER NOT NULL DEFAULT 0;
-- Les lignes écrites avant cette migration portaient ces trois valeurs dans `detail` (JSON).
UPDATE couts SET type = COALESCE(json_extract(detail, '$.type'), ''),
                 lot_id = json_extract(detail, '$.lot_id'),
                 simule = CASE WHEN json_extract(detail, '$.simule') THEN 1 ELSE 0 END
 WHERE detail IS NOT NULL AND json_valid(detail);
CREATE INDEX IF NOT EXISTS idx_couts_lot ON couts(lot_id, service);

CREATE TABLE IF NOT EXISTS workers (
  verrou     TEXT PRIMARY KEY,
  hote       TEXT NOT NULL DEFAULT '',
  pid        INTEGER,
  demarre_le TEXT NOT NULL,
  battu_le   TEXT NOT NULL,
  arrete_le  TEXT
);
