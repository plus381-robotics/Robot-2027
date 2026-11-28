// Blok „Odozgo · lidar“ (mesto top): radar oko robota (napred gore, levo levo; radi i bez poze), robot, IR lampice u
// uglovima (ugao svetli kad vidi D ili U), najbliža grupa (krstić + mm). Krug: uz sesiju poslednji krug sesije
// (store.lidarScan), bez nje krug snimka u trenutku d.t (run.lidarAt).
// Grupe računa LAPTOP (POST /api/lidar/stages, isto kao detalj lidara): zahtev se šalje samo iz draw (dok se pločica
// vidi), jedan odjednom, za poslednji krug; prikazuje se par krug + međukoraci koji su stigli (kasni najviše jedan
// zahtev), posle odgovora d.redraw(). Bez međukoraka (zahtev traje ili je pao): sirove tačke iz kruga, bez grupa.
// Upozorenje: ispod 5 Hz ili krug stariji od 1,5 s (core/lidar.js STALE_MS). U dnu: Hz · tačaka · najbliža grupa ·
// „grupe računa laptop“ (foot).
// Dugme Upali/Ugasi lidar samo uz ROBOT sesiju (pravi ili virtuelni robot): postojeća komanda ['lidar', 'on'|'off'], siva
// sa razlogom iz robotLidarView dok taktika radi / robot je naoružan / meč traje. Hibrid: pravi lidar pali i gasi sama
// sesija, dugmeta nema. SIM: SIM sesija nema komandu lidar (session.SIM_CMD_CAP, Sim.command), a upload server sa
// LIDAR ON simulirani ESP ima samo kao virtuelni robot (sim.py robot / Poveži robota → virtuelni), pa u SIM-u ostaje uputa
// „na ESP-u: Meni → Lidar test“ (razlog bloka dok krugova nema, na platnu kad krug stane).
// Detalj (klik) su postojeći paneli lidara (panels/lidar.js, sensOpen = 'lidar').
//   scanOf(d)      krug koji blok prikazuje, ili null
//   scanXY(scan)   tačke kruga u koordinatama robota [[x napred, y levo], ...] (mm; od položaja lidara scan.o)
//   lidarLive(d)   stižu sveži krugovi (skica robota tada crta lidar upaljen)
import { api } from '../../core/api.js';
import { STALE_MS, radarView, radarXY, robotLidarView, stagesBody, fmtGroup, fmtAge } from '../../core/lidar.js';
import { sketchGeometry, irSensors, cornerOn, lamp } from '../skica.js';
import { none, at, num, DASH } from './osnova.js';

const RANGE = 1500, RING = 500, SLOW_HZ = 5;
const FOOT = 'grupe računa laptop';
const SIM_HINT = 'na ESP-u: Meni → Lidar test';
const COL = { grid: '#2a313c', dim: '#97a3b3', pts: '#38d9f5', out: '#6b7686', grp: '#ffb547', robot: '#dfe5ec',
  robotFill: 'rgba(223,229,236,.10)', off: '#20262e', edge: '#556070', text: '#e6ebf1' };

export function scanOf(d) {
  const st = (d && d.st) || {};
  if (st.session) return st.lidarScan || null;
  return d && d.run && d.run.lidarAt ? d.run.lidarAt(d.t) : null;
}

export function scanXY(scan) {
  const p = (scan && Array.isArray(scan.pts) && scan.pts) || [], o = (scan && scan.o) || [], out = [];
  for (let i = 0; i + 1 < p.length; i += 2) {
    const r = p[i + 1];
    if (!(r > 0)) continue;
    const a = p[i] * Math.PI / 180;
    out.push([(o[0] || 0) + r * Math.cos(a), (o[1] || 0) + r * Math.sin(a)]);
  }
  return out;
}

const ageOf = scan => (scan && scan.wall != null ? performance.now() - scan.wall : null);
const hzOf = scan => (scan && typeof scan.hz === 'number' && Number.isFinite(scan.hz) ? scan.hz : null);
const nPts = scan => (Array.isArray(scan.pts) ? scan.pts.length >> 1 : 0);
const isStale = scan => { const a = ageOf(scan); return a != null && a > STALE_MS; };

export const lidarLive = d => { const s = scanOf(d); return !!s && !isStale(s); };

