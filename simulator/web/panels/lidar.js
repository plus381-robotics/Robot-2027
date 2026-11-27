// Test dela → Lidar (Zadatak 5.2): sirovo → u stolu / van stola → grupe, sa brojkama. Međukorake računa LAPTOP
// (POST /api/lidar/stages, eurosim/lidarview.py): ESP danas ima samo binove i najbližu tačku (lib/lidar.py _closest).
// Tri panela, jedno stanje (S, ispod):
//   lidar-alati (red komandi)  Izvor: Sesija | Snimak (simulator/lidar/, ▶/⏸, u krug); uz ROBOT sesiju „Upali lidar“
//                              (postojeća komanda LIDAR ON/OFF upload servera; ESP je odbija dok taktika radi, dok je
//                              naoružan ili meč traje — upload.py BUSY_OK — pa je dugme tada sivo sa razlogom; natpis
//                              prati stanje lidara iz telemetrije kad ga ima, inače ono što je panel poslao)
//                              i „Snimi krugove“ (simulator/lidar/<vreme>.jsonl.gz, isti format kao lidarsrc.FileLidar)
//   lidar (glavni region)      sto (u stolu puno, van stola sivo prazno, grupe krstić + mm) i radar oko robota (napred
//                              gore; radi i bez poze). Svoje platno, ne FieldView: Test dela ne otima sto Vožnji.
//   lidar-info (kartica)       slojevi (sirovo / van stola / grupe), Hz, tačke, starost kruga, poza, najbliža grupa
//                              (laptop) i najbliža tačka (ESP), „izračunao laptop“
// Krugovi sesije stižu kroz store.lidarScan (app.js: događaj "lidar" sesije SIM ili ROBOT), odgovori na komandu lidar
// kroz store.lidarReply. Međukoraci se traže samo dok je Test dela prikazan (jedan zahtev odjednom, poslednji krug).
import { registerPanel } from '../core/panels.js';
import { api, esc } from '../core/api.js';
import { LAYERS, RANGES, STALE_MS, robotLidarView, scanPose, radarView, radarXY, tableView, tableXY, layerItems, playIndex,
  fmtGroup, statsRows, loadPrefs, savePrefs } from '../core/lidar.js';

const COL = { bg: '#12151a', table: '#1b232c', edge: '#5a6675', grid: '#26303b', in: '#3ee0ff', out: '#8a96a5',
  group: '#ffb547', near: '#ff5c5c', esp: '#ffd65a', robot: '#dfe5ec', text: '#dfe5ec', dim: '#8a96a5',
  zuta: 'rgba(247,181,0,.22)', plava: 'rgba(47,127,193,.3)' };
const TICK_MS = 100;
const TABLE_MARGIN_MM = 350;          // prostor oko stola na crtežu: tačke van stola blizu ivice (sudija, publika)
const HINT = {
  noSession: 'Nijedna sesija ne radi. Pokreni sesiju u Vožnji (SIM: ESP meni → Lidar test; ROBOT: Upali lidar) ili izaberi Snimak.',
  sim: 'Krugova nema: u Vožnji, na ESP-u izaberi Meni → Lidar test (ili hibrid sa pravim lidarom / snimkom iz Izvora).',
  robot: 'Krugova nema: Upali lidar (ESP ga ne pali dok taktika radi, dok je naoružan ili dok meč traje).',
  noFiles: 'Nema snimaka u simulator/lidar/: snimaju se sa „Snimi krugove“ uz robota ili u hibridu sa pravim lidarom.',
};

const S = {
  ctx: null, prefs: loadPrefs(), scan: null, stages: null, stagesFor: null, busy: false, err: null, stale: false,
  file: null, fileErr: null, loading: null, play: { on: false, start: 0, pos: 0, i: -1 },
  robot: { on: null, state: null, rec: null, n: 0 }, body: { length: 165, width: 300 }, els: {},
};

const visible = () => !!S.ctx && S.ctx.store.get().ws === 'test';
const session = () => (S.ctx ? S.ctx.store.get().session : null);
const setPrefs = p => { S.prefs = { ...S.prefs, ...p }; savePrefs(S.prefs); };

// ---------------- krug i međukoraci ----------------

