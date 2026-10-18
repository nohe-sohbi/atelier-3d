"""Cadre commun des générateurs code.

Tout ce qui touche à Blender passe par ici : matériaux du style, briques de construction
(révolution, extrusion, boîte, cylindre, tore, arc, loft), jonction, nettoyage, pivot, UV,
mesures. Le module s'importe SANS bpy (le registre lit les manifestes depuis l'API) ; seules
les fonctions qui construisent de la géométrie exigent bpy et lèvent BlenderAbsent sinon.

Conventions : 1 unité = 1 m ; haut = +Z ; face avant = -Y. Les couleurs, matériaux, budgets,
dimensions et tolérances viennent du style (pipeline/style.py), jamais d'ici.
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable, Iterable, Sequence

try:  # bpy n'existe que dans Blender ou dans .venv-bpy
    import bmesh
    import bpy
    from mathutils import Matrix, Vector
    from mathutils.kdtree import KDTree
except ImportError:  # pragma: no cover - chemin API / worker
    bpy = None
    bmesh = None
    Matrix = Vector = KDTree = None

from pipeline.style import Style

ModeFamille = {"armes": "poignee", "outils": "poignee"}


class ParametresInvalides(ValueError):
    """Un paramètre ne respecte pas le schéma du MANIFESTE."""


class BlenderAbsent(RuntimeError):
    """bpy n'est pas importable : lancer avec Blender ou .venv-bpy."""


def exiger_bpy() -> None:
    if bpy is None:
        raise BlenderAbsent("bpy est requis pour construire de la géométrie")


# ---------------------------------------------------------------------------
# Paramètres et aléa
# ---------------------------------------------------------------------------
_AXES = {"x": 0, "y": 1, "z": 2}


def lire_params(manifeste: dict[str, Any], params: dict[str, Any] | None,
                style: Style | None = None) -> dict[str, Any]:
    """Applique les défauts, borne min/max, vérifie les choix.

    Un paramètre peut porter `style_dim: "x"|"y"|"z"` : s'il n'est pas fourni et qu'un style
    est donné, sa valeur vient de style.dimensions(manifeste["dimensions_type"]) plutôt que du
    défaut du manifeste. Les clés hors schéma (id, variante...) sont recopiées telles quelles.
    Lève ParametresInvalides pour un choix inconnu ou une valeur du mauvais type.
    """
    params = dict(params or {})
    resultat: dict[str, Any] = {}
    dims = None
    if style is not None:
        dims = style.dimensions(manifeste.get("dimensions_type", ""))
    for nom, schema in manifeste["parametres"].items():
        typ = schema["type"]
        fourni = nom in params and params[nom] is not None
        if fourni:
            valeur = params[nom]
        elif dims and schema.get("style_dim") in _AXES:
            valeur = dims[_AXES[schema["style_dim"]]]
        else:
            valeur = schema["defaut"]
        if typ == "choix":
            if valeur not in schema["choix"]:
                raise ParametresInvalides(
                    f"{nom} : {valeur!r} n'est pas dans {list(schema['choix'])}")
        elif typ == "bool":
            if isinstance(valeur, str):
                valeur = valeur.strip().lower() in ("1", "true", "vrai", "oui", "on")
            valeur = bool(valeur)
        elif typ in ("float", "int"):
            try:
                valeur = float(valeur) if typ == "float" else int(round(float(valeur)))
            except (TypeError, ValueError) as e:
                raise ParametresInvalides(f"{nom} : nombre attendu, reçu {valeur!r}") from e
            if schema.get("min") is not None:
                valeur = max(schema["min"], valeur)
            if schema.get("max") is not None:
                valeur = min(schema["max"], valeur)
            if typ == "int":
                valeur = int(valeur)
        else:
            raise ParametresInvalides(f"{nom} : type de paramètre inconnu {typ!r}")
        resultat[nom] = valeur
    for cle, valeur in params.items():
        if cle not in resultat:
            resultat[cle] = valeur
    return resultat


def rng(seed: int) -> random.Random:
    """Générateur pseudo-aléatoire isolé : même seed = mêmes tirages, jamais `random` global."""
    return random.Random(int(seed))