// Šta poslati: stanje lidara iz telemetrije (robotLidarView), inače poslednji odgovor na komandu lidar.
function sentOf(st) {
  const r = st.lidarReply, L = r && r.cmd === 'lidar' && r.lidar ? r.lidar : {};
  return { on: L.on ?? null, state: L.state ?? null };
}

function staleHint(st) {
  const s = st.session;
  if (!s) return '';
  if (s.kind === 'robot') return robotLidarView(st, sentOf(st)).on ? 'lidar stao? proveri napajanje i kabl' : 'lidar ugašen: Upali lidar';
  return s.lidar === 'robot' ? 'pravi lidar ne šalje krugove' : s.lidar === 'file' ? '' : SIM_HINT;
}

// ---------------- međukoraci (laptop) ----------------

const C = { key: null, scan: null, st: null, busy: false };
const keyOf = d => (d.st && d.st.session) || d.run || null;             // izvor krugova: sesija ili snimak

function want(d, scan) {
  const key = keyOf(d);
  if (key !== C.key) { C.key = key; C.scan = null; C.st = null; }      // drugi izvor: stari međukoraci ne važe
  if (!scan || C.busy || C.scan === scan) return;
  C.busy = true;
  api('/api/lidar/stages', stagesBody(scan))
    .then(r => { if (C.key === key) { C.scan = scan; C.st = r; } })
    .catch(() => { if (C.key === key) { C.scan = scan; C.st = null; } })
    .finally(() => { C.busy = false; if (d.redraw) d.redraw(); });
}

function pairOf(d, scan) {
  if (!scan) return { scan: null, st: null };
  if (C.st && C.scan && C.key === keyOf(d)) return { scan: C.scan, st: C.st };
  return { scan, st: null };
}

// ---------------- crtanje ----------------

function dot(g, x, y, r, fill, stroke) {
  g.beginPath(); g.arc(x, y, r, 0, 2 * Math.PI);
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.lineWidth = 1; g.stroke(); }
}

function draw(g, w, h, d) {
  const scan = scanOf(d);
  want(d, scan);
  const { scan: ps, st: stg } = pairOf(d, scan), stale = !!scan && isStale(scan);
  const v = radarView(w, h, RANGE, 10), P = (x, y) => radarXY(x, y, v), inR = (x, y) => Math.hypot(x, y) <= RANGE;
  g.lineWidth = 1; g.strokeStyle = COL.grid; g.fillStyle = COL.dim; g.font = '11px system-ui, sans-serif';
  g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  for (let r = RING; r <= RANGE; r += RING) {
    g.beginPath(); g.arc(v.cx, v.cy, r * v.k, 0, 2 * Math.PI); g.stroke();
    g.fillText(String(r / 1000).replace('.', ',') + ' m', v.cx + 4, v.cy - r * v.k + 12);
  }
  g.globalAlpha = stale ? 0.4 : 1;                                    // krug stoji: posivljen
  if (ps && stg && Array.isArray(stg.raw)) {
    for (const [x, y, k] of stg.raw) {
      if (!inR(x, y)) continue;
      const [a, b] = P(x, y);
      if (k === 0) dot(g, a, b, 2.2, null, COL.out); else dot(g, a, b, 2.2, COL.pts);   // van stola: sivo prazno
    }
  } else if (ps) {
    for (const [x, y] of scanXY(ps)) if (inR(x, y)) { const [a, b] = P(x, y); dot(g, a, b, 2.2, COL.pts); }
  }
  const nr = stg && stg.nearest;
  if (nr && inR(nr.rx, nr.ry)) {
    const [a, b] = P(nr.rx, nr.ry);
    g.strokeStyle = COL.grp; g.lineWidth = 2.5;
    g.beginPath(); g.moveTo(a - 7, b - 7); g.lineTo(a + 7, b + 7); g.moveTo(a + 7, b - 7); g.lineTo(a - 7, b + 7); g.stroke();
    g.lineWidth = 1; g.fillStyle = COL.grp; g.font = 'bold 13px system-ui, sans-serif';
    g.fillText(`${nr.dist} mm`, a + 10, b - 7);
  }
  g.globalAlpha = 1;
  drawRobot(g, v, d, scan && !stale);
  if (stale) {                                                        // poruka na tamnoj podlozi (preko tačaka)
    const hint = staleHint((d.st) || {});
    const txt = `nema novog kruga ${fmtAge(ageOf(scan)).replace('.', ',')}` + (hint ? ` · ${hint}` : '');
    g.font = '13px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    const tw = Math.min(w - 8, g.measureText(txt).width + 16), y = Math.max(14, v.cy - v.r * 0.6);
    g.fillStyle = 'rgba(18,21,26,.88)'; g.fillRect(v.cx - tw / 2, y - 11, tw, 22);
    g.fillStyle = COL.text; g.fillText(txt, v.cx, y, w - 16);
    g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  }
}

