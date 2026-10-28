// Afficheur 3D de la maquette : tourner, zoomer, changer l'affichage, éclairer, vérifier le point d'ancrage,
// pointer un défaut. Même principe que ce que fera l'app ; les mesures viennent du fichier GLB lui-même.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const chargeur = new GLTFLoader();
const cacheGlb = new Map(); // url → Promise<gltf> : changer de niveau de détail est instantané la 2e fois

export function chargerGlb(url) {
  if (!cacheGlb.has(url)) cacheGlb.set(url, chargeur.loadAsync(url));
  return cacheGlb.get(url);
}

export function mesurer(gltf) {
  const boite = new THREE.Box3().setFromObject(gltf.scene);
  let triangles = 0, uv = true;
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    triangles += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
    if (!o.geometry.attributes.uv) uv = false;
  });
  return { boite, taille: boite.getSize(new THREE.Vector3()), centre: boite.getCenter(new THREE.Vector3()), triangles, uv };
}

const m = v => v.toFixed(2).replace(".", ",") + " m";
const cm = v => Math.abs(v * 100).toFixed(1).replace(".", ",") + " cm";

function damier() {
  const c = document.createElement("canvas"); c.width = c.height = 512;
  const g = c.getContext("2d");
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { g.fillStyle = (i + j) % 2 ? "#3E5BD9" : "#EEF1FD"; g.fillRect(i * 64, j * 64, 64, 64); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
  return t;
}

function tacheOmbre() {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d"), d = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  d.addColorStop(0, "rgba(0,0,0,.55)"); d.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = d; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}


/** Mannequin de 1,75 m, volontairement neutre : il sert d'étalon, pas de décor. */
export function construirePersonnage() {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0xa8a49b, roughness: 0.9 });
  const ajouter = (geo, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; g.add(m); };
  ajouter(new THREE.CapsuleGeometry(0.07, 0.72, 6, 12), -0.09, 0.43, 0);
  ajouter(new THREE.CapsuleGeometry(0.07, 0.72, 6, 12), 0.09, 0.43, 0);
  ajouter(new THREE.CapsuleGeometry(0.17, 0.4, 6, 14), 0, 1.12, 0);
  ajouter(new THREE.CapsuleGeometry(0.05, 0.52, 6, 10), -0.26, 1.08, 0);
  ajouter(new THREE.CapsuleGeometry(0.05, 0.52, 6, 10), 0.26, 1.08, 0);
  ajouter(new THREE.CylinderGeometry(0.05, 0.055, 0.1, 12), 0, 1.5, 0);
  ajouter(new THREE.SphereGeometry(0.11, 18, 14), 0, 1.64, 0);
  return g;
}

/**
 * racine : élément positionné (relative/absolute) qui reçoit le canvas.
 * Retourne l'objet de pilotage : charger(url), mode(nom), lumiere({direction, hauteur}), reperes(bool), tourner(bool),
 * recentrer(), pointage(bool), vues(angles, taille), et les rappels surPointage / surPastille.
 */