# ---------------------------------------------------------------------------
# Matériaux
# ---------------------------------------------------------------------------
def materiau(style: Style, nom: str):
    """Matériau Principled BSDF nommé d'après le matériau du style, réutilisé s'il existe."""
    exiger_bpy()
    m = style.materiau(nom)
    mat = bpy.data.materials.get(nom)
    if mat is None:
        mat = bpy.data.materials.new(nom)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        sortie = mat.node_tree.nodes.get("Material Output") or mat.node_tree.nodes.new(
            "ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], sortie.inputs["Surface"])
    rgba = (*m["rgb"], 1.0)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = float(m["roughness"])
    bsdf.inputs["Metallic"].default_value = float(m["metallic"])
    mat.diffuse_color = rgba
    mat.roughness = float(m["roughness"])
    mat.metallic = float(m["metallic"])
    mat["style_materiau"] = nom
    mat["style_base"] = m["base"]
    return mat


def slot_materiau(obj, mat) -> int:
    """Index du slot de ce matériau sur l'objet, ajouté s'il manque."""
    for i, existant in enumerate(obj.data.materials):
        if existant == mat:
            return i
    obj.data.materials.append(mat)
    return len(obj.data.materials) - 1


def assigner_materiaux(obj, style: Style,
                       choix: Callable[["Vector", "Vector"], str | None]) -> None:
    """Pour chaque face, `choix(centre, normale)` renvoie un nom de matériau du style (ou None
    pour laisser la face telle quelle). Les slots sont créés à la demande."""
    exiger_bpy()
    me = obj.data
    cache: dict[str, int] = {}
    for poly in me.polygons:
        nom = choix(Vector(poly.center), Vector(poly.normal))
        if nom is None:
            continue
        if nom not in cache:
            cache[nom] = slot_materiau(obj, materiau(style, nom))
        poly.material_index = cache[nom]


# ---------------------------------------------------------------------------
# Objets et bmesh
# ---------------------------------------------------------------------------
def objet_depuis_bmesh(bm, nom: str, materiaux: Sequence[Any] = (), lisser: bool = False):
    """Crée un objet maillage dans la scène courante à partir d'un bmesh (qui est libéré)."""
    exiger_bpy()
    if lisser:
        for f in bm.faces:
            f.smooth = True
    me = bpy.data.meshes.new(nom)
    bm.to_mesh(me)
    bm.free()
    me.update()
    obj = bpy.data.objects.new(nom, me)
    bpy.context.scene.collection.objects.link(obj)
    for mat in materiaux:
        if mat is not None:
            me.materials.append(mat)
    return obj


def bmesh_depuis_objet(obj):
    """bmesh indépendant, copie du maillage de l'objet (à libérer par l'appelant)."""
    exiger_bpy()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


def ecrire_bmesh(obj, bm) -> None:
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def supprimer(obj) -> None:
    exiger_bpy()
    me = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def transformer(obj, matrice) -> None:
    """Applique une matrice au maillage lui-même (l'objet garde une transformation identité)."""
    obj.data.transform(matrice)
    obj.data.update()


def deplacer(obj, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> None:
    transformer(obj, Matrix.Translation((dx, dy, dz)))


def tourner(obj, axe: str, degres: float) -> None:
    transformer(obj, Matrix.Rotation(math.radians(degres), 4, axe.upper()))


# ---------------------------------------------------------------------------
# Sections et briques
# ---------------------------------------------------------------------------
def section_polaire(forme: str, n: int, a: float, b: float | None = None, z: float = 0.0,
                    rotation_deg: float = 0.0, centre=(0.0, 0.0)) -> list[tuple[float, float, float]]:
    """Anneau de n points sur le contour d'une forme convexe, échantillonné par angle.

    forme : "cercle" (ellipse a, b), "rect" (demi-côtés a, b), "losange" (demi-diagonales a, b),
    "octogone" (rayon a, b). Les anneaux de même n s'enchaînent en loft, quelle que soit la forme.
    Le premier point est à l'angle 0 (+X) : avec n pair, l'anneau est symétrique en X et en Y.
    """
    b = a if b is None else b
    pts = []
    rot = math.radians(rotation_deg)
    for k in range(n):
        t = 2.0 * math.pi * k / n
        c, s = math.cos(t), math.sin(t)
        if forme == "cercle":
            r = 1.0 / math.sqrt((c / a) ** 2 + (s / b) ** 2)
        elif forme == "rect":
            r = min(a / abs(c) if abs(c) > 1e-12 else math.inf,
                    b / abs(s) if abs(s) > 1e-12 else math.inf)
        elif forme == "losange":
            r = 1.0 / (abs(c) / a + abs(s) / b)
        elif forme == "octogone":
            k8 = math.sqrt(2.0) - 1.0
            r = 1.0 / max(abs(c) / a, abs(s) / b, (abs(c) / a + abs(s) / b) / (1.0 + k8))
        else:
            raise ValueError(f"forme de section inconnue : {forme}")
        x, y = r * c, r * s
        if rot:
            x, y = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
        pts.append((centre[0] + x, centre[1] + y, z))
    return pts


def loft(anneaux: Sequence[Sequence[tuple[float, float, float]]], fermer_bas: bool = True,
         fermer_haut: bool = True, boucle: bool = False, lisser: bool = True, nom: str = "loft",
         materiau=None, pole_bas=None, pole_haut=None):
    """Surface fermée entre des anneaux successifs de même nombre de points.

    Chaque bout est fermé par une face (fermer_*), par un sommet pôle (pole_*), ou relié au
    premier anneau si boucle=True. Les normales sont recalculées par nettoyer().
    """
    exiger_bpy()
    n = len(anneaux[0])
    if any(len(a) != n for a in anneaux):
        raise ValueError("loft : tous les anneaux doivent avoir le même nombre de points")
    bm = bmesh.new()
    rings = [[bm.verts.new(p) for p in anneau] for anneau in anneaux]
    paires = list(zip(rings, rings[1:]))
    if boucle:
        paires.append((rings[-1], rings[0]))
    for a, b in paires:
        for k in range(n):
            k2 = (k + 1) % n
            if a[k].co == b[k].co and a[k2].co == b[k2].co:
                continue  # deux anneaux confondus : pas de face dégénérée
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if not boucle:
        if pole_bas is not None:
            v = bm.verts.new(pole_bas)
            for k in range(n):
                bm.faces.new((rings[0][(k + 1) % n], rings[0][k], v))
        elif fermer_bas:
            bm.faces.new(list(reversed(rings[0])))
        if pole_haut is not None:
            v = bm.verts.new(pole_haut)
            for k in range(n):
                bm.faces.new((rings[-1][k], rings[-1][(k + 1) % n], v))
        elif fermer_haut:
            bm.faces.new(rings[-1])
    return objet_depuis_bmesh(bm, nom, [materiau], lisser)


def revolution(profil_xy: Sequence[tuple[float, float]], segments: int = 32, lisser: bool = True,
               nom: str = "revolution", materiau=None):
    """Surface de révolution autour de Z d'un profil [(rayon, z), ...] du bas vers le haut.

    Un rayon nul au premier ou au dernier point donne un pôle ; sinon le bout est fermé par une
    face plane. Un rayon nul au milieu du profil est refusé. Utilise segments pair (symétrie).
    """
    if len(profil_xy) < 2:
        raise ValueError("revolution : au moins deux points de profil")
    pts = [(float(r), float(z)) for r, z in profil_xy]
    pole_bas = pole_haut = None
    if pts[0][0] <= 1e-9:
        pole_bas = (0.0, 0.0, pts[0][1])
        pts = pts[1:]
    if pts and pts[-1][0] <= 1e-9:
        pole_haut = (0.0, 0.0, pts[-1][1])
        pts = pts[:-1]
    if any(r <= 1e-9 for r, _ in pts):
        raise ValueError("revolution : rayon nul au milieu du profil")
    anneaux = [section_polaire("cercle", segments, r, r, z) for r, z in pts]
    return loft(anneaux, lisser=lisser, nom=nom, materiau=materiau,
                pole_bas=pole_bas, pole_haut=pole_haut)


def extrusion(polygone_xy: Sequence[tuple[float, float]], hauteur: float, biseau: float = 0.0,
              segments_biseau: int = 1, nom: str = "extrusion", materiau=None, z0: float = 0.0):
    """Prisme droit : polygone (sens trigonométrique vu de dessus) extrudé de z0 à z0+hauteur."""
    exiger_bpy()
    bm = bmesh.new()
    bas = [bm.verts.new((x, y, z0)) for x, y in polygone_xy]
    haut = [bm.verts.new((x, y, z0 + hauteur)) for x, y in polygone_xy]
    n = len(bas)
    bm.faces.new(list(reversed(bas)))
    bm.faces.new(haut)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((bas[k], bas[k2], haut[k2], haut[k]))
    if biseau > 0:
        bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=biseau,
                        segments=segments_biseau, affect="EDGES", clamp_overlap=True)
    return objet_depuis_bmesh(bm, nom, [materiau], False)


def boite(dims: tuple[float, float, float], biseau: float = 0.0, segments_biseau: int = 1,
          nom: str = "boite", materiau=None, centre=(0.0, 0.0, 0.0)):
    """Pavé de dimensions (x, y, z) centré sur `centre`, arêtes biseautées si biseau > 0."""
    dx, dy, dz = (d / 2.0 for d in dims)
    cx, cy, cz = centre
    poly = [(cx - dx, cy - dy), (cx + dx, cy - dy), (cx + dx, cy + dy), (cx - dx, cy + dy)]
    return extrusion(poly, dims[2], biseau, segments_biseau, nom, materiau, z0=cz - dz)


def cylindre(rayon: float, hauteur: float, segments: int = 32, rayon_haut: float | None = None,
             lisser: bool = True, nom: str = "cylindre", materiau=None, z0: float = 0.0):
    """Cylindre (ou tronc de cône) d'axe Z, base en z0."""
    rh = rayon if rayon_haut is None else rayon_haut
    return revolution([(rayon, z0), (rh, z0 + hauteur)], segments, lisser, nom, materiau)


def tore(rayon_majeur: float, rayon_mineur: float, segments_majeur: int = 24,
         segments_mineur: int = 12, angle_deg: float = 360.0, lisser: bool = True,
         nom: str = "tore", materiau=None):
    """Tore dans le plan XY, centré à l'origine ; partiel (angle < 360) = fermé par deux faces.

    Le secteur part de l'angle 0 (+X) et tourne vers +Y.
    """
    complet = angle_deg >= 360.0 - 1e-9
    nb = segments_majeur if complet else segments_majeur + 1
    anneaux = []
    for i in range(nb):
        phi = math.radians(angle_deg) * i / segments_majeur
        c, s = math.cos(phi), math.sin(phi)
        anneau = []
        for k in range(segments_mineur):
            t = 2.0 * math.pi * k / segments_mineur
            r = rayon_majeur + rayon_mineur * math.cos(t)
            anneau.append((r * c, r * s, rayon_mineur * math.sin(t)))
        anneaux.append(anneau)
    return loft(anneaux, boucle=complet, lisser=lisser, nom=nom, materiau=materiau)


def arc(rayon: float, epaisseur: float, segments: int = 16, profondeur: float = 0.3,
        angle_deg: float = 180.0, nom: str = "arc", materiau=None):
    """Arc (voûte) dans le plan XZ : secteur d'anneau de rayon extérieur `rayon`, épais de
    `epaisseur` vers l'intérieur, extrudé sur `profondeur` le long de Y. Part de +X vers +Z."""
    r_int = rayon - epaisseur
    p = profondeur / 2.0
    anneaux = []
    for i in range(segments + 1):
        phi = math.radians(angle_deg) * i / segments
        c, s = math.cos(phi), math.sin(phi)
        anneaux.append([(r_int * c, -p, r_int * s), (rayon * c, -p, rayon * s),
                        (rayon * c, p, rayon * s), (r_int * c, p, r_int * s)])
    return loft(anneaux, lisser=False, nom=nom, materiau=materiau)


def miroir_x(obj, distance_fusion: float = 1e-5) -> None:
    """Rend l'objet symétrique en X : coupe à x=0, garde le côté x<=0 et le reflète."""
    exiger_bpy()
    bm = bmesh_depuis_objet(obj)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                           plane_co=(0.0, 0.0, 0.0), plane_no=(1.0, 0.0, 0.0),
                           clear_outer=True, clear_inner=False)
    bmesh.ops.mirror(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], matrix=Matrix.Identity(4),
                     merge_dist=distance_fusion, axis="X")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ecrire_bmesh(obj, bm)