function setScan(scan) {
  S.scan = scan || null;
  if (!S.scan) { S.stages = null; S.stagesFor = null; draw(); renderInfo(); return; }
  compute();
}

function compute() {
  if (!visible() || S.busy || !S.scan || S.stagesFor === S.scan) return;
  const scan = S.scan;
  S.busy = true;
  api('/api/lidar/stages', { scan: { pts: scan.pts || [], o: scan.o || null, near: scan.near || null, hz: scan.hz ?? null },
    pose: scanPose(scan) })
    .then(d => { S.stages = d; S.stagesFor = scan; S.err = null; })
    .catch(e => { S.err = e.message; S.stages = null; S.stagesFor = scan; })
    .finally(() => { S.busy = false; draw(); renderInfo(); if (S.scan !== scan) compute(); });
}

// Šta se prikazuje: krug za koji su međukoraci stigli (par ostaje usklađen; zaostaje najviše jedan zahtev), inače
// najnoviji krug bez međukoraka.
function pair() {
  return S.stages && S.stagesFor && S.scan ? { scan: S.stagesFor, st: S.stages } : { scan: S.scan, st: null };
}

// Starost kruga: sesija = od kad je stigao; snimak = koliko je puštanje odmaklo od tog kruga (pauza ga ne stari).
function ageWall() {
  if (!S.scan) return null;
  if (S.prefs.src !== 'snimak' || !S.file) return S.scan.wall;
  const p = S.play, el = p.on ? performance.now() - p.start : p.pos, per = S.file.scans[S.file.scans.length - 1].t + 100;
  return performance.now() - Math.max(0, (S.prefs.loop ? el % per : Math.min(el, per)) - S.scan.t);
}

function sessionScan() {
  const s = S.ctx.store.get();
  return s.session ? s.lidarScan : null;
}

// ---------------- snimak (simulator/lidar/) ----------------

function files() { return S.ctx.store.get().lidarFiles || []; }

async function refreshFiles() {
  try {
    const d = await api('/api/lidar/files');
    S.ctx.store.set({ lidarFiles: d.files.map(f => f.name) });       // i Izvori (hibrid: lidar iz snimka) vide nov snimak
  } catch (e) { /* lista ostaje */ }
}

async function loadFile(name) {
  if (!name) { S.file = null; renderTools(); setScan(null); return; }
  setPrefs({ file: name });
  S.loading = name; S.fileErr = null;
  renderTools(); draw();
  try {
    const d = await api('/api/lidar/files/' + encodeURIComponent(name));
    if (S.loading !== name) return;
    if (!d.scans.length) throw new Error('nema krugova');
    S.file = d;
    S.play = { on: true, start: performance.now(), pos: 0, i: -1 };
  } catch (e) {
    if (S.loading !== name) return;
    S.file = null; S.fileErr = `snimak ${name}: ${e.message}`;
  }
  S.loading = null;
  renderTools();
  if (S.prefs.src === 'snimak') { S.play.i = -1; tick(); if (!S.file) setScan(null); }
}

function setPlay(on) {
  const now = performance.now(), p = S.play;
  if (on === p.on || !S.file) return;
  if (on) {
    if (!S.prefs.loop && playIndex(S.file.scans, p.pos, false).done) p.pos = 0;    // kraj snimka: ispočetka
    p.start = now - p.pos;
  } else p.pos = now - p.start;
  p.on = on;
  renderTools();
}

function tick() {
  if (!visible()) return;
  if (S.prefs.src === 'snimak' && S.file && S.file.scans.length) {
    const p = S.play, el = p.on ? performance.now() - p.start : p.pos;
    const { i, done } = playIndex(S.file.scans, el, S.prefs.loop);
    if (i !== p.i) { p.i = i; setScan({ ...S.file.scans[i], wall: performance.now(), kind: 'snimak' }); }
    if (done && p.on) { p.pos = el; p.on = false; renderTools(); }
    renderPos(el);
  }
  const w = ageWall(), stale = w != null && performance.now() - w > STALE_MS;
  if (stale !== S.stale) { S.stale = stale; draw(); }
  renderInfo();
}

