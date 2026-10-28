"""Projets de démonstration : des objets fabriqués à tous les stades, avec de vrais fichiers 3D.

Sert aux tests (serveur et bout en bout, sans Blender) et à l'essai à la main sur le téléphone de Nohé :

    python -m tests.outils.projet_demo                      # dans la base de développement
    python -m tests.outils.projet_demo --db X --lots Y      # dans une base et un dossier précis (tests e2e)

Les fichiers 3D viennent de `docs/maquette/modeles/` (Git LFS). Ils sont recomposés en un seul .glb avec les nœuds
`_LOD0`, `_LOD1`, `_LOD2` et `_COL`, comme ceux de la vraie chaîne.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

from api import chemins, db
from api.services import lots as lots_svc
from pipeline import validate

MAQUETTE = chemins.racine() / "docs" / "maquette"


def glb_avec_niveaux(nom: str, modele: str, destination) -> None:
    """Un .glb à quatre nœuds (trois niveaux de détail et une collision) à partir des trois fichiers de la maquette."""
    import trimesh

    scene = trimesh.Scene()
    for i in range(3):
        for g in trimesh.load(str(MAQUETTE / "modeles" / f"{modele}-lod{i}.glb"), force="scene").geometry.values():
            scene.add_geometry(g.copy(), node_name=f"{nom}_LOD{i}", geom_name=f"{nom}_LOD{i}")
    boite = trimesh.creation.box(extents=(0.5, 0.5, 0.95))  # collision : plus grande, elle ne doit jamais s'afficher
    boite.apply_translation((0, 0.45, 0))
    scene.add_geometry(boite, node_name=f"{nom}_COL", geom_name=f"{nom}_COL")
    destination.write_bytes(trimesh.exchange.gltf.export_glb(scene))


def _objet_pret(conn, lot_id: int, nom: str, modele: str, id_asset: str, controles: list, tris: tuple, dimensions: list) -> int:
    conn.execute("INSERT INTO objets(lot_id, nom, type_objet, etape, voie, generateur) VALUES (?, ?, ?, 'revue', 'ia', 'meshy')",
                 (lot_id, nom, nom.lower()))
    oid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    dossier = f"{lot_id}/{oid}/essai-1"
    asset = chemins.dossier_lots() / dossier / "asset"
    (asset / "rendus").mkdir(parents=True, exist_ok=True)
    glb_avec_niveaux(id_asset, modele, asset / f"{id_asset}.glb")
    for vue in (*validate.VUES, "planche"):
        shutil.copy(MAQUETTE / "img" / f"vue-amphore-{'trois_quarts' if vue == 'planche' else vue}.png", asset / "rendus" / f"{vue}.png")
    validate.Rapport(id=id_asset, controles=controles, licence={"ok": True}).ecrire(asset / "rapport.json")
    (asset / "meta.json").write_text(json.dumps({"dimensions_m": dimensions, "tris_lod0": tris[0], "tris_lod1": tris[1],
                                                  "tris_lod2": tris[2]}), encoding="utf-8")
    references = chemins.dossier_lots() / str(lot_id) / str(oid) / "references"
    references.mkdir(parents=True, exist_ok=True)
    shutil.copy(MAQUETTE / "img" / f"look-{modele}-1.png", references / "look.png")
    conn.execute("INSERT INTO propositions(objet_id, serie, rang, genre, fichier, cree_le) VALUES (?, 1, 0, 'image', 'look.png', ?)",
                 (oid, db.maintenant()))
    conn.execute("UPDATE objets SET reference_id = last_insert_rowid() WHERE id = ?", (oid,))
    conn.execute("INSERT INTO essais(objet_id, numero, generateur, etat, dossier, cout_credits) VALUES (?, 1, 'meshy', 'pret', ?, 42)",
                 (oid, dossier))
    conn.execute("INSERT INTO assets(id, lot_id, objet_id, nom, theme, voie, statut, cree_le, maj_le) VALUES (?, ?, ?, ?, 'ROM', 'ia', 'revue', ?, ?)",
                 (id_asset, lot_id, oid, nom, db.maintenant(), db.maintenant()))
    conn.commit()
    return oid


def semer_validation(conn, nom: str = "Port de pêche (démo validation)") -> dict:
    """Un projet avec deux objets prêts à valider (une amphore nette, une caisse « à regarder ») et une lanterne en fabrication."""
    lot = lots_svc.creer(conn, nom=nom, besoin="Des amphores, des caisses et une lanterne pour un petit port de pêche.")
    lid = lot["id"]
    net = [validate.Controle(n, None, None, True, True) for n in validate.NOMS_CONTROLES[:8]]
    a_regarder = [validate.Controle("Maillage fermé", None, None, True, True),
                  validate.Controle("Normales", None, None, False, False, "12 faces inversées"),
                  validate.Controle("Polycount", None, None, True, True),
                  validate.Controle("Densité de texels", None, None, False, False, "netteté inégale")]
    amphore = _objet_pret(conn, lid, "Amphore", "amphore", f"ROM_PROP_Amphore_D{lid}", net, (3816, 1908, 954), [0.35, 0.35, 0.9])
    caisse = _objet_pret(conn, lid, "Caisse ferrée", "caisse", f"ROM_PROP_Caisse_D{lid}", a_regarder, (404, 202, 100), [0.6, 0.4, 0.4])
    conn.execute("INSERT INTO objets(lot_id, nom, type_objet, etape, voie, generateur) VALUES (?, 'Lanterne', 'lanterne', 'generation', 'ia', 'meshy')",
                 (lid,))
    lanterne = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.commit()
    lots_svc.synchroniser_etat(conn, lid)
    return {"lot_id": lid, "amphore": amphore, "caisse": caisse, "lanterne": lanterne}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--db", help="base SQLite (défaut : celle de l'app)")
    p.add_argument("--lots", help="dossier des projets (défaut : celui de l'app)")
    p.add_argument("--nom", default="Port de pêche (démo validation)")
    a = p.parse_args(argv)
    if a.db:
        os.environ["ATELIER_DB"] = a.db
    if a.lots:
        os.environ["ATELIER_LOTS"] = a.lots
    conn = db.connexion()
    try:
        print(json.dumps(semer_validation(conn, a.nom)))
    finally:
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1:])