def cannelures(obj, n: int, profondeur: float, z_min: float | None = None,
               z_max: float | None = None, fondu: float = 0.0) -> None:
    """Creuse n cannelures radiales (autour de Z) : crêtes aux angles 2πk/n, creux entre.
    Les anneaux doivent avoir un nombre de sommets multiple de 2n (idéalement 4n). n pair
    conserve la symétrie X."""
    exiger_bpy()
    me = obj.data
    for v in me.vertices:
        x, y, z = v.co
        if z_min is not None and z < z_min - 1e-9 or z_max is not None and z > z_max + 1e-9:
            continue
        r = math.hypot(x, y)
        if r < 1e-9:
            continue
        theta = math.atan2(y, x)
        f = 0.5 - 0.5 * math.cos(n * theta)
        w = 1.0
        if fondu > 0:
            if z_min is not None:
                w = min(w, (z - z_min) / fondu)
            if z_max is not None:
                w = min(w, (z_max - z) / fondu)
            w = max(0.0, min(1.0, w))
        d = profondeur * f * w
        v.co = (x * (r - d) / r, y * (r - d) / r, z)
    me.update()


def biseauter(obj, largeur: float, segments: int = 1) -> None:
    """Biseaute toutes les arêtes de l'objet."""
    exiger_bpy()
    bm = bmesh_depuis_objet(obj)
    bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=largeur, segments=segments,
                    affect="EDGES", clamp_overlap=True)
    ecrire_bmesh(obj, bm)