function setSrc(src) {
  setPrefs({ src });
  S.play.i = -1;
  if (src === 'sesija') { setPlay(false); setScan(sessionScan()); }
  else {
    const want = files().includes(S.prefs.file) ? S.prefs.file : files()[0];
    if (!S.file || S.file.name !== want) loadFile(want || null);
    else { setPlay(true); tick(); }
  }
  renderTools(); draw();
}

// ---------------- red komandi ----------------

function mountTools(el, ctx) {
  el.className += ' tool-row';
  el.innerHTML = `<span class="dim">Izvor</span>
    <span class="seg" id="liSrc" role="group" title="Odakle dolaze krugovi lidara">
      <button type="button" data-v="sesija" title="Krugovi sesije koja radi (SIM uživo ili ROBOT)">Sesija</button>
      <button type="button" data-v="snimak" title="Snimak krugova iz simulator/lidar/, pušta se svojim tempom">Snimak</button>
    </span>
    <span id="liFileBox" class="li-inline">
      <select id="liFile" title="Snimak krugova (simulator/lidar/)"></select>
      <button type="button" id="liPlay" title="Pusti / pauziraj snimak">▶</button>
      <label title="Posle poslednjeg kruga ispočetka"><input type="checkbox" id="liLoop"> u krug</label>
      <span id="liPos" class="dim small"></span>
    </span>
    <span id="liRobotBox" class="li-inline">
      <button type="button" id="liOn">Upali lidar</button>
      <button type="button" id="liRec">● Snimi krugove</button>
    </span>`;
  const E = S.els;
  for (const id of ['liSrc', 'liFileBox', 'liFile', 'liPlay', 'liLoop', 'liPos', 'liRobotBox', 'liOn', 'liRec'])
    E[id] = el.querySelector('#' + id);
  for (const b of E.liSrc.children) b.onclick = () => { if (S.prefs.src !== b.dataset.v) setSrc(b.dataset.v); };
  E.liFile.onchange = () => loadFile(E.liFile.value);
  E.liPlay.onclick = () => setPlay(!S.play.on);
  E.liLoop.onchange = () => {
    const p = S.play, el2 = p.on ? performance.now() - p.start : p.pos;
    setPrefs({ loop: E.liLoop.checked });
    if (S.file && E.liLoop.checked) { const per = S.file.scans[S.file.scans.length - 1].t + 100; p.pos = el2 % per; p.start = performance.now() - p.pos; }
  };
  E.liOn.onclick = () => {
    const v = robotLidarView(ctx.store.get(), S.robot);
    if (ctx.command(['lidar', v.on ? 'off' : 'on'])) E.liOn.disabled = true;
  };
  E.liRec.onclick = () => { if (ctx.command(['lidar', 'rec', !S.robot.rec])) E.liRec.disabled = true; };
}

function renderTools() {
  const E = S.els;
  if (!E.liSrc) return;
  const src = S.prefs.src;
  for (const b of E.liSrc.children) {
    b.classList.toggle('on', b.dataset.v === src);
    b.setAttribute('aria-pressed', b.dataset.v === src ? 'true' : 'false');
  }
  E.liFileBox.hidden = src !== 'snimak';
  const fl = files(), cur = S.loading || (S.file && S.file.name) || S.prefs.file;
  const html = fl.map(f => `<option value="${esc(f)}"${f === cur ? ' selected' : ''}>${esc(f.replace('.jsonl.gz', ''))}</option>`).join('')
    || '<option value="">nema snimaka</option>';
  if (E.liFile.dataset.html !== html) { E.liFile.innerHTML = html; E.liFile.dataset.html = html; }
  E.liFile.disabled = !fl.length;
  E.liPlay.disabled = !S.file;
  E.liPlay.textContent = S.play.on ? '⏸' : '▶';
  E.liPlay.title = S.play.on ? 'Pauziraj snimak' : 'Pusti snimak';
  E.liLoop.checked = S.prefs.loop;
  E.liRobotBox.hidden = src !== 'sesija';
  const R = S.robot, v = robotLidarView(S.ctx.store.get(), R), state = v.state;
  E.liOn.textContent = v.on ? 'Ugasi lidar' : 'Upali lidar';
  E.liOn.disabled = v.onDisabled;
  E.liOn.title = !v.robot || v.reason ? v.reason
    : (v.on ? 'LIDAR OFF na robotu' : 'LIDAR ON na robotu (postojeća komanda upload servera; ESP je odbija dok taktika radi, dok je naoružan ili dok meč traje)')
      + (state ? ` · stanje: ${state}` : '');
  E.liRec.textContent = R.rec ? '■ Zaustavi snimanje' : '● Snimi krugove';
  E.liRec.classList.toggle('on', !!R.rec);
  E.liRec.disabled = v.recDisabled;
  E.liRec.title = !v.robot ? v.reason : R.rec ? `snima u simulator/lidar/${R.rec}`
    : v.reason || 'Krugovi sa robota u simulator/lidar/<vreme>.jsonl.gz (pušta ih Snimak i hibrid)';
}

