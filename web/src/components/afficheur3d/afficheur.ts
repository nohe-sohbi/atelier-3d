/*
 * Afficheur 3D de la Validation : tourner, zoomer, changer l'affichage, éclairer, voir la taille et le point d'ancrage,
 * poser à côté d'un personnage, pointer un défaut. Un fichier .glb de l'app contient les niveaux de détail
 * (…_LOD0, …_LOD1, …_LOD2) et la collision (…_COL) : un seul niveau est montré à la fois, jamais la collision.
 */
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

export type ModeAffichage = "texture" | "argile" | "fil" | "surfaces" | "damier";
export type NiveauDetail = 0 | 1 | 2;

export interface MesuresModele {
  /** Taille du niveau le plus fin, en mètres (largeur x, hauteur y, profondeur z dans le repère glTF). */
  largeur: number;
  hauteur: number;
  profondeur: number;
  /** Altitude du pied : 0 quand l'objet est posé au sol. */
  pied: number;
  /** Nombre de niveaux de détail trouvés dans le fichier. */
  niveaux: number;
}

export interface Afficheur {
  charger(url: string): Promise<MesuresModele>;
  niveau(n: NiveauDetail): void;
  mode(m: ModeAffichage): void;
  lumiere(p: { direction?: number; hauteur?: number }): void;
  reperes(on: boolean): void;
  personnage(on: boolean): void;
  tourner(on: boolean): void;
  recentrer(): void;
  pointage(on: boolean): void;
  effacerPastilles(): void;
  /** Appelé avec le numéro de la pastille posée. */
  surPointage: ((n: number) => void) | null;
  /** Appelé quand on touche une pastille déjà posée. */
  surPastille: ((n: number) => void) | null;
  /** Appelé quand le toucher arrête la rotation automatique. */
  surArretRotation: (() => void) | null;
  detruire(): void;
}

const chargeur = new GLTFLoader();
const cache = new Map<string, Promise<{ scene: THREE.Group }>>();

function chargerGlb(url: string): Promise<{ scene: THREE.Group }> {
  let p = cache.get(url);
  if (!p) {
    p = chargeur.loadAsync(url);
    p.catch(() => cache.delete(url)); // une erreur ne reste pas en cache : on peut réessayer
    cache.set(url, p);
  }
  return p;
}

const RE_LOD = /_LOD([0-2])$/;
const RE_COL = /_COL$/;

function damier(): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const g = c.getContext("2d")!;
  for (let i = 0; i < 8; i++) {
    for (let j = 0; j < 8; j++) {
      g.fillStyle = (i + j) % 2 ? "#3E5BD9" : "#EEF1FD";
      g.fillRect(i * 64, j * 64, 64, 64);
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  return t;
}

function tacheOmbre(): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d")!;
  const d = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  d.addColorStop(0, "rgba(0,0,0,.55)");
  d.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = d;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

/** Mannequin de 1,75 m, volontairement neutre : il sert d'étalon, pas de décor. */
function construirePersonnage(): THREE.Group {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0xa8a49b, roughness: 0.9 });
  const ajouter = (geo: THREE.BufferGeometry, x: number, y: number) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, 0);
    m.castShadow = true;
    m.receiveShadow = true;
    g.add(m);
  };
  ajouter(new THREE.CapsuleGeometry(0.07, 0.72, 6, 12), -0.09, 0.43);
  ajouter(new THREE.CapsuleGeometry(0.07, 0.72, 6, 12), 0.09, 0.43);
  ajouter(new THREE.CapsuleGeometry(0.17, 0.4, 6, 14), 0, 1.12);
  ajouter(new THREE.CapsuleGeometry(0.05, 0.52, 6, 10), -0.26, 1.08);
  ajouter(new THREE.CapsuleGeometry(0.05, 0.52, 6, 10), 0.26, 1.08);
  ajouter(new THREE.CylinderGeometry(0.05, 0.055, 0.1, 12), 0, 1.5);
  ajouter(new THREE.SphereGeometry(0.11, 18, 14), 0, 1.64);
  return g;
}

const fr = (v: number) => v.toFixed(2).replace(".", ",") + " m";