// Robot na sredini: telo iz Profila (širina popreko, dužina napred-nazad), strelica napred, lidar, IR u uglovima. Kad je
// razmera radara sitna, robot se crta krupnije (do 30 % poluprečnika) da se lampice vide; tačke i mm su u pravoj razmeri.
function drawRobot(g, v, d, live) {
  const geo = sketchGeometry(d.profile), s = Math.max(v.k, Math.min(0.42, 0.3 * v.r / (geo.w / 2)));
  const bw = geo.w * s, bh = geo.len * s, cx = v.cx, cy = v.cy;
  g.fillStyle = COL.robotFill; g.strokeStyle = COL.robot; g.lineWidth = 2;
  g.beginPath(); g.rect(cx - bw / 2, cy - bh / 2, bw, bh); g.fill(); g.stroke();
  g.lineWidth = 1.5;
  g.beginPath(); g.moveTo(cx - 12, cy - bh / 2 - 3); g.lineTo(cx, cy - bh / 2 - 15); g.lineTo(cx + 12, cy - bh / 2 - 3); g.stroke();
  g.lineWidth = 1;
  const o = (scanOf(d) || {}).o || [0, 0];
  dot(g, cx - (o[1] || 0) * s, cy - (o[0] || 0) * s, Math.max(5, Math.min(12, 38 * s)), live ? COL.pts : COL.off, live ? null : COL.edge);
  const sens = irSensors(d.profile), ir = at(d, 'ir'), r = 6;
  for (const front of [true, false]) {
    for (const left of [true, false]) {
      lamp(g, cx + (left ? -1 : 1) * (bw / 2 - r - 2), cy + (front ? -1 : 1) * (bh / 2 - r - 2), r, cornerOn(sens, ir, front, left));
    }
  }
}

// ---------------- blok ----------------

export default {
  id: 'lidar', name: 'Odozgo · lidar', slot: 'top', part: 'lidar', fields: ['@lidar'],
  hints: [
    'Stavi kutiju ~50 cm ispred robota: najbliža grupa ~500 mm, ugao ~0°.',
    'Pomeri je ulevo: ugao raste (suprotno od kazaljke).',
    'Učestanost 8–12 Hz. Ispod 5 Hz: proveri napajanje i kabl lidara.',
    'Tačke van stola (sivo) se ne računaju kao prepreka.',
  ],
  view(d) {
    if (!d.src) return none();
    const st = d.st || {}, scan = scanOf(d);
    if (!scan) return { status: 'none', text: st.session ? 'čeka krug lidara' : 'nema kruga lidara u ovom trenutku snimka', vals: [] };
    const hz = hzOf(scan), p = pairOf(d, scan), stale = isStale(scan), slow = hz != null && hz < SLOW_HZ;
    const vals = [['Hz', hz == null ? DASH : num(hz, 1)], ['tačaka', String(nPts(scan))],
      ['najbliža grupa', p.st ? fmtGroup(p.st.nearest) : '…']];
    let text = 'radi';
    if (stale) {
      const hint = staleHint(st);
      text = `nema novog kruga ${fmtAge(ageOf(scan)).replace('.', ',')}` + (hint ? ` · ${hint}` : '');
    } else if (slow) text = `lidar ${num(hz, 1)} Hz (ispod ${SLOW_HZ} Hz)`;
    return { status: stale || slow ? 'warn' : 'ok', text, vals, foot: FOOT };
  },
  draw,
  actions(d) {
    const st = (d && d.st) || {}, v = robotLidarView(st, sentOf(st));
    if (!v.robot) return [];
    const title = v.reason || (v.on ? 'LIDAR OFF na robotu'
      : 'LIDAR ON na robotu (postojeća komanda upload servera; ESP je odbija dok taktika radi, dok je naoružan ili dok meč traje)')
      + (v.state ? ` · stanje: ${v.state}` : '');
    return [{ label: v.on ? 'Ugasi lidar' : 'Upali lidar', disabled: v.onDisabled, title,
      run: () => d.ctx && d.ctx.command(['lidar', v.on ? 'off' : 'on']) }];
  },
};