# ---------------------------------------------------------------------------
# Jonction, nettoyage, pivot, UV
# ---------------------------------------------------------------------------
def joindre(objets: Sequence[Any], nom: str | None = None):
    """Fusionne plusieurs objets en un seul maillage (slots de matériaux réunis, transformations
    des objets appliquées). Les objets sources sont supprimés ; renvoie le premier, agrandi."""
    exiger_bpy()
    objets = [o for o in objets if o is not None]
    if not objets:
        raise ValueError("joindre : aucun objet")
    cible = objets[0]
    if nom:
        cible.name = nom
        cible.data.name = nom
    mats: list[Any] = list(cible.data.materials)
    bm = bmesh.new()
    for obj in objets:
        me = obj.data
        if obj.matrix_world != Matrix.Identity(4):
            me.transform(obj.matrix_world)
            obj.matrix_world = Matrix.Identity(4)
        correspondance = []
        for mat in me.materials:
            if mat not in mats:
                mats.append(mat)
            correspondance.append(mats.index(mat))
        if correspondance and correspondance != list(range(len(correspondance))):
            for poly in me.polygons:
                poly.material_index = correspondance[min(poly.material_index,
                                                        len(correspondance) - 1)]
        bm.from_mesh(me)
    for obj in objets[1:]:
        supprimer(obj)
    bm.to_mesh(cible.data)
    bm.free()
    cible.data.materials.clear()
    for mat in mats:
        cible.data.materials.append(mat)
    cible.data.update()
    return cible