function renderPos(el) {
  const E = S.els;
  if (!E.liPos || !S.file) return;
  const n = S.file.scans.length, i = Math.max(0, S.play.i);
  const txt = `krug ${i + 1}/${n} · ${(el / 1000).toFixed(1)} s` + (S.file.truncated ? ` · prvih ${n} od ${S.file.total}` : '');
  if (E.liPos.textContent !== txt) E.liPos.textContent = txt;
}

// ---------------- crtanje ----------------

function fit(cv) {
  const r = cv.parentElement.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  const w = Math.max(10, Math.floor(r.width)), h = Math.max(10, Math.floor(r.height));
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    cv.style.width = w + 'px'; cv.style.height = h + 'px';
  }
  const g = cv.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.fillStyle = COL.bg; g.fillRect(0, 0, w, h);
  return { g, w, h };
}

function dot(g, x, y, r, fill, stroke) {
  g.beginPath(); g.arc(x, y, r, 0, 2 * Math.PI);
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.lineWidth = 1; g.stroke(); }
}

function cross(g, x, y, s, col, label, bold) {
  g.strokeStyle = col; g.lineWidth = bold ? 2.5 : 1.8;
  g.beginPath(); g.moveTo(x - s, y - s); g.lineTo(x + s, y + s); g.moveTo(x + s, y - s); g.lineTo(x - s, y + s); g.stroke();
  if (!label) return;
  g.font = (bold ? 'bold ' : '') + '12px sans-serif'; g.textBaseline = 'middle';
  const tw = g.measureText(label).width;
  g.fillStyle = 'rgba(18,21,26,.8)'; g.fillRect(x + s + 3, y - 8, tw + 6, 16);
  g.fillStyle = col; g.fillText(label, x + s + 6, y);
}

function robotBox(g, P, pose) {           // P(x, y) -> piksel; pose = [x, y, ugao°] (sto) ili [0, 0, 0] (radar)
  const L = S.body.length || 165, W = S.body.width || 300, r = pose[2] * Math.PI / 180, c = Math.cos(r), s = Math.sin(r);
  const at = (a, b) => P(pose[0] + a * c - b * s, pose[1] + a * s + b * c);
  g.strokeStyle = COL.robot; g.lineWidth = 1.5; g.fillStyle = 'rgba(223,229,236,.08)';
  g.beginPath();
  [[L / 2, W / 2], [L / 2, -W / 2], [-L / 2, -W / 2], [-L / 2, W / 2]].forEach(([a, b], i) => { const [x, y] = at(a, b); i ? g.lineTo(x, y) : g.moveTo(x, y); });
  g.closePath(); g.fill(); g.stroke();
  const [x0, y0] = at(0, 0), [x1, y1] = at(L / 2 + 120, 0);
  g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
}

function overlay(box, text) {
  const o = box.querySelector('.li-over');
  o.textContent = text || '';
  o.hidden = !text;
}

function emptyText() {
  if (S.prefs.src === 'snimak') {
    if (!files().length) return HINT.noFiles;
    if (S.loading) return `učitavam snimak ${S.loading}…`;
    if (S.fileErr) return S.fileErr;
    return S.file ? '' : 'izaberi snimak';
  }
  const ses = session();
  if (!ses) return HINT.noSession;
  return S.scan ? '' : ses.kind === 'robot' ? HINT.robot : HINT.sim;
}

