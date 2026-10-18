"""Contrôles qualité automatiques d'un asset exporté (sans bpy : trimesh + numpy sur le GLB).

Les 12 contrôles du cahier des charges, dans l'ordre et avec les noms du tableau
« Contrôles qualité automatiques ». Chaque contrôle est un `Controle`
{nom, mesure, seuil, bloquant, ok, detail, etat}. Les seuils viennent du style, jamais d'ici.

S'y ajoute la liste blanche des licences : une source hors liste rend l'asset refusé.

Ce que trimesh ne sait pas mesurer peut être fourni par le script bpy dans
`<dossier>/rapport_interne.json` (tailles des textures, facteur d'échelle appliqué...).

Aucune dépendance optionnelle de trimesh (scipy, networkx, rtree) n'est requise :
composantes connexes, cohérence des normales et distance à la surface sont faites en numpy.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from pipeline.style import Style

LICENCES_AUTORISEES = ("CC0-1.0", "CC-BY-4.0", "Meshy-Pro", "ComfyUI-local")

NOMS_CONTROLES = (
    "Maillage fermé",
    "Pièces flottantes",
    "Normales",
    "Dimensions",
    "Polycount",
    "Symétrie",
    "UV",
    "Densité de texels",
    "Export",
    "Conformité du fichier",
    "Rendus",
    "Critique IA",
)
VUES = ("face", "dos", "profil", "trois_quarts", "dessus")
SUFFIXES_GLB = ("_LOD0", "_LOD1", "_LOD2", "_COL")
_EPS_UV = 1e-4          # tolérance numérique pour « hors du carré 0-1 »
_EPS_SAT = 1e-7         # tolérance numérique de la séparation de deux triangles UV
_ECHANTILLON_SYM = 2000  # sommets testés au plus pour la symétrie


# ---------------------------------------------------------------------------
# Résultats
# ---------------------------------------------------------------------------
@dataclass
class Controle:
    nom: str
    mesure: Any
    seuil: Any
    bloquant: bool
    ok: bool
    detail: str = ""
    etat: str = ""   # ok | echec | alerte | non exécuté | non demandée | disponible

    def __post_init__(self) -> None:
        if not self.etat:
            self.etat = "ok" if self.ok else ("echec" if self.bloquant else "alerte")

    def to_dict(self) -> dict[str, Any]:
        return {"nom": self.nom, "mesure": self.mesure, "seuil": self.seuil,
                "bloquant": self.bloquant, "ok": bool(self.ok), "detail": self.detail,
                "etat": self.etat}


@dataclass
class Rapport:
    id: str
    controles: list[Controle] = field(default_factory=list)
    licence: dict[str, Any] = field(default_factory=dict)
    style: str = ""
    dossier: str = ""
    date: str = field(default_factory=lambda: date.today().isoformat())
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def bloquants_ok(self) -> bool:
        return all(c.ok for c in self.controles if c.bloquant) and bool(self.licence.get("ok", False))

    @property
    def statut(self) -> str:
        return "accepte" if self.bloquants_ok else "refuse"

    @property
    def nb_ok(self) -> int:
        return sum(1 for c in self.controles if c.ok)

    def controle(self, nom: str) -> Controle:
        for c in self.controles:
            if c.nom == nom:
                return c
        raise KeyError(nom)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date,
            "style": self.style,
            "dossier": self.dossier,
            "statut": self.statut,
            "bloquants_ok": self.bloquants_ok,
            "nb_ok": self.nb_ok,
            "nb_controles": len(self.controles),
            "licence": self.licence,
            "controles": [c.to_dict() for c in self.controles],
            "extras": self.extras,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, default=str)

    def ecrire(self, chemin: str | Path) -> Path:
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(self.to_json() + "\n", encoding="utf-8")
        return chemin

    @classmethod
    def depuis_dict(cls, d: dict[str, Any]) -> "Rapport":
        r = cls(id=d.get("id", ""), style=d.get("style", ""), dossier=d.get("dossier", ""),
                date=d.get("date", ""), licence=dict(d.get("licence", {})),
                extras=dict(d.get("extras", {})))
        for c in d.get("controles", []):
            r.controles.append(Controle(nom=c["nom"], mesure=c.get("mesure"), seuil=c.get("seuil"),
                                        bloquant=bool(c.get("bloquant")), ok=bool(c.get("ok")),
                                        detail=c.get("detail", ""), etat=c.get("etat", "")))
        return r

    @classmethod
    def lire(cls, chemin: str | Path) -> "Rapport":
        return cls.depuis_dict(json.loads(Path(chemin).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Géométrie en numpy (sans scipy / networkx / rtree)
# ---------------------------------------------------------------------------
def nettoyer_topologie(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Copie fusionnée par position (les coutures UV / normales de l'export séparent les sommets)."""
    m = mesh.copy()
    m.merge_vertices(merge_tex=True, merge_norm=True)
    if len(m.faces):
        m.update_faces(m.nondegenerate_faces())
    if len(m.faces):
        m.update_faces(m.unique_faces())
    return m


