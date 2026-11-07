// 3D / top view of the table, robot, path and steps (three.js). Scene units: meters, Z up,
// field coordinates as on the robot: x 0..3, y 0..2, angle 0 = +x, positive = counter-clockwise.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

const SIDE_COLOR = { plava: 0x2f7fc1, zuta: 0xf7b500 };

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
    this.robot = this._robot(SIDE_COLOR.plava);
    this.scene.add(this.robot);
    this.ghost = this._ghost();
    this.scene.add(this.ghost);
    this.robot.visible = this.ghost.visible = false;
    this.oppGroup = new THREE.Group();             // editable opponents (independent of the run)
    this.scene.add(this.oppGroup);
    this.opponents = []; this.oppSel = -1; this.drag = null;
    this.onOppSelect = null; this.onOppMove = null;

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
    new ResizeObserver(() => this.resize()).observe(el);
    this.resize();
    this.follow = false;
    const loop = () => { this._tick(); requestAnimationFrame(loop); };
    loop();
  }

  _buildTable(W, H) {
    const top = new THREE.Mesh(new THREE.PlaneGeometry(W, H),
      new THREE.MeshStandardMaterial({ map: tableTexture(this.field), roughness: 0.95 }));
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
    return g;
  }

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
      if (o.material) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); }
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
    this.pathAll = mk(pts, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.18 }));
    this.pathDone = mk(pts, new THREE.LineBasicMaterial({ color: 0xffffff }));
    const og = new THREE.BufferGeometry();
    og.setAttribute('position', new THREE.Float32BufferAttribute(opts, 3));
    this.odomPath = new THREE.LineSegments(og, new THREE.LineBasicMaterial({ color: 0xff9f43, transparent: true, opacity: 0.8 }));
    this.dyn.add(this.odomPath);
    // steps: markers where each step started, colored by result
    this.stepMarks = new THREE.Group(); this.dyn.add(this.stepMarks);
    this.targets = new THREE.Group(); this.dyn.add(this.targets);
    for (const s of run.steps) {
      const i = run.frameAt(s.t);
      const m = new THREE.Mesh(new THREE.CircleGeometry(0.018, 20), new THREE.MeshBasicMaterial({ color: 0xffffff }));
      m.position.set(c.x[i] / 1000, c.y[i] / 1000, 0.008);
      const lbl = textSprite(String(s.idx), '#fff', 0.045);
      lbl.position.set(c.x[i] / 1000, c.y[i] / 1000, 0.06);
      const grp = new THREE.Group(); grp.add(m, lbl); grp.userData = { step: s, dot: m };
      this.stepMarks.add(grp);
      if (s.target) {                                    // GOTO target (field coordinates)
        const [tx, ty] = s.target;
        const ring = new THREE.Mesh(new THREE.RingGeometry(0.022, 0.03, 28),
          new THREE.MeshBasicMaterial({ color: 0x4aa3ff, side: THREE.DoubleSide }));
        ring.position.set(tx / 1000, ty / 1000, 0.007);
        const t = textSprite(`${s.idx}: ${Math.round(tx)}, ${Math.round(ty)}`, '#9cd0ff', 0.04);
        t.position.set(tx / 1000, ty / 1000 + 0.05, 0.05);
        const tg = new THREE.Group(); tg.add(ring, t); tg.userData = { step: s, ring };
        this.targets.add(tg);
      }
    }
    this.setFrame(this.frame && this.frame < n ? this.frame : 0);
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

  _down(e) {
    if (e.button !== 0) return;
    const i = this._hitOpp(e);
    if (i < 0) return;
    const p = this._pick(e), o = this.opponents[i];
    if (!p) return;
    this.controls.enabled = false;
    this.drag = { i, dx: o.x - p[0], dy: o.y - p[1], moved: false };
    this.renderer.domElement.setPointerCapture(e.pointerId);
    if (this.onOppSelect) this.onOppSelect(i);
  }

  _dragMove(e) {
    if (!this.drag) return;
    const p = this._pick(e);
    if (!p) return;
    const d = this.drag, o = this.opponents[d.i];
    o.x = Math.round(Math.max(0, Math.min(this.field.w, p[0] + d.dx)) / 5) * 5;
    o.y = Math.round(Math.max(0, Math.min(this.field.h, p[1] + d.dy)) / 5) * 5;
    d.moved = true;
    const g = this.oppGroup.children[d.i];
    g.position.set(o.x / 1000, o.y / 1000, 0);
    if (this.onOppMove) this.onOppMove(d.i, false);
  }

  _up(e) {
    if (!this.drag) return;
    const d = this.drag;
    this.drag = null;
    this.controls.enabled = true;
    if (d.moved && this.onOppMove) this.onOppMove(d.i, true);
  }

  setPose(f) {                                     // robot pose straight from a frame (live, between rebuilds)
    this.robot.visible = true;
    this.robot.position.set(f.x / 1000, f.y / 1000, 0);
    this.robot.rotation.z = f.th * Math.PI / 180;
    this.ghost.position.set(f.ox / 1000, f.oy / 1000, 0);
    this.ghost.rotation.z = f.oth * Math.PI / 180;
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
    this.pathDone.geometry.setDrawRange(0, i + 1);
    let k = 0, lo = 0, hi = this.odomSeg.length;          // segments ending at or before frame i
    while (lo < hi) { const m = (lo + hi) >> 1; if (this.odomSeg[m] <= i) lo = m + 1; else hi = m; }
    k = lo;
    this.odomPath.geometry.setDrawRange(0, 2 * k);
    const t = c.t[i];
    for (const g of this.stepMarks.children) {
      const s = g.userData.step;
      const col = s.t > t ? 0x55606d : (s.end == null || s.end > t) ? 0xffb547 : (s.ok ? 0x3ecf8e : 0xff5c5c);
      g.userData.dot.material.color.setHex(col);
    }
    for (const g of this.targets.children) {
      const s = g.userData.step;
      const active = s.t <= t && (s.end == null || s.end > t);
      g.userData.ring.material.color.setHex(active ? 0xffb547 : (s.t > t ? 0x4aa3ff : (s.ok ? 0x3ecf8e : 0xff5c5c)));
      g.userData.ring.scale.setScalar(active ? 1.4 : 1);
    }
  }

  // ---------------- camera ----------------

  setCamera(mode) {
    const W = this.field.w / 1000, H = this.field.h / 1000;
    this.controls.dispose();
    this.camera = mode === 'top' ? this.ortho : this.persp;
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    if (mode === 'top') {
      this.ortho.position.set(W / 2, H / 2, 10);
      this.controls.enableRotate = false;
      this.controls.screenSpacePanning = true;
    }
    this.controls.target.copy(this.center);
    this._fitAspect = 0;
    this.resize();
  }

  resize() {
    const w = this.el.clientWidth || 1, h = this.el.clientHeight || 1;
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = w + 'px'; this.renderer.domElement.style.height = h + 'px';
    this.persp.aspect = w / h; this.persp.updateProjectionMatrix();
    if (Math.abs(w / h - (this._fitAspect || 0)) > 0.05) { this._fitAspect = w / h; this.fit(); }
    const W = this.field.w / 1000 + 0.2, H = this.field.h / 1000 + 0.2;
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

  _hover(e) { if (this.onHover) this.onHover(this._pick(e)); }

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