def nettoyer(obj, distance_fusion: float = 1e-5) -> int:
    """Fusionne les doublons, supprime les sommets/arêtes isolés et les faces dégénérées,
    triangule les n-gones (> 4 côtés), recalcule les normales vers l'extérieur.
    Renvoie le nombre de triangles."""
    exiger_bpy()
    bm = bmesh_depuis_objet(obj)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=distance_fusion)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=distance_fusion)
    isoles = [v for v in bm.verts if not v.link_faces]
    if isoles:
        bmesh.ops.delete(bm, geom=isoles, context="VERTS")
    ngones = [f for f in bm.faces if len(f.verts) > 4]
    if ngones:
        bmesh.ops.triangulate(bm, faces=ngones, quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ecrire_bmesh(obj, bm)
    return compter_tris(obj)


def appliquer_transformations(obj) -> None:
    """Écrit la transformation de l'objet dans le maillage : scale 1, rotation 0, position 0."""
    exiger_bpy()
    if obj.matrix_world != Matrix.Identity(4):
        obj.data.transform(obj.matrix_world)
        obj.data.update()
    obj.matrix_world = Matrix.Identity(4)
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)


def boite_englobante(obj) -> tuple[Vector, Vector]:
    exiger_bpy()
    co = [v.co for v in obj.data.vertices]
    if not co:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    mini = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    maxi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    return mini, maxi