function draw() {
  const E = S.els;
  if (!E.table || !visible()) return;
  const { scan, st } = pair(), pose = scan ? scanPose(scan) : null;
  const items = layerItems(st, S.prefs.layers), empty = emptyText();
  drawTable(st, pose, items);
  drawRadar(st, items, scan);
  overlay(E.tableBox, empty || (S.err ? 'međukoraci: ' + S.err
    : scan && !pose ? 'nema poze: prikaz samo oko robota (radar)'
      : S.stale ? 'nema novog kruga duže od 1.5 s (lidar stao?): poslednji krug je posivljen' : ''));
  overlay(E.radarBox, '');                                      // poruka bez podataka je jednom, na stolu
}

function drawTable(st, pose, it) {
  const { g, w, h } = fit(S.els.table), v = tableView(w, h, { w: 3000, h: 2000 }, 8, TABLE_MARGIN_MM);
  const P = (x, y) => tableXY(x, y, v);
  const [x0, y0] = P(0, 2000), [x1, y1] = P(3000, 0);
  g.fillStyle = COL.table; g.fillRect(x0, y0, x1 - x0, y1 - y0);
  g.strokeStyle = COL.grid; g.lineWidth = 1;
  for (let x = 500; x < 3000; x += 500) { const [a] = P(x, 0); g.beginPath(); g.moveTo(a, y0); g.lineTo(a, y1); g.stroke(); }
  for (let y = 500; y < 2000; y += 500) { const [, b] = P(0, y); g.beginPath(); g.moveTo(x0, b); g.lineTo(x1, b); g.stroke(); }
  for (const [side, zx] of [['zuta', 0], ['plava', 2500]]) {
    const [a, b] = P(zx, 1250), [c, d] = P(zx + 500, 750);
    g.fillStyle = COL[side]; g.fillRect(a, b, c - a, d - b);
  }
  g.strokeStyle = COL.edge; g.lineWidth = 2; g.strokeRect(x0, y0, x1 - x0, y1 - y0);
  if (!st || !pose) return;
  g.globalAlpha = S.stale ? 0.4 : 1;                            // star krug (lidar stao?): posivljen
  for (const [x, y] of it.tableOut) { const [a, b] = P(x, y); dot(g, a, b, 3, null, COL.out); }
  for (const [x, y] of it.tableIn) { const [a, b] = P(x, y); dot(g, a, b, 2.2, COL.in); }
  robotBox(g, P, pose);
  for (const gr of it.groups) {
    const [a, b] = P(gr.x, gr.y), n = gr === it.nearest || (it.nearest && gr.x === it.nearest.x && gr.y === it.nearest.y);
    cross(g, a, b, n ? 8 : 6, n ? COL.near : COL.group, `${gr.dist} mm`, n);
  }
  g.globalAlpha = 1;
}