def aretes_non_manifold(mesh: trimesh.Trimesh) -> tuple[int, int, int]:
    """(arêtes non-manifold, dont bords, dont arêtes partagées par > 2 faces)."""
    if not len(mesh.faces):
        return 0, 0, 0
    _, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    return int((counts != 2).sum()), int((counts == 1).sum()), int((counts > 2).sum())


def composantes_connexes(mesh: trimesh.Trimesh) -> int:
    """Nombre de morceaux reliés par des sommets partagés (union-find vectorisé)."""
    if not len(mesh.faces):
        return 0
    nv = len(mesh.vertices)
    edges = mesh.edges_unique
    labels = np.arange(nv)
    for _ in range(nv + 1):
        mn = np.minimum(labels[edges[:, 0]], labels[edges[:, 1]])
        new = labels.copy()
        np.minimum.at(new, edges[:, 0], mn)
        np.minimum.at(new, edges[:, 1], mn)
        new = new[new]  # saut de pointeur
        if np.array_equal(new, labels):
            break
        labels = new
    utilises = np.unique(mesh.faces)
    return int(len(np.unique(labels[utilises])))


def faces_inversees(mesh: trimesh.Trimesh) -> tuple[int, bool, float]:
    """(faces à retourner pour des normales cohérentes et vers l'extérieur, cohérent ?, volume signé).

    Parcours en largeur de l'adjacence des faces : deux faces voisines sont cohérentes si
    l'arête commune est parcourue dans des sens opposés. Par composante, l'orientation
    retenue est celle qui donne un volume positif (normales vers l'extérieur).
    """
    faces = mesh.faces
    nf = len(faces)
    if nf == 0:
        return 0, True, 0.0
    adj = mesh.face_adjacency
    adj_edges = mesh.face_adjacency_edges
    voisins: dict[int, list[tuple[int, bool]]] = defaultdict(list)
    for (f1, f2), (a, b) in zip(adj, adj_edges):
        # sens de l'arête (a,b) dans chaque face
        def avant(f: int) -> bool:
            v = faces[f]
            for i in range(3):
                if v[i] == a and v[(i + 1) % 3] == b:
                    return True
            return False
        coherent = avant(f1) != avant(f2)
        voisins[int(f1)].append((int(f2), coherent))
        voisins[int(f2)].append((int(f1), coherent))

    flip = np.zeros(nf, dtype=bool)
    vu = np.zeros(nf, dtype=bool)
    coherent_global = True
    total_inverses = 0
    volume_total = 0.0
    tri = mesh.triangles  # (nf, 3, 3)
    vol_faces = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])) / 6.0
    for depart in range(nf):
        if vu[depart]:
            continue
        comp = [depart]
        vu[depart] = True
        file = deque([depart])
        while file:
            f = file.popleft()
            for g, coherent in voisins.get(f, ()):
                attendu = flip[f] ^ (not coherent)
                if not vu[g]:
                    vu[g] = True
                    flip[g] = attendu
                    comp.append(g)
                    file.append(g)
                elif flip[g] != attendu:
                    coherent_global = False  # bande de Möbius : impossible à orienter
        comp = np.asarray(comp)
        signe = np.where(flip[comp], -1.0, 1.0)
        vol = float((vol_faces[comp] * signe).sum())
        if vol < 0:  # tout retourner : l'orientation « flip » est la bonne
            inverses = int((~flip[comp]).sum())
            vol = -vol
        else:
            inverses = int(flip[comp].sum())
        total_inverses += inverses
        volume_total += vol
    return total_inverses, coherent_global, volume_total


