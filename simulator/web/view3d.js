// 3D / top view of the table, robot, path and steps (three.js). Scene units: meters, Z up,
// field coordinates as on the robot: x 0..3, y 0..2, angle 0 = +x, positive = counter-clockwise.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { GLTFLoader } from './vendor/loaders/GLTFLoader.js';

const SIDE_COLOR = { plava: 0x2f7fc1, zuta: 0xf7b500 };
// boje putanje po koraku (svaki korak svoja, pa se vidi gde se jedan završava a drugi počinje)
const STEP_COLORS = [0x4cc9f0, 0xf72585, 0xb5e48c, 0xffd166, 0x9d4edd, 0xff8c42, 0x06d6a0, 0xef476f];

// Traka (ribbon) duž putanje, širine w (m), jer WebGL ne crta debele linije. Boja po temenu.
// Vraća geometriju sa 6 temena po segmentu, pa drawRange(0, 6 * i) crta do frejma i.
function ribbon(pts, cols, w, z) {
  const pos = [], col = [];
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
    let dx = x1 - x0, dy = y1 - y0;
    const L = Math.hypot(dx, dy) || 1;
    const nx = -dy / L * w / 2, ny = dx / L * w / 2;
    const a = [x0 + nx, y0 + ny, z], b = [x0 - nx, y0 - ny, z], c = [x1 + nx, y1 + ny, z], d = [x1 - nx, y1 - ny, z];
    pos.push(...a, ...b, ...c, ...b, ...d, ...c);
    const k = cols[i];
    for (let j = 0; j < 6; j++) col.push(k.r, k.g, k.b);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  return g;
}

function textSprite(text, color = '#fff', size = 0.06, bg = 'rgba(0,0,0,0.55)') {
  const c = document.createElement('canvas');
  const fs = 48, pad = 10;
  const ctx = c.getContext('2d');
  ctx.font = `600 ${fs}px system-ui, sans-serif`;
  const w = Math.ceil(ctx.measureText(text).width) + pad * 2;
  c.width = w; c.height = fs + pad * 2;
  ctx.font = `600 ${fs}px system-ui, sans-serif`;
  ctx.fillStyle = bg; ctx.beginPath(); ctx.roundRect(0, 0, c.width, c.height, 12); ctx.fill();
  ctx.fillStyle = color; ctx.textBaseline = 'middle'; ctx.fillText(text, pad, c.height / 2 + 2);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false }));
  s.scale.set(size * c.width / c.height, size, 1);
  s.renderOrder = 10;
  return s;
}

function tableTexture(field) {
  const S = 0.5;                                   // px per mm
  const c = document.createElement('canvas');
  c.width = field.w * S; c.height = field.h * S;
  const g = c.getContext('2d');
  g.fillStyle = '#2b3330'; g.fillRect(0, 0, c.width, c.height);
  // canvas y goes down, field y goes up: flip
  const R = (x0, y0, x1, y1) => [x0 * S, (field.h - y1) * S, (x1 - x0) * S, (y1 - y0) * S];
  for (const z of field.zones) {
    const [r, gg, b] = z.color;
    g.fillStyle = `rgba(${r},${gg},${b},0.45)`; g.fillRect(...R(...z.rect));
    g.strokeStyle = `rgb(${r},${gg},${b})`; g.lineWidth = 6; g.strokeRect(...R(...z.rect));
  }
  for (let x = 0; x <= field.w; x += 100) {
    g.strokeStyle = x % 500 ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.18)'; g.lineWidth = x % 500 ? 1 : 2;
    g.beginPath(); g.moveTo(x * S, 0); g.lineTo(x * S, c.height); g.stroke();
  }
  for (let y = 0; y <= field.h; y += 100) {
    g.strokeStyle = y % 500 ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.18)'; g.lineWidth = y % 500 ? 1 : 2;
    g.beginPath(); g.moveTo(0, (field.h - y) * S); g.lineTo(c.width, (field.h - y) * S); g.stroke();
  }
  g.fillStyle = 'rgba(255,255,255,0.45)'; g.font = '22px system-ui, sans-serif';
  for (let x = 500; x < field.w; x += 500) g.fillText(String(x), x * S + 4, c.height - 6);
  for (let y = 500; y < field.h; y += 500) g.fillText(String(y), 6, (field.h - y) * S - 6);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