def dimensions(obj) -> tuple[float, float, float]:
    """Dimensions (x, y, z) du maillage en mètres, transformation comprise."""
    appliquer_transformations(obj)
    mini, maxi = boite_englobante(obj)
    d = maxi - mini
    return (d.x, d.y, d.z)


def placer_pivot(obj, mode: str = "sol_centre", point_poignee=None) -> None:
    """Déplace le maillage pour que l'origine de l'objet soit le pivot.

    sol_centre : centre de la boîte englobante en X/Y, bas en Z. poignee : `point_poignee`
    (coordonnées actuelles du maillage) devient l'origine."""
    appliquer_transformations(obj)
    if mode == "sol_centre":
        mini, maxi = boite_englobante(obj)
        decalage = Vector((-(mini.x + maxi.x) / 2.0, -(mini.y + maxi.y) / 2.0, -mini.z))
    elif mode == "poignee":
        if point_poignee is None:
            raise ValueError("placer_pivot : point_poignee requis en mode poignee")
        decalage = -Vector(point_poignee)
    else:
        raise ValueError(f"placer_pivot : mode inconnu {mode!r}")
    transformer(obj, Matrix.Translation(decalage))


def deplier_uv(obj, marge: float = 0.02, angle_limite_deg: float = 66.0) -> None:
    """Dépliage par projection intelligente (Smart UV Project) : îlots sans chevauchement,
    rangés dans le carré 0-1 avec une marge. Déterministe pour un maillage donné."""
    exiger_bpy()
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    me.uv_layers.active = me.uv_layers[0]
    for autre in bpy.context.view_layer.objects:
        autre.select_set(autre == obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle_limite_deg), island_margin=marge,
                                 area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")


def finaliser(obj, manifeste: dict[str, Any], style: Style, params: dict[str, Any],
              point_poignee=None, marge_uv: float = 0.02) -> Any:
    """Queue commune de build() : nettoyage, pivot selon la famille, transformations appliquées,
    UV dépliées, nom et métadonnées. Renvoie l'objet final."""
    nettoyer(obj)
    mode = style.pivot_pour(manifeste["famille"])
    placer_pivot(obj, mode, point_poignee)
    deplier_uv(obj, marge_uv)
    nom = str(params.get("id") or manifeste["nom"])
    obj.name = nom
    obj.data.name = nom
    obj["generateur"] = manifeste["nom"]
    obj["generateur_version"] = int(manifeste["version"])
    obj["categorie"] = manifeste["categorie"]
    obj["famille"] = manifeste["famille"]
    obj["symetrique"] = manifeste["symetrique"] or ""
    obj["pieces_declarees"] = int(manifeste["pieces_declarees"])
    obj["pivot"] = mode
    return obj


# ---------------------------------------------------------------------------
# Mesures (utilisées par les tests et par la finition)
# ---------------------------------------------------------------------------
def compter_tris(obj) -> int:
    return sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)


def aretes_non_manifold(obj) -> int:
    """Nombre d'arêtes qui ne bordent pas exactement deux faces."""
    bm = bmesh_depuis_objet(obj)
    n = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return n