export function creerVisionneuse(racine) {
  const rendu = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: false });
  rendu.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  rendu.shadowMap.enabled = true; rendu.shadowMap.type = THREE.PCFSoftShadowMap;
  rendu.toneMapping = THREE.NeutralToneMapping;
  rendu.domElement.className = "toile3d";
  racine.prepend(rendu.domElement);
  const calquePastilles = document.createElement("div"); calquePastilles.className = "calque3d"; racine.append(calquePastilles);
  const etat = document.createElement("div"); etat.className = "etat3d"; etat.textContent = "Chargement de la 3D…"; racine.append(etat);

  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(rendu).fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  const camera = new THREE.PerspectiveCamera(32, 1, 0.01, 60);
  const controles = new OrbitControls(camera, rendu.domElement);
  controles.enableDamping = true; controles.dampingFactor = 0.14; controles.autoRotateSpeed = 2.2;
  controles.screenSpacePanning = true;

  const soleil = new THREE.DirectionalLight(0xffffff, 2.3);
  soleil.castShadow = true; soleil.shadow.mapSize.set(1024, 1024);
  scene.add(soleil, soleil.target);
  const groupe = new THREE.Group(); scene.add(groupe);
  const sol = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.ShadowMaterial({ opacity: 0.22 }));
  sol.rotation.x = -Math.PI / 2; sol.receiveShadow = true; scene.add(sol);
  const tache = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: tacheOmbre(), transparent: true, opacity: 0.5, depthWrite: false }));
  tache.rotation.x = -Math.PI / 2; scene.add(tache);
  const aides = new THREE.Group(); aides.visible = false; scene.add(aides);

  const matieres = {
    argile: new THREE.MeshStandardMaterial({ color: 0xd2cbc0, roughness: 0.92, metalness: 0, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }),
    surfaces: new THREE.MeshNormalMaterial(),
    damier: new THREE.MeshStandardMaterial({ map: damier(), roughness: 0.8, metalness: 0 }),
  };
  const dosRouge = new THREE.MeshBasicMaterial({ color: 0xe5484d, side: THREE.BackSide });
  const traitFil = new THREE.LineBasicMaterial({ color: 0x20242e, transparent: true, opacity: 0.6 });

  const api = { surPointage: null, surPastille: null, mesure: null, modeActuel: "texture" };
  let meshes = [], objet = null, rayon = 1, centre = new THREE.Vector3(), boite = new THREE.Box3();
  let sale = true, pointage = false, premier = true, interagi = false, reperesActifs = false;
  let angle = { direction: 40, hauteur: 50 };
  const pastilles = []; const cotes = []; let etiquettePivot = null;

  const visible = () => racine.offsetWidth > 0 && racine.offsetHeight > 0;
  const demander = () => { sale = true; };

  function placerLumiere() {
    const d = THREE.MathUtils.degToRad(angle.direction), h = THREE.MathUtils.degToRad(angle.hauteur);
    const R = rayon * 5;
    soleil.position.set(centre.x + Math.sin(d) * Math.cos(h) * R, centre.y + Math.sin(h) * R, centre.z + Math.cos(d) * Math.cos(h) * R);
    soleil.target.position.copy(centre);
    const c = soleil.shadow.camera, e = rayon * 1.8;
    c.left = -e; c.right = e; c.top = e; c.bottom = -e; c.near = rayon * 0.5; c.far = rayon * 11; c.updateProjectionMatrix();
    soleil.shadow.bias = -0.0004; soleil.shadow.normalBias = rayon * 0.012;
    demander();
  }

  function cadrer(r = rayon, c = centre) {
    const vfov = THREE.MathUtils.degToRad(camera.fov), hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
    const d = (r / Math.sin(Math.min(vfov, hfov) / 2)) * 1.0;
    const az = THREE.MathUtils.degToRad(35), po = THREE.MathUtils.degToRad(75);
    controles.target.copy(c);
    camera.position.set(c.x + d * Math.sin(po) * Math.sin(az), c.y + d * Math.cos(po), c.z + d * Math.sin(po) * Math.cos(az));
    controles.minDistance = r * 0.6; controles.maxDistance = d * 3;
    camera.near = Math.max(0.005, d / 200); camera.far = d * 30; camera.updateProjectionMatrix();
    controles.update(); demander();
  }

  function redimensionner() {
    const w = racine.clientWidth, h = racine.clientHeight; if (!w || !h) return;
    rendu.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    if (objet && !interagi) cadrerCourant();
    demander();
  }
  new ResizeObserver(redimensionner).observe(racine);

  // ---- chargement d'un modèle ----
  api.charger = async (url, { recadrer = false } = {}) => {
    etat.hidden = false; etat.textContent = "Chargement de la 3D…";
    let gltf;
    try { gltf = await chargerGlb(url); } catch { etat.textContent = "Impossible d'ouvrir ce modèle."; throw new Error("glb"); }
    if (objet) groupe.remove(objet);
    objet = gltf.scene.clone(true); groupe.add(objet);
    meshes = [];
    objet.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; o.userData.orig = o.material; meshes.push(o); } });
    const mes = mesurer({ scene: objet }); api.mesure = mes;
    boite = mes.boite; centre = mes.centre.clone(); rayon = mes.taille.length() / 2;
    const ground = boite.min.y;
    sol.position.set(centre.x, ground - 0.0005, centre.z); sol.scale.setScalar(rayon * 7);
    tache.position.set(centre.x, ground + 0.0004, centre.z); tache.scale.set(Math.max(mes.taille.x, mes.taille.z) * 1.7, Math.max(mes.taille.x, mes.taille.z) * 1.7, 1);
    construireAides(mes); placerLumiere(); placerPerso();
    api.mode(api.modeActuel);
    if (premier || recadrer) { cadrerCourant(); premier = false; interagi = false; }
    etat.hidden = true; demander();
    return mes;
  };


  // ---- personnage de 1,75 m pour juger l'échelle ----
  const perso = construirePersonnage(); perso.visible = false; scene.add(perso);
  let persoActif = false;
  function placerPerso() {
    perso.position.set(boite.max.x + 0.5, boite.min.y, centre.z);
  }
  function cadrerCourant() {
    if (!persoActif) return cadrer();
    const u = boite.clone().union(new THREE.Box3().setFromObject(perso));
    cadrer(u.getSize(new THREE.Vector3()).length() / 2, u.getCenter(new THREE.Vector3()));
  }
  api.personnage = on => { persoActif = on; perso.visible = on; if (objet) { placerPerso(); interagi = false; cadrerCourant(); } demander(); };

  // ---- modes d'affichage ----
  api.mode = nom => {
    api.modeActuel = nom;
    for (const me of meshes) {
      me.material = nom === "texture" ? me.userData.orig : (nom === "argile" || nom === "fil") ? matieres.argile : matieres[nom];
      const fil = me.children.find(c => c.userData.role === "fil"), dos = me.children.find(c => c.userData.role === "dos");
      if (nom === "fil" && !fil) { const l = new THREE.LineSegments(new THREE.WireframeGeometry(me.geometry), traitFil); l.userData.role = "fil"; me.add(l); }
      if (nom === "surfaces" && !dos) { const d = new THREE.Mesh(me.geometry, dosRouge); d.userData.role = "dos"; me.add(d); }
      me.children.forEach(c => { if (c.userData.role === "fil") c.visible = nom === "fil"; if (c.userData.role === "dos") c.visible = nom === "surfaces"; });
    }
    demander();
  };

  api.lumiere = (p = {}) => { angle = { ...angle, ...p }; placerLumiere(); };
  api.tourner = on => { controles.autoRotate = on; demander(); };
  api.recentrer = () => { interagi = false; cadrerCourant(); };

  // ---- repères : sol, axes, boîte, tailles, point d'ancrage ----
  function construireAides(mes) {
    aides.clear(); cotes.length = 0; etiquettePivot = null;
    const grand = Math.max(mes.taille.x, mes.taille.y, mes.taille.z), pas = 0.1;
    const cote = Math.max(1, Math.ceil((grand * 2.6) / pas / 2) * 2 * pas);
    const grille = new THREE.GridHelper(cote, Math.round(cote / pas), 0x9a968e, 0xc8c4bb);
    grille.position.y = 0.0008; grille.material.transparent = true; grille.material.opacity = 0.55; aides.add(grille);
    const axes = new THREE.AxesHelper(Math.max(0.2, grand * 0.4)); axes.material.depthTest = false; axes.renderOrder = 5; aides.add(axes);
    const pivot = new THREE.Mesh(new THREE.SphereGeometry(Math.max(0.008, grand * 0.018), 16, 12), new THREE.MeshBasicMaterial({ color: 0xf08a24, depthTest: false }));
    pivot.renderOrder = 6; aides.add(pivot);
    const bh = new THREE.Box3Helper(mes.boite, 0x3555d6); bh.material.depthTest = false; bh.renderOrder = 4; aides.add(bh);
    const b = mes.boite, c = mes.centre;
    const def = [[new THREE.Vector3(c.x, b.min.y, b.max.z), m(mes.taille.x), "l"], [new THREE.Vector3(b.max.x, b.min.y, c.z), m(mes.taille.z), "p"], [new THREE.Vector3(b.max.x, c.y, b.max.z), m(mes.taille.y), "h"]];
    for (const [pos, txt, cls] of def) { const el = document.createElement("span"); el.className = "cote3d"; el.textContent = txt; el.hidden = true; calquePastilles.append(el); cotes.push({ pos, el }); }
    const lp = document.createElement("span"); lp.className = "cote3d pivot"; lp.textContent = "Point d'ancrage"; lp.hidden = true; calquePastilles.append(lp);
    etiquettePivot = { pos: new THREE.Vector3(0, 0, 0), el: lp };
  }
  api.reperes = on => { reperesActifs = on; aides.visible = on; cotes.forEach(c => c.el.hidden = !on); if (etiquettePivot) etiquettePivot.el.hidden = !on; demander(); };

  /** Vérifications calculées sur le vrai fichier. */
  api.verifications = () => {
    const mes = api.mesure; if (!mes) return [];
    const pied = mes.boite.min.y, dx = mes.centre.x, dz = mes.centre.z;
    const tol = Math.max(0.004, Math.max(mes.taille.x, mes.taille.z) * 0.03);
    const sol = Math.abs(pied) <= 0.003;
    const centre = Math.hypot(dx, dz) <= tol;
    return [
      { ok: sol, texte: sol ? "Posé au sol : le pied est à 0 cm" : (pied > 0 ? "Flotte à " + cm(pied) + " au-dessus du sol" : "Enfoncé de " + cm(pied) + " sous le sol") },
      { ok: centre, texte: centre ? "Point d'ancrage au centre, au pied de l'objet" : "Point d'ancrage décalé de " + cm(Math.hypot(dx, dz)) },
      { ok: true, info: true, texte: "Taille " + m(mes.taille.x) + " × " + m(mes.taille.z) + " × " + m(mes.taille.y) + " (L × P × H)" },
    ];
  };

  // ---- pointer un défaut ----
  api.pointage = on => { pointage = on; rendu.domElement.style.cursor = on ? "crosshair" : ""; };
  const rayonLancer = new THREE.Raycaster();
  let depart = null;
  rendu.domElement.addEventListener("pointerdown", e => { depart = { x: e.clientX, y: e.clientY, t: performance.now() }; interagi = true; if (controles.autoRotate) { controles.autoRotate = false; racine.dispatchEvent(new CustomEvent("arret-rotation")); } });
  rendu.domElement.addEventListener("pointerup", e => {
    if (!pointage || !depart) return;
    const bouge = Math.hypot(e.clientX - depart.x, e.clientY - depart.y), duree = performance.now() - depart.t; depart = null;
    if (bouge > 7 || duree > 700) return;
    const r = rendu.domElement.getBoundingClientRect();
    rayonLancer.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const hit = rayonLancer.intersectObjects(meshes, false)[0]; if (!hit) return;
    const n = pastilles.length + 1;
    const el = document.createElement("button"); el.className = "pin"; el.textContent = n; el.setAttribute("aria-label", "Défaut " + n);
    el.addEventListener("click", ev => { ev.stopPropagation(); api.surPastille && api.surPastille(n); });
    calquePastilles.append(el);
    pastilles.push({ n, pos: hit.point.clone(), el });
    demander();
    api.surPointage && api.surPointage({ n });
  });

  // ---- vues fixes (miniatures générées depuis le vrai modèle) ----
  api.vues = (angles, taille = 240) => {
    if (!objet) return [];
    const sauvegarde = { pos: camera.position.clone(), asp: camera.aspect, cibles: pastilles.map(p => p.el.style.display) };
    const pr = rendu.getPixelRatio();
    aides.visible = false; calquePastilles.style.display = "none"; tache.visible = true;
    rendu.setPixelRatio(1); rendu.setSize(taille, taille, false); camera.aspect = 1; camera.updateProjectionMatrix();
    const vfov = THREE.MathUtils.degToRad(camera.fov), d = (rayon / Math.sin(vfov / 2)) * 0.95;
    const images = angles.map(([az, po]) => {
      const a = THREE.MathUtils.degToRad(az), p = THREE.MathUtils.degToRad(po);
      camera.position.set(centre.x + d * Math.sin(p) * Math.sin(a), centre.y + d * Math.cos(p), centre.z + d * Math.sin(p) * Math.cos(a));
      camera.lookAt(centre); rendu.render(scene, camera); return rendu.domElement.toDataURL("image/png");
    });
    rendu.setPixelRatio(pr); const avait = interagi; redimensionner();
    if (avait) { camera.position.copy(sauvegarde.pos); controles.update(); }
    aides.visible = reperesActifs; calquePastilles.style.display = "";
    demander(); return images;
  };

  // ---- projection des pastilles et étiquettes ----
  const v = new THREE.Vector3(), ray = new THREE.Raycaster();
  function projeter(pos, el, occlusion) {
    v.copy(pos).project(camera);
    const w = racine.clientWidth, h = racine.clientHeight;
    const derriere = v.z > 1 || v.z < -1;
    el.style.transform = `translate(${((v.x * 0.5 + 0.5) * w).toFixed(1)}px,${((-v.y * 0.5 + 0.5) * h).toFixed(1)}px)`;
    el.style.visibility = derriere ? "hidden" : "visible";
    if (occlusion && !derriere) {
      const dir = pos.clone().sub(camera.position), dist = dir.length(); ray.set(camera.position, dir.normalize());
      const hit = ray.intersectObjects(meshes, false)[0];
      el.classList.toggle("cache", !!hit && hit.distance < dist - rayon * 0.02);
    }
  }
  function dessiner() {
    rendu.render(scene, camera);
    pastilles.forEach(p => projeter(p.pos, p.el, true));
    if (aides.visible) { cotes.forEach(c => projeter(c.pos, c.el, false)); if (etiquettePivot) projeter(etiquettePivot.pos, etiquettePivot.el, false); }
  }
  (function boucle() {
    requestAnimationFrame(boucle);
    if (!visible()) return;
    const bouge = controles.update();
    if (bouge || sale) { dessiner(); sale = false; }
  })();
  controles.addEventListener("change", demander);

  api.effacerPastilles = () => { pastilles.forEach(p => p.el.remove()); pastilles.length = 0; demander(); };
  api.racine = racine;
  return api;
}