function drawRadar(st, it, scan) {
  const { g, w, h } = fit(S.els.radar), range = S.prefs.range, v = radarView(w, h, range);
  const P = (x, y) => radarXY(x, y, v);
  const step = range <= 1000 ? 250 : range <= 2000 ? 500 : 1000;
  g.lineWidth = 1; g.font = '11px sans-serif'; g.textBaseline = 'bottom';
  for (let r = step; r <= range + 1; r += step) {
    g.strokeStyle = COL.grid; g.beginPath(); g.arc(v.cx, v.cy, r * v.k, 0, 2 * Math.PI); g.stroke();
    g.fillStyle = COL.dim; g.fillText(r >= 1000 ? `${r / 1000} m` : `${r}`, v.cx + 3, v.cy - r * v.k - 1);
  }
  g.strokeStyle = COL.grid; g.beginPath();
  g.moveTo(v.cx - v.r, v.cy); g.lineTo(v.cx + v.r, v.cy); g.moveTo(v.cx, v.cy - v.r); g.lineTo(v.cx, v.cy + v.r); g.stroke();
  g.fillStyle = COL.dim; g.textBaseline = 'top'; g.textAlign = 'right'; g.fillText('napred ↑', v.cx - 4, v.cy - v.r);
  g.textAlign = 'left'; g.fillText('← levo', v.cx - v.r + 2, v.cy + 3);
  robotBox(g, P, [0, 0, 0]);
  const inR = (x, y) => Math.hypot(x, y) <= range * 1.02;
  g.globalAlpha = S.stale ? 0.4 : 1;
  if (st) {
    for (const [x, y] of it.radarOut) if (inR(x, y)) { const [a, b] = P(x, y); dot(g, a, b, 3, null, COL.out); }
    for (const [x, y] of it.radarIn) if (inR(x, y)) { const [a, b] = P(x, y); dot(g, a, b, 2.2, COL.in); }
    for (const gr of it.groups) {
      if (!inR(gr.rx, gr.ry)) continue;
      const [a, b] = P(gr.rx, gr.ry), n = it.nearest && gr.rx === it.nearest.rx && gr.ry === it.nearest.ry;
      cross(g, a, b, n ? 8 : 6, n ? COL.near : COL.group, `${gr.dist} mm, ${Math.round(gr.angle)}°`, n);
    }
  }
  const nr = scan && scan.near;
  if (st && Array.isArray(nr) && nr[0] > 0) {                   // ESP-ova najbliža tačka (robot je izračunao)
    const o = scan.o || [0, 0], r = nr[1] * Math.PI / 180;
    const x = o[0] + nr[0] * Math.cos(r), y = o[1] + nr[0] * Math.sin(r);
    if (inR(x, y)) { const [a, b] = P(x, y); dot(g, a, b, 6, null, COL.esp); }
  }
  g.globalAlpha = 1;
}

// ---------------- kartica Lidar ----------------

function mountInfo(el) {
  el.innerHTML = `<div class="li-by" title="ESP (lib/lidar.py) danas ima samo binove po stepenu i najbližu tačku; detekcija na robotu dolazi sa Fazom 6">
      Međukoraci (u stolu / van stola / grupe): <b>izračunao laptop</b></div>
    <div class="li-layers" role="group" aria-label="Slojevi">${LAYERS.map(l =>
      `<label title="${esc(l.title)}"><input type="checkbox" data-l="${l.id}"> ${esc(l.label)}</label>`).join('')}</div>
    <table class="li-stats"></table>
    <div class="li-groups"></div>
    <div class="li-legend small dim">
      <span><i class="li-k in"></i>u stolu</span><span><i class="li-k out"></i>van stola (odbačeno)</span>
      <span><i class="li-k gr">✕</i>grupa</span><span><i class="li-k nr">✕</i>najbliža grupa</span><span><i class="li-k esp"></i>najbliža tačka (ESP)</span>
    </div>`;
  S.els.stats = el.querySelector('.li-stats');
  S.els.groups = el.querySelector('.li-groups');
  for (const c of el.querySelectorAll('.li-layers input')) {
    c.checked = !!S.prefs.layers[c.dataset.l];
    c.onchange = () => { setPrefs({ layers: { ...S.prefs.layers, [c.dataset.l]: c.checked } }); draw(); renderInfo(); };
  }
}

function renderInfo() {
  const E = S.els;
  if (!E.stats || !visible()) return;
  const { scan, st } = pair();
  const src = S.prefs.src === 'snimak' ? (S.file ? `snimak ${S.file.name.replace('.jsonl.gz', '')}` : 'snimak')
    : session() ? (session().kind === 'robot' ? 'ROBOT (uživo)' : 'SIM (uživo)') : 'nema sesije';
  const rows = [['izvor', src, '', ''], ...statsRows(scan && { ...scan, wall: ageWall() }, st, performance.now())];
  const html = rows.map(([k, v, cls, t]) => `<tr${t ? ` title="${esc(t)}"` : ''}><th>${esc(k)}</th><td class="${cls}">${esc(v)}</td></tr>`).join('');
  if (E.stats.dataset.html !== html) { E.stats.innerHTML = html; E.stats.dataset.html = html; }
  const gr = st ? st.groups.slice().sort((a, b) => a.dist - b.dist) : [];
  const gh = gr.length ? `<div class="dim small">grupe (${gr.length}), najbliža prva:</div>` + gr.slice(0, 8).map(g =>
    `<div class="li-g${g === gr[0] ? ' hl' : ''}">${esc(fmtGroup(g))} <span class="dim">· ${g.n} t.${st.frame === 'sto' ? ` · sto ${g.x}, ${g.y}` : ''}</span></div>`).join('')
    : st ? '<div class="dim small">grupa nema</div>' : '';
  if (E.groups.dataset.html !== gh) { E.groups.innerHTML = gh; E.groups.dataset.html = gh; }
}