interface Pastille {
  n: number;
  position: THREE.Vector3;
  el: HTMLButtonElement;
}

/** `racine` : élément positionné qui reçoit le canvas. Lance une erreur si WebGL n'est pas disponible. */
export function creerAfficheur(racine: HTMLElement): Afficheur {
  const rendu = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  rendu.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  rendu.shadowMap.enabled = true;
  rendu.shadowMap.type = THREE.PCFSoftShadowMap;
  rendu.toneMapping = THREE.NeutralToneMapping;
  rendu.domElement.className = "afficheur__toile";
  racine.prepend(rendu.domElement);
  const calque = document.createElement("div");
  calque.className = "afficheur__calque";
  racine.append(calque);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(rendu);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  const camera = new THREE.PerspectiveCamera(32, 1, 0.01, 60);
  const controles = new OrbitControls(camera, rendu.domElement);
  controles.enableDamping = true;
  controles.dampingFactor = 0.14;
  controles.autoRotateSpeed = 2.2;
  controles.screenSpacePanning = true;

  const soleil = new THREE.DirectionalLight(0xffffff, 2.3);
  soleil.castShadow = true;
  soleil.shadow.mapSize.set(1024, 1024);
  scene.add(soleil, soleil.target);
  const groupe = new THREE.Group();
  scene.add(groupe);
  const sol = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.ShadowMaterial({ opacity: 0.22 }));
  sol.rotation.x = -Math.PI / 2;
  sol.receiveShadow = true;
  scene.add(sol);
  const tache = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.MeshBasicMaterial({ map: tacheOmbre(), transparent: true, opacity: 0.5, depthWrite: false }),
  );
  tache.rotation.x = -Math.PI / 2;
  scene.add(tache);
  const aides = new THREE.Group();
  aides.visible = false;
  scene.add(aides);
  const perso = construirePersonnage();
  perso.visible = false;
  scene.add(perso);

  const matieres = {
    argile: new THREE.MeshStandardMaterial({ color: 0xd2cbc0, roughness: 0.92, metalness: 0, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }),
    surfaces: new THREE.MeshNormalMaterial(),
    damier: new THREE.MeshStandardMaterial({ map: damier(), roughness: 0.8, metalness: 0 }),
  };
  const dosRouge = new THREE.MeshBasicMaterial({ color: 0xe5484d, side: THREE.BackSide });
  const traitFil = new THREE.LineBasicMaterial({ color: 0x20242e, transparent: true, opacity: 0.6 });

  let objet: THREE.Object3D | null = null;
  let meshes: THREE.Mesh[] = [];
  let niveaux: Array<THREE.Object3D[]> = [[], [], []];
  let boite = new THREE.Box3();
  let centre = new THREE.Vector3();
  let rayon = 1;
  let modeActuel: ModeAffichage = "texture";
  let angle = { direction: 40, hauteur: 50 };
  let sale = true;
  let pointage = false;
  let interagi = false;
  let persoActif = false;
  let detruit = false;
  let raf = 0;
  const pastilles: Pastille[] = [];
  const cotes: Array<{ pos: THREE.Vector3; el: HTMLElement }> = [];
  let pivot: { pos: THREE.Vector3; el: HTMLElement } | null = null;

  const api: Afficheur = {
    charger: async () => {
      throw new Error("pas encore");
    },
    niveau: () => undefined,
    mode: () => undefined,
    lumiere: () => undefined,
    reperes: () => undefined,
    personnage: () => undefined,
    tourner: () => undefined,
    recentrer: () => undefined,
    pointage: () => undefined,
    effacerPastilles: () => undefined,
    surPointage: null,
    surPastille: null,
    surArretRotation: null,
    detruire: () => undefined,
  };

  const visible = () => racine.offsetWidth > 0 && racine.offsetHeight > 0;
  const demander = () => {
    sale = true;
  };

  function placerLumiere() {
    const d = THREE.MathUtils.degToRad(angle.direction);
    const h = THREE.MathUtils.degToRad(angle.hauteur);
    const R = rayon * 5;
    soleil.position.set(centre.x + Math.sin(d) * Math.cos(h) * R, centre.y + Math.sin(h) * R, centre.z + Math.cos(d) * Math.cos(h) * R);
    soleil.target.position.copy(centre);
    const c = soleil.shadow.camera;
    const e = rayon * 1.8;
    c.left = -e;
    c.right = e;
    c.top = e;
    c.bottom = -e;
    c.near = rayon * 0.5;
    c.far = rayon * 11;
    c.updateProjectionMatrix();
    soleil.shadow.bias = -0.0004;
    soleil.shadow.normalBias = rayon * 0.012;
    demander();
  }

  function cadrer(r = rayon, c = centre) {
    const vfov = THREE.MathUtils.degToRad(camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
    const d = r / Math.sin(Math.min(vfov, hfov) / 2);
    const az = THREE.MathUtils.degToRad(35);
    const po = THREE.MathUtils.degToRad(75);
    controles.target.copy(c);
    camera.position.set(c.x + d * Math.sin(po) * Math.sin(az), c.y + d * Math.cos(po), c.z + d * Math.sin(po) * Math.cos(az));
    controles.minDistance = r * 0.6;
    controles.maxDistance = d * 3;
    camera.near = Math.max(0.005, d / 200);
    camera.far = d * 30;
    camera.updateProjectionMatrix();
    controles.update();
    demander();
  }

  function placerPerso() {
    perso.position.set(boite.max.x + 0.5, boite.min.y, centre.z);
  }

  function cadrerCourant() {
    if (!persoActif) return cadrer();
    const u = boite.clone().union(new THREE.Box3().setFromObject(perso));
    cadrer(u.getSize(new THREE.Vector3()).length() / 2, u.getCenter(new THREE.Vector3()));
  }

  function redimensionner() {
    const w = racine.clientWidth;
    const h = racine.clientHeight;
    if (!w || !h) return;
    rendu.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (objet && !interagi) cadrerCourant();
    demander();
  }
  const observateur = new ResizeObserver(redimensionner);
  observateur.observe(racine);

  /** Les meshes du niveau montré ; tous ceux du fichier quand il n'a pas de niveaux nommés. */
  function meshesVisibles(): THREE.Mesh[] {
    const sortie: THREE.Mesh[] = [];
    objet?.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      let v = true;
      for (let n: THREE.Object3D | null = o; n && n !== objet; n = n.parent) if (!n.visible) v = false;
      if (v && !o.userData.aide) sortie.push(o);
    });
    return sortie;
  }

  function construireAides() {
    aides.clear();
    for (const c of cotes) c.el.remove();
    cotes.length = 0;
    pivot?.el.remove();
    pivot = null;
    const taille = boite.getSize(new THREE.Vector3());
    const grand = Math.max(taille.x, taille.y, taille.z);
    const pas = 0.1;
    const cote = Math.max(1, Math.ceil((grand * 2.6) / pas / 2) * 2 * pas);
    const grille = new THREE.GridHelper(cote, Math.round(cote / pas), 0x9a968e, 0xc8c4bb);
    grille.position.y = 0.0008;
    const mg = grille.material as THREE.Material;
    mg.transparent = true;
    mg.opacity = 0.55;
    aides.add(grille);
    const axes = new THREE.AxesHelper(Math.max(0.2, grand * 0.4));
    (axes.material as THREE.Material).depthTest = false;
    axes.renderOrder = 5;
    aides.add(axes);
    const rondPivot = new THREE.Mesh(
      new THREE.SphereGeometry(Math.max(0.008, grand * 0.018), 16, 12),
      new THREE.MeshBasicMaterial({ color: 0xf08a24, depthTest: false }),
    );
    rondPivot.renderOrder = 6;
    aides.add(rondPivot);
    const bh = new THREE.Box3Helper(boite, 0x3555d6);
    (bh.material as THREE.Material).depthTest = false;
    bh.renderOrder = 4;
    aides.add(bh);
    const b = boite;
    const c = centre;
    const etiquettes: Array<[THREE.Vector3, string]> = [
      [new THREE.Vector3(c.x, b.min.y, b.max.z), fr(taille.x)],
      [new THREE.Vector3(b.max.x, b.min.y, c.z), fr(taille.z)],
      [new THREE.Vector3(b.max.x, c.y, b.max.z), fr(taille.y)],
    ];
    for (const [pos, texte] of etiquettes) {
      const el = document.createElement("span");
      el.className = "afficheur__cote";
      el.textContent = texte;
      el.hidden = true;
      calque.append(el);
      cotes.push({ pos, el });
    }
    const lp = document.createElement("span");
    lp.className = "afficheur__cote afficheur__cote--ancrage";
    lp.textContent = "Point d'ancrage";
    lp.hidden = true;
    calque.append(lp);
    pivot = { pos: new THREE.Vector3(0, 0, 0), el: lp };
  }

  api.charger = async (url) => {
    const gltf = await chargerGlb(url);
    if (detruit) throw new Error("afficheur détruit");
    if (objet) groupe.remove(objet);
    objet = gltf.scene.clone(true);
    groupe.add(objet);
    niveaux = [[], [], []];
    objet.traverse((o) => {
      const m = RE_LOD.exec(o.name);
      if (m) niveaux[Number(m[1])]!.push(o);
      if (RE_COL.test(o.name)) o.visible = false;
      if (o instanceof THREE.Mesh) {
        o.castShadow = o.receiveShadow = true;
        o.userData.orig = o.material;
      }
    });
    api.niveau(0);
    // La taille se mesure sur le niveau le plus fin seulement (la collision et les autres niveaux ne comptent pas).
    boite = new THREE.Box3();
    if (niveaux[0]!.length) for (const n of niveaux[0]!) boite.union(new THREE.Box3().setFromObject(n));
    else boite.setFromObject(objet);
    centre = boite.getCenter(new THREE.Vector3());
    const taille = boite.getSize(new THREE.Vector3());
    rayon = taille.length() / 2;
    sol.position.set(centre.x, boite.min.y - 0.0005, centre.z);
    sol.scale.setScalar(rayon * 7);
    const emprise = Math.max(taille.x, taille.z) * 1.7;
    tache.position.set(centre.x, boite.min.y + 0.0004, centre.z);
    tache.scale.set(emprise, emprise, 1);
    construireAides();
    placerLumiere();
    placerPerso();
    api.mode(modeActuel);
    interagi = false;
    cadrerCourant();
    demander();
    return { largeur: taille.x, hauteur: taille.y, profondeur: taille.z, pied: boite.min.y, niveaux: niveaux.filter((n) => n.length).length };
  };

  api.niveau = (n) => {
    if (!objet) return;
    const connus = niveaux.some((l) => l.length);
    if (connus) niveaux.forEach((liste, i) => liste.forEach((o) => (o.visible = i === n)));
    meshes = meshesVisibles();
    api.mode(modeActuel);
    demander();
  };

  api.mode = (m) => {
    modeActuel = m;
    for (const me of meshes) {
      me.material = m === "texture" ? (me.userData.orig as THREE.Material) : m === "argile" || m === "fil" ? matieres.argile : matieres[m];
      let fil = me.children.find((c) => c.userData.role === "fil");
      let dos = me.children.find((c) => c.userData.role === "dos");
      if (m === "fil" && !fil) {
        const l = new THREE.LineSegments(new THREE.WireframeGeometry(me.geometry), traitFil);
        l.userData.role = "fil";
        l.userData.aide = true;
        me.add(l);
        fil = l;
      }
      if (m === "surfaces" && !dos) {
        const d = new THREE.Mesh(me.geometry, dosRouge);
        d.userData.role = "dos";
        d.userData.aide = true;
        me.add(d);
        dos = d;
      }
      if (fil) fil.visible = m === "fil";
      if (dos) dos.visible = m === "surfaces";
    }
    demander();
  };

  api.lumiere = (p) => {
    angle = { ...angle, ...p };
    placerLumiere();
  };
  api.tourner = (on) => {
    controles.autoRotate = on;
    demander();
  };
  api.recentrer = () => {
    interagi = false;
    cadrerCourant();
  };
  api.reperes = (on) => {
    aides.visible = on;
    for (const c of cotes) c.el.hidden = !on;
    if (pivot) pivot.el.hidden = !on;
    demander();
  };
  api.personnage = (on) => {
    persoActif = on;
    perso.visible = on;
    if (objet) {
      placerPerso();
      interagi = false;
      cadrerCourant();
    }
    demander();
  };

  // --- pointer un défaut ---
  api.pointage = (on) => {
    pointage = on;
    rendu.domElement.style.cursor = on ? "crosshair" : "";
  };
  api.effacerPastilles = () => {
    for (const p of pastilles) p.el.remove();
    pastilles.length = 0;
    demander();
  };
  const rayonLancer = new THREE.Raycaster();
  let depart: { x: number; y: number; t: number } | null = null;
  const auBas = (e: PointerEvent) => {
    depart = { x: e.clientX, y: e.clientY, t: performance.now() };
    interagi = true;
    if (controles.autoRotate) {
      controles.autoRotate = false;
      api.surArretRotation?.();
    }
  };
  const auHaut = (e: PointerEvent) => {
    if (!pointage || !depart) return;
    const bouge = Math.hypot(e.clientX - depart.x, e.clientY - depart.y);
    const duree = performance.now() - depart.t;
    depart = null;
    if (bouge > 7 || duree > 700) return;
    const r = rendu.domElement.getBoundingClientRect();
    rayonLancer.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const touche = rayonLancer.intersectObjects(meshes, false)[0];
    if (!touche) return;
    const n = pastilles.length + 1;
    const el = document.createElement("button");
    el.type = "button";
    el.className = "afficheur__pastille";
    el.textContent = String(n);
    el.setAttribute("aria-label", `Pastille ${n} sur l'objet`);
    el.addEventListener("click", (ev) => {
      ev.stopPropagation();
      api.surPastille?.(n);
    });
    calque.append(el);
    pastilles.push({ n, position: touche.point.clone(), el });
    demander();
    api.surPointage?.(n);
  };
  rendu.domElement.addEventListener("pointerdown", auBas);
  rendu.domElement.addEventListener("pointerup", auHaut);

  // --- projection des pastilles et des étiquettes sur l'écran ---
  const v = new THREE.Vector3();
  const rayonOcclusion = new THREE.Raycaster();
  function projeter(pos: THREE.Vector3, el: HTMLElement, occlusion: boolean) {
    v.copy(pos).project(camera);
    const derriere = v.z > 1 || v.z < -1;
    el.style.transform = `translate(${((v.x * 0.5 + 0.5) * racine.clientWidth).toFixed(1)}px,${((-v.y * 0.5 + 0.5) * racine.clientHeight).toFixed(1)}px)`;
    el.style.visibility = derriere ? "hidden" : "visible";
    if (occlusion && !derriere) {
      const dir = pos.clone().sub(camera.position);
      const dist = dir.length();
      rayonOcclusion.set(camera.position, dir.normalize());
      const touche = rayonOcclusion.intersectObjects(meshes, false)[0];
      el.classList.toggle("afficheur__pastille--cachee", !!touche && touche.distance < dist - rayon * 0.02);
    }
  }
  function dessiner() {
    rendu.render(scene, camera);
    for (const p of pastilles) projeter(p.position, p.el, true);
    if (aides.visible) {
      for (const c of cotes) projeter(c.pos, c.el, false);
      if (pivot) projeter(pivot.pos, pivot.el, false);
    }
  }
  function boucle() {
    if (detruit) return;
    raf = requestAnimationFrame(boucle);
    if (!visible()) return;
    const bouge = controles.update();
    if (bouge || sale) {
      dessiner();
      sale = false;
    }
  }
  raf = requestAnimationFrame(boucle);
  controles.addEventListener("change", demander);

  api.detruire = () => {
    detruit = true;
    cancelAnimationFrame(raf);
    observateur.disconnect();
    rendu.domElement.removeEventListener("pointerdown", auBas);
    rendu.domElement.removeEventListener("pointerup", auHaut);
    controles.dispose();
    for (const m of Object.values(matieres)) m.dispose();
    pmrem.dispose();
    rendu.dispose();
    rendu.domElement.remove();
    calque.remove();
  };
  return api;
}