/**
 * Scène d'essai : plusieurs objets ensemble, vue d'ensemble ou vue du joueur, trois éclairages.
 * disposition : [{ id, nom, url, instances: [{ x, z, y?, ry?, s? }] }]
 */
export function creerEssai(racine) {
  const rendu = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  rendu.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  rendu.shadowMap.enabled = true; rendu.shadowMap.type = THREE.PCFSoftShadowMap; rendu.toneMapping = THREE.NeutralToneMapping;
  rendu.domElement.className = "toile3d"; racine.prepend(rendu.domElement);
  const calque = document.createElement("div"); calque.className = "calque3d"; racine.append(calque);
  const etat = document.createElement("div"); etat.className = "etat3d"; etat.textContent = "Chargement de la scène…"; racine.append(etat);
  const etiquette = document.createElement("span"); etiquette.className = "cote3d"; etiquette.hidden = true; calque.append(etiquette);

  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(rendu).fromScene(new RoomEnvironment(), 0.04).texture;
  const camera = new THREE.PerspectiveCamera(36, 1, 0.05, 80);
  const controles = new OrbitControls(camera, rendu.domElement);
  controles.enableDamping = true; controles.dampingFactor = 0.12; controles.maxPolarAngle = Math.PI * 0.495; controles.minDistance = 1.5; controles.maxDistance = 16;

  const soleil = new THREE.DirectionalLight(0xfff3dc, 2.6); soleil.castShadow = true; soleil.shadow.mapSize.set(2048, 2048);
  const c = soleil.shadow.camera; c.left = -6; c.right = 6; c.top = 6; c.bottom = -6; c.near = 1; c.far = 30; soleil.shadow.bias = -0.0003; soleil.shadow.normalBias = 0.02;
  scene.add(soleil, soleil.target);
  const lampe = new THREE.PointLight(0xffc27a, 0, 9, 1.6); lampe.position.set(0.4, 2.3, 1.2); lampe.castShadow = true; scene.add(lampe);

  const dalles = document.createElement("canvas"); dalles.width = dalles.height = 256;
  { const g = dalles.getContext("2d"); g.fillStyle = "#cfc7b6"; g.fillRect(0, 0, 256, 256); g.strokeStyle = "rgba(90,80,60,.28)"; g.lineWidth = 2; g.strokeRect(1, 1, 254, 254); g.beginPath(); g.moveTo(128, 0); g.lineTo(128, 256); g.moveTo(0, 128); g.lineTo(256, 128); g.stroke(); }
  const tex = new THREE.CanvasTexture(dalles); tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(16, 16); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const sol = new THREE.Mesh(new THREE.CircleGeometry(14, 72), new THREE.MeshStandardMaterial({ map: tex, roughness: 1 }));
  sol.rotation.x = -Math.PI / 2; sol.receiveShadow = true; scene.add(sol);

  const perso = construirePersonnage(); perso.position.set(2.7, 0, 0.3); perso.rotation.y = -0.6; scene.add(perso);
  const groupe = new THREE.Group(); scene.add(groupe);
  const marque = new THREE.Box3Helper(new THREE.Box3(), 0x3555d6); marque.visible = false; marque.material.depthTest = false; marque.renderOrder = 5; scene.add(marque);

  const api = { surSelection: null, stats: { triangles: 0, objets: 0, parType: {} }, selection: null };
  let sale = true, instances = [], anim = null, selectionne = null;
  const visible = () => racine.offsetWidth > 0 && racine.offsetHeight > 0;
  const demander = () => { sale = true; };

  const VUES = {
    ensemble: { pos: [3.1, 2.3, 4.3], cible: [0.5, 0.5, 0.3], fov: 36 },
    joueur: { pos: [0.6, 1.65, 4.3], cible: [0.4, 0.95, 0], fov: 58 },
  };
  api.vue = (nom, direct = false) => {
    const v = VUES[nom]; const depart = { p: camera.position.clone(), t: controles.target.clone(), f: camera.fov };
    const arrivee = { p: new THREE.Vector3(...v.pos), t: new THREE.Vector3(...v.cible), f: v.fov };
    if (direct) { camera.position.copy(arrivee.p); controles.target.copy(arrivee.t); camera.fov = arrivee.f; camera.updateProjectionMatrix(); controles.update(); demander(); return; }
    anim = { depart, arrivee, t0: performance.now(), duree: 650 }; demander();
  };

  const LUMIERES = {
    jour: { soleil: [0xfff3dc, 2.6, 40, 50], env: 0.6, lampe: 0 },
    soir: { soleil: [0xff9a55, 1.7, 250, 11], env: 0.16, lampe: 0 },
    interieur: { soleil: [0xaab8ff, 0.25, 40, 40], env: 0.12, lampe: 22 },
  };
  api.lumiere = nom => {
    const l = LUMIERES[nom]; soleil.color.set(l.soleil[0]); soleil.intensity = l.soleil[1];
    const d = THREE.MathUtils.degToRad(l.soleil[2]), h = THREE.MathUtils.degToRad(l.soleil[3]), R = 14;
    soleil.position.set(Math.sin(d) * Math.cos(h) * R, Math.sin(h) * R, Math.cos(d) * Math.cos(h) * R);
    scene.environmentIntensity = l.env; lampe.intensity = l.lampe; demander();
  };

  api.charger = async disposition => {
    etat.hidden = false; instances = []; groupe.clear(); api.stats = { triangles: 0, objets: 0, parType: {} };
    for (const o of disposition) {
      const gltf = await chargerGlb(o.url), mes = mesurer(gltf);
      api.stats.parType[o.id] = { nom: o.nom, n: o.instances.length, hauteur: mes.taille.y, triangles: mes.triangles };
      for (const it of o.instances) {
        const g = gltf.scene.clone(true); g.position.set(it.x, it.y || 0, it.z); g.rotation.y = it.ry || 0; if (it.s) g.scale.setScalar(it.s);
        g.traverse(m => { if (m.isMesh) { m.castShadow = m.receiveShadow = true; } });
        g.userData = { id: o.id, nom: o.nom }; groupe.add(g); instances.push(g);
        api.stats.triangles += mes.triangles; api.stats.objets++;
      }
    }
    etat.hidden = true; demander();
  };

  api.selectionner = id => {
    selectionne = id; api.selection = id;
    const ens = instances.filter(g => g.userData.id === id);
    if (!id || !ens.length) { marque.visible = false; etiquette.hidden = true; demander(); return; }
    const b = new THREE.Box3(); ens.forEach(g => b.expandByObject(g));
    marque.box.copy(b); marque.visible = true; etiquette.textContent = ens[0].userData.nom + (ens.length > 1 ? " ×" + ens.length : ""); etiquette.hidden = false;
    etiquette.userData = { pos: b.getCenter(new THREE.Vector3()).setY(b.max.y + 0.08) }; demander();
  };

  const ray = new THREE.Raycaster(); let depart = null;
  rendu.domElement.addEventListener("pointerdown", e => { depart = { x: e.clientX, y: e.clientY }; anim = null; });
  rendu.domElement.addEventListener("pointerup", e => {
    if (!depart) return; const bouge = Math.hypot(e.clientX - depart.x, e.clientY - depart.y); depart = null; if (bouge > 7) return;
    const r = rendu.domElement.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const hit = ray.intersectObjects(instances, true)[0]; let n = hit && hit.object;
    while (n && !(n.userData && n.userData.id)) n = n.parent;
    api.selectionner(n ? n.userData.id : null); api.surSelection && api.surSelection(n ? n.userData : null);
  });

  function redimensionner() { const w = racine.clientWidth, h = racine.clientHeight; if (!w || !h) return; rendu.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); demander(); }
  new ResizeObserver(redimensionner).observe(racine);
  const v = new THREE.Vector3();
  function dessiner() {
    rendu.render(scene, camera);
    if (!etiquette.hidden && etiquette.userData.pos) {
      v.copy(etiquette.userData.pos).project(camera);
      etiquette.style.transform = `translate(${((v.x * 0.5 + 0.5) * racine.clientWidth).toFixed(1)}px,${((-v.y * 0.5 + 0.5) * racine.clientHeight).toFixed(1)}px)`;
    }
  }
  (function boucle() {
    requestAnimationFrame(boucle); if (!visible()) return;
    if (anim) {
      const k = Math.min(1, (performance.now() - anim.t0) / anim.duree), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      camera.position.lerpVectors(anim.depart.p, anim.arrivee.p, e); controles.target.lerpVectors(anim.depart.t, anim.arrivee.t, e);
      camera.fov = anim.depart.f + (anim.arrivee.f - anim.depart.f) * e; camera.updateProjectionMatrix(); if (k >= 1) anim = null; sale = true;
    }
    const bouge = controles.update(); if (bouge || sale) { dessiner(); sale = false; }
  })();
  controles.addEventListener("change", demander);
  api.lumiere("jour"); api.vue("ensemble", true);
  return api;
}