def distance_surface(mesh: trimesh.Trimesh, points: np.ndarray, k: int = 8) -> np.ndarray:
    """Distance de chaque point à la surface : k triangles aux centroïdes les plus proches,
    puis point le plus proche exact sur ces triangles (trimesh.triangles.closest_point)."""
    tris = mesh.triangles
    if len(tris) == 0 or len(points) == 0:
        return np.zeros(len(points))
    centres = tris.mean(axis=1)
    k = min(k, len(tris))
    resultat = np.empty(len(points))
    lot = 512
    for i in range(0, len(points), lot):
        p = points[i:i + lot]
        d2 = ((p[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        idx = np.argpartition(d2, k - 1, axis=1)[:, :k]  # (n, k)
        cand = tris[idx.reshape(-1)]                        # (n*k, 3, 3)
        pts = np.repeat(p, k, axis=0)
        proches = trimesh.triangles.closest_point(cand, pts)
        d = np.linalg.norm(proches - pts, axis=1).reshape(len(p), k)
        resultat[i:i + lot] = d.min(axis=1)
    return resultat


def chevauchements_uv(faces_uv: np.ndarray, cellules: int = 64) -> tuple[int, int]:
    """(paires de triangles UV qui se chevauchent, triangles UV concernés).

    Les triangles empilés exactement (miroir volontaire) ne comptent pas : un seul
    exemplaire de chaque triangle identique est gardé. Les triangles simplement voisins
    (arête commune) ne comptent pas non plus : séparation par axes avec tolérance.
    """
    if len(faces_uv) == 0:
        return 0, 0
    t = np.asarray(faces_uv, dtype=float)
    # retirer les triangles dégénérés
    aires = 0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
                         - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1]))
    t = t[aires > 1e-12]
    if len(t) < 2:
        return 0, 0
    # dédoublonner les triangles identiques (miroirs empilés)
    cle = np.round(t, 5)
    ordre = np.lexsort((cle[:, :, 1], cle[:, :, 0]), axis=1)  # sommets de chaque triangle triés par (x, y)
    cle_triee = np.take_along_axis(cle, ordre[:, :, None], axis=1).reshape(len(t), -1)
    _, premiers = np.unique(cle_triee, axis=0, return_index=True)
    t = t[np.sort(premiers)]
    n = len(t)
    if n < 2:
        return 0, 0
    # candidats par grille
    mins = t.min(axis=1)
    maxs = t.max(axis=1)
    lo = np.floor(np.clip(mins, -1, 2) * cellules).astype(int)
    hi = np.floor(np.clip(maxs, -1, 2) * cellules).astype(int)
    grille: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i in range(n):
        for cx in range(lo[i, 0], hi[i, 0] + 1):
            for cy in range(lo[i, 1], hi[i, 1] + 1):
                grille[(cx, cy)].append(i)
    paires: set[tuple[int, int]] = set()
    for membres in grille.values():
        if len(membres) < 2:
            continue
        for a in range(len(membres)):
            for b in range(a + 1, len(membres)):
                i, j = membres[a], membres[b]
                paires.add((i, j) if i < j else (j, i))
    if not paires:
        return 0, 0
    P = np.array(sorted(paires))
    # filtre AABB
    garde = np.all(mins[P[:, 0]] <= maxs[P[:, 1]] + _EPS_SAT, axis=1) & \
        np.all(mins[P[:, 1]] <= maxs[P[:, 0]] + _EPS_SAT, axis=1)
    P = P[garde]
    if len(P) == 0:
        return 0, 0
    A = t[P[:, 0]]  # (m, 3, 2)
    B = t[P[:, 1]]
    separes = np.zeros(len(P), dtype=bool)
    for T in (A, B):
        for i in range(3):
            e = T[:, (i + 1) % 3] - T[:, i]
            axe = np.stack([-e[:, 1], e[:, 0]], axis=1)
            norme = np.linalg.norm(axe, axis=1, keepdims=True)
            axe = axe / np.where(norme == 0, 1, norme)
            pa = np.einsum("mij,mj->mi", A, axe)
            pb = np.einsum("mij,mj->mi", B, axe)
            sep = (pb.min(axis=1) >= pa.max(axis=1) - _EPS_SAT) | (pa.min(axis=1) >= pb.max(axis=1) - _EPS_SAT)
            separes |= sep
    chev = P[~separes]
    return int(len(chev)), int(len(np.unique(chev)))


