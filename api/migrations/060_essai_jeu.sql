-- 060 · Essai et Jeu : les deux dernières étapes d'un projet, après la validation de ses objets.
-- essai_fait : l'utilisateur a regardé ses objets ensemble et les a acceptés ; jeu_fait : il a récupéré le pack pour son jeu.
ALTER TABLE lots ADD COLUMN essai_fait INTEGER NOT NULL DEFAULT 0;
ALTER TABLE lots ADD COLUMN jeu_fait INTEGER NOT NULL DEFAULT 0;