// ---------------- prijava ----------------

let started = false;

function start(ctx) {
  if (started) return;
  started = true;
  S.ctx = ctx;
  ctx.store.subscribe((st, prev) => {
    if (st.lidarScan !== prev.lidarScan && S.prefs.src === 'sesija') setScan(sessionScan());
    if (st.session !== prev.session) {
      if (!st.session) S.robot = { on: null, state: null, rec: null, n: 0 };
      if (S.prefs.src === 'sesija') setScan(sessionScan());
      renderTools(); draw();
    }
    if (st.lidarReply !== prev.lidarReply && st.lidarReply) {
      const m = st.lidarReply, L = m.lidar || {};
      if ('on' in L && L.on != null) S.robot.on = L.on;
      if ('state' in L) S.robot.state = L.state;
      if ('rec' in L) { S.robot.rec = L.rec; S.robot.n = L.n || 0; }
      if (L.saved) refreshFiles();
      renderTools();
    }
    if (st.lidarFiles !== prev.lidarFiles || st.running !== prev.running || st.robotMec !== prev.robotMec
      || st.robotLidar !== prev.robotLidar || st.robotLidarSeen !== prev.robotLidarSeen) renderTools();
    if (st.ws !== prev.ws && st.ws === 'test') { compute(); draw(); renderInfo(); }
  });
  api('/api/info').then(i => { if (i.profile && i.profile.body) S.body = i.profile.body; draw(); }).catch(() => {});
  setInterval(tick, TICK_MS);
}

registerPanel({
  id: 'lidar-alati', title: 'Lidar: alati', workspaces: ['test'], region: 'tool', priority: 10, open: true,
  mount: (el, ctx) => { start(ctx); mountTools(el, ctx); renderTools(); },
});

registerPanel({
  id: 'lidar', title: 'Lidar', workspaces: ['test'], region: 'main', priority: 1, open: true,
  mount: (el, ctx) => {
    start(ctx);
    el.innerHTML = `<div class="li-main">
      <div class="li-col li-col-table"><div class="li-h">Sto <span class="dim">· u stolu, van stola, grupe</span></div>
        <div class="li-box" id="liTableBox"><canvas id="liTable"></canvas><div class="li-over" hidden></div></div></div>
      <div class="li-col li-col-radar"><div class="li-h">Radar oko robota <span class="dim">· napred gore</span>
        <span class="seg li-range" id="liRange" title="Domet radara">${RANGES.map(r => `<button type="button" data-v="${r}">${r / 1000} m</button>`).join('')}</span></div>
        <div class="li-box" id="liRadarBox"><canvas id="liRadar"></canvas><div class="li-over" hidden></div></div></div>
    </div>`;
    const E = S.els;
    E.table = el.querySelector('#liTable'); E.radar = el.querySelector('#liRadar');
    E.tableBox = el.querySelector('#liTableBox'); E.radarBox = el.querySelector('#liRadarBox');
    const range = el.querySelector('#liRange');
    const syncRange = () => { for (const b of range.children) b.classList.toggle('on', +b.dataset.v === S.prefs.range); };
    for (const b of range.children) b.onclick = () => { setPrefs({ range: +b.dataset.v }); syncRange(); draw(); };
    syncRange();
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => draw()).observe(el);
    if (S.prefs.src === 'snimak') setSrc('snimak'); else setScan(sessionScan());
  },
  shown: () => { compute(); draw(); renderInfo(); renderTools(); },
});

registerPanel({
  id: 'lidar-info', title: 'Lidar', workspaces: ['test'], region: 'side', priority: 1, open: true, grow: true,
  mount: (el, ctx) => { start(ctx); mountInfo(el); },
  shown: () => renderInfo(),
});