def compter_pieces(obj) -> int:
    """Nombre de morceaux connexes (par les arêtes) du maillage."""
    bm = bmesh_depuis_objet(obj)
    vus = set()
    pieces = 0
    for v in bm.verts:
        if v.index in vus:
            continue
        pieces += 1
        pile = [v]
        vus.add(v.index)
        while pile:
            cur = pile.pop()
            for e in cur.link_edges:
                autre = e.other_vert(cur)
                if autre.index not in vus:
                    vus.add(autre.index)
                    pile.append(autre)
    bm.free()
    return pieces


def volume_signe(obj) -> float:
    bm = bmesh_depuis_objet(obj)
    v = bm.calc_volume(signed=True)
    bm.free()
    return v


def ecart_symetrie(obj, axe: str = "X") -> float:
    """Plus grande distance entre un sommet et le sommet le plus proche de son miroir."""
    exiger_bpy()
    verts = obj.data.vertices
    kd = KDTree(len(verts))
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()
    i_axe = _AXES[axe.lower()]
    pire = 0.0
    for v in verts:
        co = v.co.copy()
        co[i_axe] = -co[i_axe]
        _, _, dist = kd.find(co)
        pire = max(pire, dist)
    return pire


def uv_hors_carre(obj, eps: float = 1e-5) -> int:
    """Nombre de coins d'UV hors du carré 0-1."""
    couche = obj.data.uv_layers.active
    if couche is None:
        return len(obj.data.loops)
    return sum(1 for l in couche.data
               if l.uv.x < -eps or l.uv.x > 1 + eps or l.uv.y < -eps or l.uv.y > 1 + eps)


def chevauchements_uv(obj, resolution: int = 1024) -> int:
    """Nombre de pixels (grille resolution²) couverts par plus d'un triangle UV.
    Chaque triangle est très légèrement rétréci vers son centre pour que deux triangles
    adjacents ne partagent jamais un pixel : seul un vrai chevauchement compte."""
    import numpy as np

    me = obj.data
    couche = me.uv_layers.active
    if couche is None:
        return 0
    me.calc_loop_triangles()
    uv = np.array([tuple(l.uv) for l in couche.data], dtype=np.float64)
    couverture = np.zeros((resolution, resolution), dtype=np.int32)
    px = np.arange(resolution) + 0.5
    for tri in me.loop_triangles:
        p = uv[list(tri.loops)] * resolution
        centre = p.mean(axis=0)
        p = centre + (p - centre) * (1.0 - 1e-4)
        x0, y0 = np.floor(p.min(axis=0)).astype(int)
        x1, y1 = np.ceil(p.max(axis=0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, resolution), min(y1, resolution)
        if x1 <= x0 or y1 <= y0:
            continue
        xs = px[x0:x1][None, :]
        ys = px[y0:y1][:, None]
        (ax, ay), (bx, by), (cx, cy) = p
        aire = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(aire) < 1e-12:
            continue
        w0 = ((bx - xs) * (cy - ys) - (cx - xs) * (by - ys)) / aire
        w1 = ((cx - xs) * (ay - ys) - (ax - xs) * (cy - ys)) / aire
        w2 = 1.0 - w0 - w1
        dedans = (w0 > 0) & (w1 > 0) & (w2 > 0)
        couverture[y0:y1, x0:x1] += dedans
    return int((couverture > 1).sum())


def materiaux_hors_palette(obj, style: Style, eps: float = 1e-4) -> list[str]:
    """Noms des matériaux de l'objet dont la couleur de base n'est pas une couleur de la palette."""
    palette = [style.couleur_rgb(n) for n in style.palette]
    hors = []
    for mat in obj.data.materials:
        if mat is None:
            hors.append("<vide>")
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.use_nodes else None
        rgb = tuple(bsdf.inputs["Base Color"].default_value)[:3] if bsdf else tuple(
            mat.diffuse_color)[:3]
        if not any(all(abs(a - b) < eps for a, b in zip(rgb, p)) for p in palette):
            hors.append(mat.name)
    return hors


def distance_point_segment(p: tuple[float, float], a: tuple[float, float],
                           b: tuple[float, float]) -> float:
    """Distance 2D d'un point à un segment [a, b] (utile pour dessiner des motifs)."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 < 1e-18 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