# ---------------------------------------------------------------------------
# Lecture du GLB
# ---------------------------------------------------------------------------
def charger_maillages(glb: str | Path) -> dict[str, trimesh.Trimesh]:
    """Nœud glTF -> maillage dans le repère de la scène (transformations appliquées)."""
    scene = trimesh.load(str(glb), force="scene", process=False)
    maillages: dict[str, trimesh.Trimesh] = {}
    for noeud in scene.graph.nodes_geometry:
        transform, nom_geom = scene.graph[noeud]
        geom = scene.geometry.get(nom_geom)
        if geom is None or not isinstance(geom, trimesh.Trimesh):
            continue
        m = geom.copy()
        m.apply_transform(transform)
        maillages[str(noeud)] = m
    return maillages


def maillage_par_suffixe(maillages: dict[str, trimesh.Trimesh], suffixe: str) -> trimesh.Trimesh | None:
    for nom, m in maillages.items():
        if nom.endswith(suffixe):
            return m
    return None


def _lire_json(chemin: Path) -> dict[str, Any]:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _pct(a: float, b: float) -> float:
    return abs(a - b) / b * 100.0 if b else float("inf")


# ---------------------------------------------------------------------------
# Les 12 contrôles
# ---------------------------------------------------------------------------
def valider(dossier_asset: str | Path, style: Style, infos: dict[str, Any] | None = None,
            config: dict[str, Any] | None = None) -> Rapport:
    """Passe les 12 contrôles sur le dossier d'un asset exporté.

    `infos` : id, categorie, dimensions_type (ou type), dimensions_m (facultatif, prime sur le
    style), symetrique ("X" | "Y" | None), pieces_declarees, licence, sources. Les valeurs
    absentes sont lues dans <dossier>/meta.json.
    """
    dossier = Path(dossier_asset)
    infos = dict(infos or {})
    meta = _lire_json(dossier / "meta.json")
    interne = _lire_json(dossier / "rapport_interne.json")
    tol = style.tolerances

    def info(cle: str, defaut: Any = None) -> Any:
        if infos.get(cle) is not None:
            return infos[cle]
        if meta.get(cle) is not None:
            return meta[cle]
        return interne.get(cle, defaut)

    id_asset = str(info("id") or dossier.name)
    categorie = info("categorie")
    type_objet = info("dimensions_type") or info("type") or interne.get("dimensions_type")
    symetrique = info("symetrique")
    pieces = info("pieces_declarees", 1)
    pieces = int(pieces) if pieces is not None else 1

    rapport = Rapport(id=id_asset, style=f"{style.nom}@{style.version}", dossier=str(dossier))
    glb = dossier / f"{id_asset}.glb"
    fbx = dossier / f"{id_asset}.fbx"

    maillages: dict[str, trimesh.Trimesh] = {}
    erreur_glb = ""
    if glb.is_file():
        try:
            maillages = charger_maillages(glb)
        except Exception as e:  # noqa: BLE001 - on rapporte l'erreur, on ne plante pas
            erreur_glb = f"{type(e).__name__}: {e}"
    else:
        erreur_glb = f"GLB absent : {glb.name}"
    lod0 = maillage_par_suffixe(maillages, "_LOD0")
    if lod0 is None and maillages:
        lod0 = next(iter(maillages.values()))
    topo = nettoyer_topologie(lod0) if lod0 is not None else None

    def sans_maillage(nom: str, seuil: Any, bloquant: bool = True) -> Controle:
        return Controle(nom, None, seuil, bloquant, False, erreur_glb or "aucun maillage LOD0 dans le GLB")

    # 1. Maillage fermé
    if topo is None:
        rapport.controles.append(sans_maillage("Maillage fermé", 0))
    else:
        nm, bords, multi = aretes_non_manifold(topo)
        rapport.controles.append(Controle(
            "Maillage fermé", nm, 0, True, nm == 0,
            f"{nm} arêtes non-manifold ({bords} de bord, {multi} partagées par plus de 2 faces) "
            f"sur {len(topo.edges_unique)}"))

    # 2. Pièces flottantes
    if topo is None:
        rapport.controles.append(sans_maillage("Pièces flottantes", 0))
    else:
        nc = composantes_connexes(topo)
        ecart = nc - pieces
        rapport.controles.append(Controle(
            "Pièces flottantes", ecart, 0, True, ecart == 0,
            f"{nc} morceaux reliés pour {pieces} déclaré(s)"))

    # 3. Normales
    if topo is None:
        rapport.controles.append(sans_maillage("Normales", 0))
    else:
        inv, coherent, vol = faces_inversees(topo)
        ok = inv == 0 and coherent and vol > 0
        rapport.controles.append(Controle(
            "Normales", inv, 0, True, ok,
            f"{inv} faces inversées ; orientation {'cohérente' if coherent else 'incohérente'} ; "
            f"volume {vol:.4f} m³"))

    # 4. Dimensions
    attendu = info("dimensions_m") if infos.get("dimensions_m") else None
    if attendu is None and type_objet:
        attendu = style.dimensions(str(type_objet))
    if lod0 is None:
        rapport.controles.append(sans_maillage("Dimensions", f"±{tol['dimensions_pct']} %"))
    elif not attendu:
        rapport.controles.append(Controle(
            "Dimensions", None, f"±{tol['dimensions_pct']} %", True, False,
            f"type d'objet {type_objet!r} absent de dimensions_m du style et aucune dimension fournie"))
    else:
        ext = [float(x) for x in lod0.extents]
        ecarts = [_pct(m, a) for m, a in zip(ext, attendu)]
        pire = max(ecarts)
        rapport.controles.append(Controle(
            "Dimensions", round(pire, 2), tol["dimensions_pct"], True, pire <= tol["dimensions_pct"],
            f"mesuré [{ext[0]:.3f}, {ext[1]:.3f}, {ext[2]:.3f}] m, attendu {list(attendu)} m "
            f"(écarts X/Y/Z : {ecarts[0]:.1f} / {ecarts[1]:.1f} / {ecarts[2]:.1f} %)"))
        rapport.extras["dimensions_m"] = [round(x, 4) for x in ext]

    # 5. Polycount (+ ratios LOD)
    budget = None
    try:
        budget = style.budget(str(categorie)) if categorie else None
    except Exception:  # noqa: BLE001
        budget = None
    if lod0 is None:
        rapport.controles.append(sans_maillage("Polycount", budget))
    elif budget is None:
        rapport.controles.append(Controle("Polycount", int(len(lod0.faces)), None, True, False,
                                          f"catégorie {categorie!r} sans budget dans le style"))
    else:
        t0 = int(len(lod0.faces))
        ok = t0 <= budget
        details = [f"LOD0 {t0} tris pour un budget de {budget}"]
        ratios = style.lod_ratios
        tris = {"tris_lod0": t0}
        for i, suffixe in ((1, "_LOD1"), (2, "_LOD2")):
            m = maillage_par_suffixe(maillages, suffixe)
            if m is None:
                ok = False
                details.append(f"LOD{i} absent")
                continue
            ti = int(len(m.faces))
            tris[f"tris_lod{i}"] = ti
            part = ti / t0 * 100 if t0 else 0.0
            cible = ratios[i] * 100
            dans_tol = abs(part - cible) <= tol["lod_pct"]
            ok = ok and dans_tol
            details.append(f"LOD{i} {ti} tris = {part:.0f} % (cible {cible:.0f} ± {tol['lod_pct']:.0f} %)"
                           + ("" if dans_tol else " HORS TOLÉRANCE"))
        col = maillage_par_suffixe(maillages, "_COL")
        if col is not None:
            tris["tris_col"] = int(len(col.faces))
            details.append(f"collision {len(col.faces)} tris")
        rapport.extras.update(tris)
        rapport.controles.append(Controle("Polycount", t0, budget, True, ok, " ; ".join(details)))

    # 6. Symétrie
    if symetrique in ("X", "Y"):
        if topo is None:
            rapport.controles.append(sans_maillage("Symétrie", tol["symetrie_m"]))
        else:
            axe = 0 if symetrique == "X" else 1
            centre = topo.bounds.mean(axis=0)
            pts = topo.vertices
            if len(pts) > _ECHANTILLON_SYM:
                idx = np.random.default_rng(0).choice(len(pts), _ECHANTILLON_SYM, replace=False)
                pts = pts[np.sort(idx)]
            miroir = pts.copy()
            miroir[:, axe] = 2 * centre[axe] - miroir[:, axe]
            d = distance_surface(topo, miroir)
            pire = float(d.max()) if len(d) else 0.0
            rapport.controles.append(Controle(
                "Symétrie", round(pire, 5), tol["symetrie_m"], True, pire <= tol["symetrie_m"],
                f"miroir sur l'axe {symetrique} : écart max {pire * 1000:.2f} mm, "
                f"moyen {float(d.mean()) * 1000 if len(d) else 0:.2f} mm sur {len(pts)} sommets"))
    else:
        rapport.controles.append(Controle("Symétrie", 0, tol["symetrie_m"], True, True,
                                          "objet non déclaré symétrique", etat="non demandée"))

    # 7. UV
    uv = None
    if lod0 is not None and hasattr(lod0.visual, "uv") and lod0.visual.uv is not None \
            and len(lod0.visual.uv) == len(lod0.vertices):
        uv = np.asarray(lod0.visual.uv, dtype=float)
    if lod0 is None:
        rapport.controles.append(sans_maillage("UV", 0))
    elif uv is None:
        rapport.controles.append(Controle("UV", None, 0, True, False, "aucune coordonnée UV dans le LOD0"))
    else:
        hors = int(((uv < -_EPS_UV) | (uv > 1 + _EPS_UV)).any(axis=1).sum())
        faces_uv = uv[lod0.faces]
        paires, concernes = chevauchements_uv(faces_uv)
        mesure = paires + hors
        rapport.controles.append(Controle(
            "UV", mesure, 0, True, mesure == 0,
            f"{paires} paires de triangles qui se chevauchent ({concernes} triangles), "
            f"{hors} sommets hors du carré 0-1 (miroirs empilés ignorés)"))

    # 8. Densité de texels (non bloquant)
    taille_tex = None
    textures = interne.get("textures") or meta.get("textures") or {}
    if isinstance(textures, dict):
        for v in textures.values():
            if isinstance(v, dict) and v.get("px"):
                taille_tex = int(v["px"])
                break
    if taille_tex is None and lod0 is not None:
        mat = getattr(lod0.visual, "material", None)
        img = getattr(mat, "baseColorTexture", None)
        if img is not None and hasattr(img, "size"):
            taille_tex = int(img.size[0])
    if taille_tex is None:
        for p in sorted((dossier / "textures").glob("*.png")) if (dossier / "textures").is_dir() else []:
            try:
                from PIL import Image
                with Image.open(p) as im:
                    taille_tex = int(im.size[0])
                break
            except Exception:  # noqa: BLE001
                continue
    if lod0 is None or uv is None or taille_tex is None or lod0.area <= 0:
        rapport.controles.append(Controle(
            "Densité de texels", None, f"{style.texel_density:.0f} px/m ± {tol['texel_pct']:.0f} %",
            False, False, "non mesurable : il faut un LOD0 avec UV et une texture", etat="non exécuté"))
    else:
        f = uv[lod0.faces]
        aire_uv = float((0.5 * np.abs((f[:, 1, 0] - f[:, 0, 0]) * (f[:, 2, 1] - f[:, 0, 1])
                                      - (f[:, 2, 0] - f[:, 0, 0]) * (f[:, 1, 1] - f[:, 0, 1]))).sum())
        densite = float(np.sqrt(aire_uv * taille_tex * taille_tex / lod0.area))
        ecart = _pct(densite, style.texel_density)
        rapport.controles.append(Controle(
            "Densité de texels", round(densite, 1), f"{style.texel_density:.0f} px/m ± {tol['texel_pct']:.0f} %",
            False, ecart <= tol["texel_pct"],
            f"{densite:.0f} px/m (texture {taille_tex} px, {aire_uv * 100:.1f} % du carré UV, "
            f"{lod0.area:.3f} m²) : écart {ecart:.1f} %"))
        rapport.extras["texel_density"] = round(densite, 1)

    # 9. Export
    details = []
    ok = True
    if erreur_glb:
        ok = False
        details.append(erreur_glb)
    else:
        manquants = [s for s in SUFFIXES_GLB if maillage_par_suffixe(maillages, s) is None]
        if manquants:
            ok = False
            details.append("objets manquants dans le GLB : " + ", ".join(manquants))
        else:
            details.append(f"GLB relu : {len(maillages)} objets ({', '.join(sorted(maillages))})")
    if fbx.is_file() and fbx.stat().st_size > 0:
        tete = fbx.read_bytes()[:32]
        if tete.startswith(b"Kaydara FBX Binary") or tete.lstrip().startswith(b";"):
            details.append(f"FBX présent ({fbx.stat().st_size} octets)")
        else:
            ok = False
            details.append("FBX présent mais sans en-tête FBX reconnu")
    else:
        ok = False
        details.append("FBX absent ou vide")
    rapport.controles.append(Controle("Export", "ok" if ok else "erreur", "OK", True, ok, " ; ".join(details)))

    # 10. Conformité du fichier (glTF-Validator)
    rapport.controles.append(_conformite_gltf(glb, config))

    # 11. Rendus
    rendus = dossier / "rendus"
    presentes = [v for v in VUES if (rendus / f"{v}.png").is_file() and (rendus / f"{v}.png").stat().st_size > 0]
    planche = (rendus / "planche.png").is_file() and (rendus / "planche.png").stat().st_size > 0
    vignette = (rendus / "vignette.png").is_file()
    ok = len(presentes) == len(VUES) and planche
    rapport.controles.append(Controle(
        "Rendus", f"{len(presentes)}/{len(VUES)} vues, planche {'oui' if planche else 'non'}", "OK", True, ok,
        f"vues présentes : {', '.join(presentes) or 'aucune'} ; planche de contact "
        f"{'présente' if planche else 'absente'} ; vignette {'présente' if vignette else 'absente'}"))

    # 12. Critique IA (indicatif)
    avis = _lire_json(dossier / "avis_ia.json")
    if avis:
        rapport.controles.append(Controle("Critique IA", "avis disponible", "Aucun", False, True,
                                          str(avis.get("avis") or avis.get("texte") or avis), etat="disponible"))
    else:
        rapport.controles.append(Controle("Critique IA", "non demandée", "Aucun", False, True,
                                          "aucun avis de modèle de vision pour l'instant (indicatif, jamais bloquant)",
                                          etat="non demandée"))

    # Licences : liste blanche
    rapport.licence = verifier_licences(info("licence"), info("sources") or [])
    if interne:
        rapport.extras["rapport_interne"] = {k: v for k, v in interne.items() if k != "textures"}
    return rapport