function stoneTexture() {
  // karton sa ArUco oznakom (vrednost 13 iz pravila; ovde samo izgled, ne prava oznaka)
  const c = document.createElement('canvas'); c.width = 320; c.height = 110;
  const g = c.getContext('2d');
  g.fillStyle = '#c79a5b'; g.fillRect(0, 0, 320, 110);
  g.fillStyle = 'rgba(0,0,0,0.08)'; for (let i = 0; i < 12; i++) g.fillRect(i * 27, 0, 2, 110);
  g.fillStyle = '#fff'; g.fillRect(122, 18, 76, 76);
  g.fillStyle = '#000'; g.fillRect(128, 24, 64, 64);
  g.fillStyle = '#fff';
  for (const [x, y] of [[1, 1], [3, 1], [2, 2], [1, 3], [4, 3], [3, 4], [2, 4]]) g.fillRect(128 + x * 10.7, 24 + y * 10.7, 10.7, 10.7);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export class FieldView {
  constructor(el, info) {
    this.el = el;
    this.field = info.field;
    this.profile = info.profile;
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    el.appendChild(this.renderer.domElement);
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x12151a);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4);
    sun.position.set(1, -2, 4);
    this.scene.add(sun);

    const W = this.field.w / 1000, H = this.field.h / 1000;
    this.center = new THREE.Vector3(W / 2, H / 2, 0);
    this.persp = new THREE.PerspectiveCamera(40, 1, 0.01, 50);
    this.persp.up.set(0, 0, 1);
    this.persp.position.set(W / 2, -1.7, 2.5);
    this.ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 50);
    this.ortho.position.set(W / 2, H / 2, 10);
    this.ortho.up.set(0, 1, 0);
    this.camera = this.persp;
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.copy(this.center);

    this._buildTable(W, H);
    this.dyn = new THREE.Group();                  // everything that belongs to one run
    this.scene.add(this.dyn);
    this.robot = this._robot(SIDE_COLOR.zuta);
    this.scene.add(this.robot);
    this.ghost = this._ghost();
    this.scene.add(this.ghost);
    this.robot.visible = this.ghost.visible = false;
    this.cmpGroup = new THREE.Group();             // reference run (compare): path + ghost robot
    this.scene.add(this.cmpGroup);
    this.cmp = null;
    this.elGroup = new THREE.Group();              // elementi igre (kamenolomi)
    this.scene.add(this.elGroup);
    this.oppGroup = new THREE.Group();             // editable opponents (independent of the run)
    this.scene.add(this.oppGroup);
    this.prevGroup = new THREE.Group();            // nacrt iz editora (plan S7)
    this.scene.add(this.prevGroup);
    this.cursorGroup = new THREE.Group();          // krst za x, y iz reda sa kursorom (plan S8)
    this.scene.add(this.cursorGroup);
    this.onPreviewClick = null; this.onAltPick = null;
    this.opponents = []; this.oppSel = -1; this.drag = null;
    this.onOppSelect = null; this.onOppMove = null;
    this.elements = []; this.elSel = -1; this.onElSelect = null; this.onElMove = null;   // kamenolomi (plan E3)

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.onHover = null;
    this.renderer.domElement.addEventListener('mousemove', e => this._hover(e));
    this.renderer.domElement.addEventListener('mouseleave', () => this.onHover && this.onHover(null));
    const cv = this.renderer.domElement;
    cv.addEventListener('pointerdown', e => this._down(e));
    cv.addEventListener('pointermove', e => this._dragMove(e));
    cv.addEventListener('pointerup', e => this._up(e));
    this.renderer.domElement.addEventListener('dblclick', e => {
      const p = this._pick(e); if (p && this.onPick) this.onPick(p);
    });
    // klik: Alt+klik = tačka sa mape u editor; klik na tačku nacrta = skok na red u kodu
    cv.addEventListener('click', e => {
      if (e.altKey) { const p = this._pick(e); if (p && this.onAltPick) { e.preventDefault(); this.onAltPick(p); } return; }
      const line = this._hitPreview(e);
      if (line && this.onPreviewClick) this.onPreviewClick(line);
    });
    new ResizeObserver(() => this.resize()).observe(el);
    this.resize();
    this.follow = false;
    const loop = () => { this._tick(); requestAnimationFrame(loop); };
    loop();
  }

  _buildTable(W, H) {
    this.gridTex = tableTexture(this.field);
    const top = new THREE.Mesh(new THREE.PlaneGeometry(W, H),
      new THREE.MeshStandardMaterial({ map: this.gridTex, roughness: 0.95 }));
    // izgled stola iz pravila 2027 (dodatak G.1, slika 8), ako postoji; inače mreža
    new THREE.TextureLoader().load(this.field.image || 'table2027.jpg', tex => {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
      this.rulesTex = tex;
      if (this.useRules !== false) this.setTableLook('rules');
    }, undefined, () => { this.rulesTex = null; });
    top.position.set(W / 2, H / 2, 0);
    this.table = top;
    this.scene.add(top);
    const t = this.field.border_t / 1000, h = this.field.border_h / 1000;
    const mat = new THREE.MeshStandardMaterial({ color: 0x59606b, roughness: 0.8 });
    const box = (w, d, x, y) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, d, h), mat);
      m.position.set(x, y, h / 2); this.scene.add(m);
    };
    box(W + 2 * t, t, W / 2, -t / 2); box(W + 2 * t, t, W / 2, H + t / 2);
    box(t, H, -t / 2, H / 2); box(t, H, W + t / 2, H / 2);
    const under = new THREE.Mesh(new THREE.BoxGeometry(W + 2 * t, H + 2 * t, 0.03),
      new THREE.MeshStandardMaterial({ color: 0x1d2228 }));
    under.position.set(W / 2, H / 2, -0.016);
    this.scene.add(under);
    // axes at origin
    const ax = (dir, color) => this.scene.add(new THREE.ArrowHelper(dir, new THREE.Vector3(0, 0, 0.002), 0.25, color, 0.05, 0.03));
    ax(new THREE.Vector3(1, 0, 0), 0xff5555); ax(new THREE.Vector3(0, 1, 0), 0x55dd55);
    const lx = textSprite('x', '#ff7777', 0.05, 'rgba(0,0,0,0)'); lx.position.set(0.29, 0, 0.02); this.scene.add(lx);
    const ly = textSprite('y', '#77ee77', 0.05, 'rgba(0,0,0,0)'); ly.position.set(0, 0.29, 0.02); this.scene.add(ly);
    // lenjir uvek vidljiv (i preko slike pravila): brojevi na 500 mm van stola, crtice na 100 mm na ivici
    const rule = new THREE.Group();
    const tick = [];
    for (let x = 0; x <= this.field.w; x += 100) {
      const big = x % 500 === 0, l = big ? 0.05 : 0.025;
      tick.push(x / 1000, -t, h + 0.001, x / 1000, -t - l, h + 0.001);
      if (big) { const s = textSprite(String(x), '#c8d0da', 0.045, 'rgba(0,0,0,0)'); s.position.set(x / 1000, -t - 0.09, h); rule.add(s); }
    }
    for (let y = 0; y <= this.field.h; y += 100) {
      const big = y % 500 === 0, l = big ? 0.05 : 0.025;
      tick.push(-t, y / 1000, h + 0.001, -t - l, y / 1000, h + 0.001);
      if (big) { const s = textSprite(String(y), '#c8d0da', 0.045, 'rgba(0,0,0,0)'); s.position.set(-t - 0.12, y / 1000, h); rule.add(s); }
    }
    const tg = new THREE.BufferGeometry(); tg.setAttribute('position', new THREE.Float32BufferAttribute(tick, 3));
    rule.add(new THREE.LineSegments(tg, new THREE.LineBasicMaterial({ color: 0xc8d0da })));
    const o = textSprite('0, 0', '#ffffff', 0.05); o.position.set(-0.07, -0.07, h + 0.02); rule.add(o);
    const xl = textSprite('x (mm) →', '#ff9b9b', 0.05, 'rgba(0,0,0,0)'); xl.position.set(W / 2, -t - 0.17, h); rule.add(xl);
    const yl = textSprite('y (mm) ↑', '#9bee9b', 0.05, 'rgba(0,0,0,0)'); yl.position.set(-t - 0.13, H / 2 + 0.25, h); rule.add(yl);
    this.scene.add(rule);
  }

  setTableLook(look) {                             // 'rules' (slika iz pravila) ili 'grid'
    this.useRules = look === 'rules';
    const m = this.table.material;
    m.map = this.useRules && this.rulesTex ? this.rulesTex : this.gridTex;
    m.needsUpdate = true;
  }

  _robot(color) {
    const b = this.profile.body, d = this.profile.drive;
    const L = b.length / 1000, Wd = b.width / 1000, Hh = b.height / 1000, off = (b.axle_offset || 0) / 1000;
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(L, Wd, Hh),
      new THREE.MeshStandardMaterial({ color, transparent: true, opacity: 0.35, roughness: 0.6 }));
    body.position.set(off, 0, Hh / 2);
    g.add(body);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(body.geometry),
      new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.6 }));
    edges.position.copy(body.position);
    g.add(edges);
    const plate = new THREE.Mesh(new THREE.BoxGeometry(L, Wd, 0.012), new THREE.MeshStandardMaterial({ color }));
    plate.position.set(off, 0, 0.04);
    g.add(plate);
    const r = d.wheel_diameter / 2000, ww = d.wheel_width / 1000, tr = d.wheel_track / 2000;
    const wm = new THREE.MeshStandardMaterial({ color: 0x111111 });
    for (const s of [1, -1]) {
      const w = new THREE.Mesh(new THREE.CylinderGeometry(r, r, ww, 24), wm);
      w.position.set(0, s * tr, r);
      g.add(w);
    }
    // heading arrow on top
    const shape = new THREE.Shape();
    shape.moveTo(L / 2 + off, 0); shape.lineTo(off - L * 0.15, Wd * 0.22); shape.lineTo(off - L * 0.15, -Wd * 0.22);
    const arrow = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({ color: 0xffffff }));
    arrow.position.z = Hh + 0.002;
    g.add(arrow);
    g.userData.body = body; g.userData.plate = plate;
    g.add(this._irRays());
    const file = this.profile.model && this.profile.model.file;
    if (file) {                                    // CAD model (simulator/tools/cad_to_glb.py): umesto ploče i točkova
      new GLTFLoader().load(file, gltf => {
        g.add(gltf.scene);
        plate.visible = false;
        for (const c of g.children) if (c.geometry && c.geometry.type === 'CylinderGeometry') c.visible = false;
        body.material.opacity = 0.16;
        this.cadLoaded = true;
      }, undefined, err => console.warn('model robota:', file, err));
    }
    return g;
  }

  // IR senzori (isti raspored kao plant.sensors(): napred/nazad x levo/desno x dole/gore): zrak do dometa,
  // crven do pogotka. Deo robota, pa ga prati.
  _irRays() {                                      // senzori iz profila (server: info.profile.ir_sensors, F1..B4)
    const ir = this.profile.ir || {};
    const range = (ir.range || 250) / 1000;
    const grp = new THREE.Group();
    this.irRays = [];
    for (const sn of this.profile.ir_sensors || []) {
      const d = sn.d, s = sn.y / 1000, z = sn.z / 1000, x0 = sn.x / 1000;
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute([x0, s, z, x0 + d * range, s, z], 3));
      const m = new THREE.LineBasicMaterial({ color: 0xaab4c0, transparent: true, opacity: 0.35, depthTest: false });
      const line = new THREE.Line(geo, m);
      line.renderOrder = 4;
      const dot = new THREE.Mesh(new THREE.CircleGeometry(0.012, 12), new THREE.MeshBasicMaterial({ color: 0xff4d4d, depthTest: false }));
      dot.position.set(x0, s, z); dot.visible = false; dot.renderOrder = 4;
      grp.add(line, dot);
      const lbl = textSprite(sn.name, '#c8d0da', 0.025, 'rgba(0,0,0,0)');
      lbl.position.set(x0 + d * 0.03, s, z + 0.01);
      grp.add(lbl);
      this.irRays.push({ line, dot, x0, d, s, z, range, name: sn.name });
    }
    this.irGroup = grp;
    return grp;
  }

  setIr(hits, mask = 0xFF) {                       // hits: [mm po senzoru, -1 = ništa] ili null; mask: uključeni
    if (!this.irRays) return;
    this.irRays.forEach((r, k) => {
      const off = !(mask & (1 << k));                // isključen (ir_off): i dalje meri, ne zaustavlja; crta se tamno
      const h = hits && hits[k] >= 0 ? hits[k] / 1000 : null;
      const len = h == null ? r.range : h;
      const a = r.line.geometry.attributes.position;
      a.setX(1, r.x0 + r.d * len); a.needsUpdate = true;
      r.line.material.color.setHex(off ? 0x55606d : h == null ? 0xaab4c0 : 0xff4d4d);
      r.line.material.opacity = off ? 0.25 : h == null ? 0.35 : 1;
      r.dot.visible = h != null;
      if (h != null) r.dot.position.set(r.x0 + r.d * h, r.s, r.z);
    });
  }

  // Obod po ishodu (sivo = još nije, žuto = u toku, zeleno = OK, crveno = neuspeh), veličina, natpis.
  _updateMarks() {
    const t = this._t || 0, k = this.markerScale || 1, mode = this.labelMode || 'current';
    for (const g of (this.stepMarks ? this.stepMarks.children : [])) {
      const s = g.userData.step;
      const cur = s.t <= t && (s.end == null || s.end > t);
      g.userData.rim.material.color.setHex(s.t > t ? 0x55606d : cur ? 0xffb547 : (s.ok ? 0x3ecf8e : 0xff5c5c));
      const hi = s.idx === this._hiStep;
      g.scale.setScalar(k * (hi ? 1.6 : cur ? 1.25 : 1));
      g.userData.lbl.visible = mode === 'all' || hi || (mode === 'current' && cur);
    }
  }

  highlightStep(idx) { this._hiStep = idx; this._updateMarks(); }     // hover: timeline ili oznaka na mapi

  setLabelMode(m) { this.labelMode = m; this._updateMarks(); }

  _hitStep(e) {
    if (!this.stepMarks || !this.stepMarks.visible || !this.stepMarks.children.length) return 0;
    const r = this.renderer.domElement.getBoundingClientRect();
    this.mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const hit = this.raycaster.intersectObjects(this.stepMarks.children.map(g => g.userData.hit))[0];
    return hit ? hit.object.parent.userData.step.idx : 0;
  }

  setShowIr(on) { if (this.irGroup) this.irGroup.visible = on; }

  setMarkerScale(k) { this.markerScale = k; this._updateMarks(); }   // veličina oznaka koraka (0.7 / 1 / 1.5)

  _ghost() {
    const b = this.profile.body;
    const L = b.length / 1000, Wd = b.width / 1000, off = (b.axle_offset || 0) / 1000;
    const geo = new THREE.EdgesGeometry(new THREE.BoxGeometry(L, Wd, 0.02));
    const m = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0xff9f43 }));
    m.position.set(off, 0, 0.01);
    const g = new THREE.Group();
    g.add(m);
    const nose = new THREE.Mesh(new THREE.CircleGeometry(0.012, 12), new THREE.MeshBasicMaterial({ color: 0xff9f43 }));
    nose.position.set(L / 2 + off, 0, 0.012);
    g.add(nose);
    return g;
  }

  // ---------------- one run ----------------

  _dispose(obj) {
    obj.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      for (const m of [].concat(o.material || [])) { if (m.map) m.map.dispose(); m.dispose(); }
    });
    obj.clear();
  }

  setRun(run) {
    this.run = run;
    this._dispose(this.dyn);
    const c = run.cols, n = c.t.length;
    const col = SIDE_COLOR[run.meta.side] || 0xffffff;
    this.robot.userData.body.material.color.setHex(col);
    this.robot.userData.plate.material.color.setHex(col);
    this.robot.visible = n > 0;
    const pts = [], opts = [];
    this.odomSeg = [];                             // segment k ends at frame odomSeg[k]
    for (let i = 0; i < n; i++) {
      pts.push(c.x[i] / 1000, c.y[i] / 1000, 0.004);
      // odometry jumps on SET_POSE: draw it as separate segments, without the jump
      if (i > 0 && Math.hypot(c.ox[i] - c.ox[i - 1], c.oy[i] - c.oy[i - 1]) < 100) {
        opts.push(c.ox[i - 1] / 1000, c.oy[i - 1] / 1000, 0.006, c.ox[i] / 1000, c.oy[i] / 1000, 0.006);
        this.odomSeg.push(i);
      }
    }
    const mk = (arr, mat) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3));
      const l = new THREE.Line(g, mat); this.dyn.add(l); return l;
    };
    // putanja: traka 14 mm, boja po koraku; cela bleda, pređeni deo puna
    const xy = [], cols = [];
    let si = -1;
    const stepAtT = run.steps.map(s => s.t);
    for (let i = 0; i < n; i++) {
      xy.push([c.x[i] / 1000, c.y[i] / 1000]);
      while (si + 1 < stepAtT.length && stepAtT[si + 1] <= c.t[i]) si++;
      cols.push(new THREE.Color(si < 0 ? 0xffffff : STEP_COLORS[si % STEP_COLORS.length]));
    }
    const rg = ribbon(xy, cols, 0.014, 0.004);
    this.pathAll = new THREE.Mesh(rg, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false }));
    this.pathDone = new THREE.Mesh(rg.clone(), new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide }));
    this.pathDone.position.z = 0.0005;
    this.dyn.add(this.pathAll, this.pathDone);
    const og = new THREE.BufferGeometry();
    og.setAttribute('position', new THREE.Float32BufferAttribute(opts, 3));
    this.odomPath = new THREE.LineSegments(og, new THREE.LineBasicMaterial({ color: 0xff9f43, transparent: true, opacity: 0.8 }));
    this.dyn.add(this.odomPath);
    // steps: markers where each step started, colored by result
    this.stepMarks = new THREE.Group(); this.dyn.add(this.stepMarks);
    // Koraci na mapi (plan E1): JEDNA mala oznaka po koraku koji pomera robota, na mestu gde ga korak vodi
    // (cilj GOTO, ili gde je robot bio na kraju MOVE). Okreti i aktuatori nemaju oznaku (vide se na timeline-u).
    // Boja = boja koraka (ista kao putanja i traka na timeline-u); obod = ishod. Natpis: tekući korak, hover ili
    // "all" (Show ▾ -> labels). Iznad svega (depthTest false).
    const over = o => { o.renderOrder = 6; if (o.material) o.material.depthTest = false; return o; };
    this.targets = this.stepMarks;                     // jedna grupa (stari prekidač "targets" je skriva)
    for (const s of run.steps) {
      let px, py, tth = null;
      if (s.target) [px, py, tth] = s.target;
      else {
        const i0 = run.frameAt(s.t), i1 = run.frameAt(s.end != null ? s.end : run.duration);
        if (Math.hypot(c.x[i1] - c.x[i0], c.y[i1] - c.y[i0]) < 30) continue;   // nije se pomerio
        [px, py] = [c.x[i1], c.y[i1]];
      }
      const sc = STEP_COLORS[(s.idx - 1 + STEP_COLORS.length) % STEP_COLORS.length];
      const rim = over(new THREE.Mesh(new THREE.RingGeometry(0.019, 0.026, 28),
        new THREE.MeshBasicMaterial({ color: 0x55606d, side: THREE.DoubleSide })));
      const dot = over(new THREE.Mesh(new THREE.CircleGeometry(0.019, 24), new THREE.MeshBasicMaterial({ color: sc })));
      const num = textSprite(String(s.idx), '#000', 0.03, 'rgba(0,0,0,0)');
      num.position.set(0, 0, 0.01);
      const grp = new THREE.Group(); grp.add(rim, dot, num);
      if (tth != null) {                               // završni ugao: tanka strelica
        const sh = new THREE.Shape(); sh.moveTo(0.06, 0); sh.lineTo(0.04, 0.012); sh.lineTo(0.04, -0.012);
        const head = over(new THREE.Mesh(new THREE.ShapeGeometry(sh), new THREE.MeshBasicMaterial({ color: sc })));
        head.rotation.z = tth * Math.PI / 180; grp.add(head);
      }
      const name = (s.name || '').length > 26 ? s.name.slice(0, 25) + '…' : (s.name || '');
      const lbl = textSprite(`${s.idx}. ${name}`, '#fff', 0.04);
      lbl.position.set(0, 0.055, 0.03); lbl.visible = false;
      grp.add(lbl);
      grp.position.set(px / 1000, py / 1000, 0.008);
      grp.userData = { step: s, rim, dot, lbl, hit: dot };
      this.stepMarks.add(grp);
    }
    if (this.markerScale) this.setMarkerScale(this.markerScale);
    this.setFrame(this.frame && this.frame < n ? this.frame : 0);
  }

  // ---------------- nacrt iz editora (plan S7) ----------------

  setPreview(p) {                                  // p: odgovor /api/preview ili null
    this._dispose(this.prevGroup);
    this.prevItems = [];
    if (!p || !p.cmds) return;
    const seg = [];
    for (const c of p.cmds) if (c.x0 !== c.x1 || c.y0 !== c.y1) seg.push(c.x0 / 1000, c.y0 / 1000, 0.02, c.x1 / 1000, c.y1 / 1000, 0.02);
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(seg, 3));
    const lines = new THREE.LineSegments(g, new THREE.LineDashedMaterial({ color: 0xe0aaff, dashSize: 0.03, gapSize: 0.02, depthTest: false }));
    lines.computeLineDistances(); lines.renderOrder = 7;
    this.prevGroup.add(lines);
    if (p.start) {
      const s = textSprite('START', '#e0aaff', 0.04); s.position.set(p.start[0] / 1000, p.start[1] / 1000 - 0.06, 0.03); this.prevGroup.add(s);
    }
    let k = 0;
    for (const c of p.cmds) {
      if (!['goto', 'move', 'pose'].includes(c.kind)) continue;
      k++;
      const grp = new THREE.Group();
      const dot = new THREE.Mesh(new THREE.CircleGeometry(0.03, 24), new THREE.MeshBasicMaterial({ color: 0xe0aaff, depthTest: false, transparent: true, opacity: 0.85 }));
      dot.renderOrder = 8; dot.userData.line = c.line;
      const num = textSprite(String(k), '#2a0040', 0.04, 'rgba(0,0,0,0)'); num.position.z = 0.01;
      grp.add(dot, num);
      const tth = c.target ? c.target[2] : null;
      if (tth != null) {
        const sh = new THREE.Shape(); sh.moveTo(0.09, 0); sh.lineTo(0.05, 0.022); sh.lineTo(0.05, -0.022);
        const a = new THREE.Mesh(new THREE.ShapeGeometry(sh), new THREE.MeshBasicMaterial({ color: 0xe0aaff, depthTest: false }));
        a.renderOrder = 8; a.rotation.z = tth * Math.PI / 180; grp.add(a);
      }
      grp.position.set(c.x1 / 1000, c.y1 / 1000, 0.02);
      grp.userData = { line: c.line, dot };
      this.prevGroup.add(grp);
      this.prevItems.push(grp);
    }
    this.highlightPreview(this._prevHi || 0);
  }

  setShowPreview(on) { this.prevGroup.visible = on; }

  highlightPreview(line) {                         // red sa kursorom: njegove tačke veće i žute
    this._prevHi = line;
    for (const g of this.prevItems || []) {
      const on = line && g.userData.line === line;
      g.scale.setScalar(on ? 1.5 : 1);
      g.userData.dot.material.color.setHex(on ? 0xffd166 : 0xe0aaff);
    }
  }

  _hitPreview(e) {
    if (!this.prevItems || !this.prevItems.length || !this.prevGroup.visible) return null;
    const r = this.renderer.domElement.getBoundingClientRect();
    this.mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const hit = this.raycaster.intersectObjects(this.prevItems.map(g => g.userData.dot))[0];
    return hit ? hit.object.userData.line : null;
  }

  // Krst za tačku iz reda sa kursorom: isprekidane linije do leve i donje ivice i natpis sa x, y (plan S8).
  setCursorPoint(pt, label) {
    this._dispose(this.cursorGroup);
    if (!pt) return;
    const [x, y] = [pt[0] / 1000, pt[1] / 1000], z = 0.025;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([0, y, z, x, y, z, x, 0, z, x, y, z], 3));
    const l = new THREE.LineSegments(g, new THREE.LineDashedMaterial({ color: 0xffd166, dashSize: 0.025, gapSize: 0.015, depthTest: false }));
    l.computeLineDistances(); l.renderOrder = 9;
    const c = new THREE.BufferGeometry();
    c.setAttribute('position', new THREE.Float32BufferAttribute([x - 0.06, y, z, x + 0.06, y, z, x, y - 0.06, z, x, y + 0.06, z], 3));
    const cross = new THREE.LineSegments(c, new THREE.LineBasicMaterial({ color: 0xffd166, depthTest: false })); cross.renderOrder = 9;
    const s = textSprite(label, '#ffd166', 0.05); s.position.set(x, y + 0.1, 0.05);
    this.cursorGroup.add(l, cross, s);
  }

  // ---------------- opponents (editable, dragged with the mouse) ----------------

  setOpponents(list, sel = -1) {
    this.opponents = list; this.oppSel = sel;
    this._dispose(this.oppGroup);
    list.forEach((o, i) => {
      const h = (o.z || 350) / 1000;
      const geo = o.r ? new THREE.CylinderGeometry(o.r / 1000, o.r / 1000, h, 32) : new THREE.BoxGeometry(o.w / 1000, o.h / 1000, h);
      const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xc0392b, transparent: true, opacity: 0.75,
        emissive: i === sel ? 0x553300 : 0x000000 }));
      if (o.r) m.rotation.x = Math.PI / 2;
      const g = new THREE.Group();
      g.add(m);
      m.position.z = h / 2;
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: i === sel ? 0xffb547 : 0xff8080 }));
      edges.position.copy(m.position); edges.rotation.copy(m.rotation);
      g.add(edges);
      const l = textSprite(o.name || 'opponent', '#ffb3b3', 0.04); l.position.set(0, 0, h + 0.05); g.add(l);
      g.position.set(o.x / 1000, o.y / 1000, 0);
      g.rotation.z = (o.th || 0) * Math.PI / 180;
      m.userData.idx = i;
      this.oppGroup.add(g);
    });
  }

  _hitOpp(e) {
    const r = this.renderer.domElement.getBoundingClientRect();
    this.mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = this.oppGroup.children.map(g => g.children[0]);
    const hit = this.raycaster.intersectObjects(meshes)[0];
    return hit ? hit.object.userData.idx : -1;
  }

  _hitEl(e) {
    if (!this.elGroup.children.length || !this.editElements) return -1;
    const r = this.renderer.domElement.getBoundingClientRect();
    this.mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const hit = this.raycaster.intersectObjects(this.elGroup.children, true)[0];
    let o = hit && hit.object;
    while (o && o.userData.el == null) o = o.parent;
    return o ? o.userData.el : -1;
  }

  _down(e) {
    if (e.button !== 0 || e.altKey) return;
    let i = this._hitOpp(e), kind = 'opp';
    if (i < 0) { i = this._hitEl(e); kind = 'el'; }
    if (i < 0) return;
    const p = this._pick(e), o = kind === 'opp' ? this.opponents[i] : this.elements[i];
    if (!p) return;
    this.controls.enabled = false;
    this.drag = { kind, i, dx: o.x - p[0], dy: o.y - p[1], moved: false };
    this.renderer.domElement.setPointerCapture(e.pointerId);
    if (kind === 'opp' && this.onOppSelect) this.onOppSelect(i);
    if (kind === 'el' && this.onElSelect) this.onElSelect(i);
  }

  _dragMove(e) {
    if (!this.drag) return;
    const p = this._pick(e);
    if (!p) return;
    const d = this.drag, o = d.kind === 'opp' ? this.opponents[d.i] : this.elements[d.i];
    o.x = Math.round(Math.max(0, Math.min(this.field.w, p[0] + d.dx)) / 5) * 5;
    o.y = Math.round(Math.max(0, Math.min(this.field.h, p[1] + d.dy)) / 5) * 5;
    d.moved = true;
    const g = (d.kind === 'opp' ? this.oppGroup : this.elGroup).children[d.i];
    g.position.set(o.x / 1000, o.y / 1000, 0);
    if (d.kind === 'opp' && this.onOppMove) this.onOppMove(d.i, false);
    if (d.kind === 'el' && this.onElMove) this.onElMove(d.i, false);
  }

  _up(e) {
    if (!this.drag) return;
    const d = this.drag;
    this.drag = null;
    this.controls.enabled = true;
    if (d.moved && d.kind === 'opp' && this.onOppMove) this.onOppMove(d.i, true);
    if (d.moved && d.kind === 'el' && this.onElMove) this.onElMove(d.i, true);
  }

  setCompare(ref) {
    this._dispose(this.cmpGroup);
    this.cmp = ref;
    if (!ref || !ref.cols.t.length) return;
    const c = ref.cols, pts = [];
    for (let i = 0; i < c.t.length; i++) pts.push(c.x[i] / 1000, c.y[i] / 1000, 0.009);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    this.cmpGroup.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xc77dff })));
    const b = this.profile.body;
    const box = new THREE.BoxGeometry(b.length / 1000, b.width / 1000, b.height / 1000);
    const ghost = new THREE.LineSegments(new THREE.EdgesGeometry(box), new THREE.LineBasicMaterial({ color: 0xc77dff }));
    ghost.position.set((b.axle_offset || 0) / 1000, 0, b.height / 2000);
    this.cmpGhost = new THREE.Group();
    this.cmpGhost.add(ghost);
    this.cmpGroup.add(this.cmpGhost);
  }

  setCompareTime(t) {
    if (!this.cmp || !this.cmpGhost) return;
    const c = this.cmp.cols, i = this.cmp.frameAt(t);
    this.cmpGhost.visible = t >= 0 && t <= this.cmp.duration + 500;
    this.cmpGhost.position.set(c.x[i] / 1000, c.y[i] / 1000, 0);
    this.cmpGhost.rotation.z = c.th[i] * Math.PI / 180;
  }

  // editable: lista se menja mišem (izbor, prevlačenje); sel: izabran kamenolom (istaknut)
  setElements(list, { editable = false, sel = -1 } = {}) {
    this._dispose(this.elGroup);
    this.elements = list || []; this.editElements = editable; this.elSel = sel;
    if (!list || !list.length) return;
    const [L, Wd, H] = this.field.stone || [320, 110, 110];
    const tex = stoneTexture();
    const side = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9 });
    const plain = new THREE.MeshStandardMaterial({ color: 0xc79a5b, roughness: 0.9 });
    const geo = new THREE.BoxGeometry(L / 1000, Wd / 1000, H / 1000 * 0.98);
    const mats = [plain, plain, side, side, plain, plain];   // +x -x +y -y +z -z: oznaka na velikim stranama
    list.forEach((e, idx) => {
      const g = new THREE.Group();
      g.userData.el = idx;
      const n = e.stones == null ? 3 : e.stones;
      for (let k = 0; k < n; k++) {
        const m = new THREE.Mesh(geo, mats);
        m.position.z = (k + 0.5) * H / 1000;
        g.add(m);
      }
      if (idx === sel) {                              // izabran: okvir oko gomile
        const box = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(L / 1000 + 0.02, Wd / 1000 + 0.02, n * H / 1000 + 0.02)),
          new THREE.LineBasicMaterial({ color: 0xffb547 }));
        box.position.z = n * H / 2000; g.add(box);
      }
      g.position.set(e.x / 1000, e.y / 1000, 0);
      g.rotation.z = (e.th || 0) * Math.PI / 180;
      this.elGroup.add(g);
    });
  }

  setPose(f) {                                     // robot pose straight from a frame (live, between rebuilds)
    this.robot.visible = true;
    this.robot.position.set(f.x / 1000, f.y / 1000, 0);
    this.robot.rotation.z = f.th * Math.PI / 180;
    this.ghost.position.set(f.ox / 1000, f.oy / 1000, 0);
    this.ghost.rotation.z = f.oth * Math.PI / 180;
    this.setIr(f.irh || null, f.irm != null ? f.irm : 0xFF);
  }

  setVisibility({ odom, targets }) {
    this.showOdom = odom; this.showTargets = targets;
    if (this.odomPath) this.odomPath.visible = odom;
    if (this.targets) this.targets.visible = targets;
  }

  setFrame(i) {
    const run = this.run; if (!run) return;
    const c = run.cols, n = c.t.length;
    if (!n) return;
    i = Math.max(0, Math.min(n - 1, i));
    this.frame = i;
    this.robot.position.set(c.x[i] / 1000, c.y[i] / 1000, 0);
    this.robot.rotation.z = c.th[i] * Math.PI / 180;
    this.ghost.position.set(c.ox[i] / 1000, c.oy[i] / 1000, 0);
    this.ghost.rotation.z = c.oth[i] * Math.PI / 180;
    const diff = Math.hypot(c.x[i] - c.ox[i], c.y[i] - c.oy[i]) > 1 || Math.abs(c.th[i] - c.oth[i]) > 0.3;
    this.ghost.visible = this.showOdom !== false && diff;
    this.pathDone.geometry.setDrawRange(0, 6 * i);
    this.setIr(c.irh ? c.irh[i] : null, c.irm && c.irm[i] != null ? c.irm[i] : 0xFF);
    if (c.opp && c.opp[i] && !this.drag) {           // protivnici sa taktikom: gde su bili u tom trenutku
      c.opp[i].forEach(([x, y, th], j) => {
        const g = this.oppGroup.children[j];
        if (g) { g.position.set(x / 1000, y / 1000, 0); g.rotation.z = th * Math.PI / 180; }
      });
    }
    let k = 0, lo = 0, hi = this.odomSeg.length;          // segments ending at or before frame i
    while (lo < hi) { const m = (lo + hi) >> 1; if (this.odomSeg[m] <= i) lo = m + 1; else hi = m; }
    k = lo;
    this.odomPath.geometry.setDrawRange(0, 2 * k);
    const t = c.t[i];
    this._t = t;
    this._updateMarks();
  }

  // ---------------- camera ----------------

  setCamera(mode) {
    const W = this.field.w / 1000, H = this.field.h / 1000;
    this.controls.dispose();
    this.camera = mode === 'top' ? this.ortho : this.persp;
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    if (mode === 'top') {
      this.ortho.position.set(W / 2, H / 2 + 0.17, 10);   // sto malo niže: gornji kamenolomi ispod alatki
      this.controls.enableRotate = false;
      this.controls.screenSpacePanning = true;
    }
    this.controls.target.copy(this.center);
    if (mode === 'top') this.controls.target.y += 0.17;
    this._fitAspect = 0;
    this.resize();
  }

  resize() {
    const w = this.el.clientWidth || 1, h = this.el.clientHeight || 1;
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = w + 'px'; this.renderer.domElement.style.height = h + 'px';
    this.persp.aspect = w / h; this.persp.updateProjectionMatrix();
    if (Math.abs(w / h - (this._fitAspect || 0)) > 0.05) { this._fitAspect = w / h; this.fit(); }
    const W = this.field.w / 1000 + 0.2, H = this.field.h / 1000 + 0.62;   // + mesto za alatke iznad stola
    let hw = W / 2, hh = H / 2;
    if (w / h > W / H) hw = hh * w / h; else hh = hw * h / w;
    Object.assign(this.ortho, { left: -hw, right: hw, top: hh, bottom: -hh });
    this.ortho.updateProjectionMatrix();
  }

  fit() {                                         // perspective camera: whole table in view for this aspect
    if (this.camera !== this.persp) return;
    const W = this.field.w / 1000 + 0.3, H = this.field.h / 1000 + 0.3;
    const v = this.persp.fov * Math.PI / 180, hf = 2 * Math.atan(Math.tan(v / 2) * this.persp.aspect);
    const d = Math.max(3.4, (W / 2) / Math.tan(hf / 2) * 1.05, (H * 0.75) / Math.tan(v / 2));
    const dir = new THREE.Vector3(0, -2.7, 2.5).normalize();
    this.persp.position.copy(this.center).addScaledVector(dir, d);
    this.controls.target.copy(this.center);
  }

  _pick(e) {
    const r = this.renderer.domElement.getBoundingClientRect();
    this.mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const hit = this.raycaster.intersectObject(this.table)[0];
    return hit ? [hit.point.x * 1000, hit.point.y * 1000] : null;
  }

  _hover(e) {
    if (this.onHover) this.onHover(this._pick(e));
    const idx = this._hitStep(e);                   // oznaka koraka pod mišem: natpis
    if (idx !== (this._hoverStep || 0)) { this._hoverStep = idx; this.highlightStep(idx); }
  }

  _tick() {
    if (this.follow && this.robot.visible) {
      const p = this.robot.position;
      const d = new THREE.Vector3().subVectors(p, this.controls.target);
      this.controls.target.add(d.multiplyScalar(0.15));
      if (this.camera === this.persp) this.camera.position.add(d);
      else this.camera.position.set(this.controls.target.x, this.controls.target.y, 10);
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