def verifier_licences(licence: Any, sources: list[Any]) -> dict[str, Any]:
    """L'asset et chacune de ses sources doivent porter une licence de la liste blanche."""
    refus: list[str] = []
    if not licence:
        refus.append("licence de l'asset absente")
    elif licence not in LICENCES_AUTORISEES:
        refus.append(f"licence de l'asset hors liste blanche : {licence}")
    lic_sources: list[str] = []
    for s in sources or []:
        if isinstance(s, dict):
            lic = s.get("licence")
            nom = s.get("nom") or s.get("url") or s.get("outil") or "source"
        else:
            lic, nom = None, str(s)
        lic_sources.append(str(lic))
        if not lic:
            refus.append(f"source sans licence : {nom}")
        elif lic not in LICENCES_AUTORISEES:
            refus.append(f"source {nom} sous licence hors liste blanche : {lic}")
    return {
        "ok": not refus,
        "licence": licence,
        "sources": lic_sources,
        "autorisees": list(LICENCES_AUTORISEES),
        "detail": "licences conformes" if not refus else " ; ".join(refus),
    }


def _conformite_gltf(glb: Path, config: dict[str, Any] | None) -> Controle:
    nom = "Conformité du fichier"
    chemin = ((config or {}).get("gltf_validator") or {}).get("chemin") or ""
    executable = shutil.which(chemin) if chemin else None
    if not executable and chemin and Path(chemin).is_file():
        executable = chemin
    if not executable:
        return Controle(nom, "non exécuté", "0 erreur", False, False,
                        "glTF-Validator introuvable (gltf_validator.chemin dans config.local.yaml) : "
                        "contrôle non exécuté, à lancer sur une machine qui l'a", etat="non exécuté")
    if not glb.is_file():
        return Controle(nom, "non exécuté", "0 erreur", True, False, "GLB absent", etat="echec")
    rapport_json = glb.with_name(glb.name + ".report.json")
    try:
        r = subprocess.run([executable, "-o", str(glb)], capture_output=True, text=True,
                           timeout=120, cwd=str(glb.parent))
    except (OSError, subprocess.SubprocessError) as e:
        return Controle(nom, "non exécuté", "0 erreur", False, False,
                        f"glTF-Validator n'a pas pu être lancé : {e}", etat="non exécuté")
    donnees = _lire_json(rapport_json)
    issues = donnees.get("issues") or {}
    if not donnees:
        return Controle(nom, "non exécuté", "0 erreur", False, False,
                        f"glTF-Validator lancé (code {r.returncode}) mais aucun rapport lisible : "
                        f"{(r.stderr or r.stdout)[-300:]}", etat="non exécuté")
    erreurs = int(issues.get("numErrors", 0))
    avert = int(issues.get("numWarnings", 0))
    messages = [m.get("message", "") for m in issues.get("messages", []) if m.get("severity") == 0][:5]
    return Controle(nom, erreurs, 0, True, erreurs == 0,
                    f"{erreurs} erreurs, {avert} avertissements (glTF-Validator)"
                    + (" : " + " | ".join(messages) if messages else ""))
