// Test dela → Lidar bez DOM-a (da ga uveze i `node --test`): projekcije sto / radar, slojevi, puštanje snimka, brojke.
// Međukoraci kruga (u stolu / van stola / grupe) stižu sa servera (POST /api/lidar/stages, eurosim/lidarview.py):
//   {in: [[x, y]], out: [[x, y]], raw: [[x, y, k]] (koordinate robota, k: 1 u stolu, 0 van, -1 nema poze),
//    groups: [{x, y, rx, ry, n, dist, angle}], nearest, esp_near: {dist, angle} | null, frame: 'sto' | 'robot', by: 'laptop'}
// Krug (store.lidarScan iz sesije, ili krug iz snimka simulator/lidar/): {pts: [ugao, mm, ...], o: [x, y, z], near, hz,
//   pose: [x, y, ugao°] | null, nopose?, wall: performance.now() kad je stigao, kind: 'sim' | 'robot' | 'snimak'}
//
//   scanPose(scan)                  poza za međukorake: null kad je nema (nopose = STM32 nije povezan, snimak bez poze)
//   radarView(w, h, range)          {cx, cy, k}: robot u centru, napred GORE, levo LEVO; range = mm do ivice
//   radarXY(x, y, v)                tačka robota (x napred, y levo, mm) -> piksel
//   tableView(w, h, field, pad, margin)  {ox, oy, k, W, H}: ceo sto (+ margin mm oko njega) u pravougaoniku, y GORE
//   tableXY(x, y, v)                tačka stola (mm) -> piksel
//   layerItems(stages, layers)      šta se crta po slojevima {sirovo, van, grupe}
//   playIndex(scans, elapsed, loop) {i, done}: krug snimka u trenutku elapsed (ms od početka puštanja)
//   fmtAge(ms), fmtGroup(g), statsRows(scan, stages, now)  brojke za karticu Lidar
//   loadPrefs() / savePrefs(p)      localStorage `eurosim.lidar` {src, file, layers, range, loop} (try/catch)
//   robotLidarView(st, sent)        dugmad Upali/Ugasi lidar i Snimi krugove: {robot, on, state, onDisabled, recDisabled,
//                                   reason}. st = store (session, running, robotMec, robotLidar, robotLidarSeen); sent =
//                                   šta je panel poslao {on, rec}. ESP odbija LIDAR ON/OFF dok taktika radi, dok je robot
//                                   naoružan ili meč traje (upload.py BUSY_OK), pa su tada siva sa razlogom.

export const LAYERS = [
  { id: 'sirovo', label: 'sirovo', title: 'Sve tačke kruga (na stolu: tačke u stolu)' },
  { id: 'van', label: 'van stola', title: 'Tačke van stola (sudija, publika): odbačene, sive i prazne' },
  { id: 'grupe', label: 'grupe', title: 'Grupe tačaka (protivnik?) sa udaljenošću od centra robota' },
];
export const RANGES = [1000, 2000, 4000];
export const STALE_MS = 1500;                      // krug stariji od ovoga: starost žuto
export const PREFS_KEY = 'eurosim.lidar';
export const DEFAULT_PREFS = { src: 'sesija', file: null, layers: { sirovo: true, van: true, grupe: true }, range: 2000, loop: true };

export function scanPose(scan) {
  if (!scan || scan.nopose || !Array.isArray(scan.pose) || scan.pose.length !== 3) return null;
  return scan.pose.every(v => typeof v === 'number' && Number.isFinite(v)) ? scan.pose : null;
}

export function radarView(w, h, range = 2000, pad = 14) {
  const r = Math.max(1, Math.min(w, h) / 2 - pad);
  return { cx: w / 2, cy: h / 2, k: r / range, r };
}

export const radarXY = (x, y, v) => [v.cx - y * v.k, v.cy - x * v.k];

export function tableView(w, h, field = { w: 3000, h: 2000 }, pad = 12, margin = 0) {
  const fw = field.w + 2 * margin, fh = field.h + 2 * margin;       // margin: mm oko stola (tačke van stola blizu ivice)
  const k = Math.max(0.0001, Math.min((w - 2 * pad) / fw, (h - 2 * pad) / fh));
  return { k, W: field.w, H: field.h, ox: (w - field.w * k) / 2, oy: (h - field.h * k) / 2 };
}

export const tableXY = (x, y, v) => [v.ox + x * v.k, v.oy + (v.H - y) * v.k];

export function layerItems(stages, layers = DEFAULT_PREFS.layers) {
  const s = stages || {}, L = { ...DEFAULT_PREFS.layers, ...(layers || {}) };
  const raw = s.raw || [];
  return {
    tableIn: L.sirovo ? s.in || [] : [],
    tableOut: L.van ? s.out || [] : [],
    radarIn: L.sirovo ? raw.filter(p => p[2] !== 0) : [],          // u stolu, ili sve kad nema poze (k = -1)
    radarOut: L.van ? raw.filter(p => p[2] === 0) : [],
    groups: L.grupe ? s.groups || [] : [],
    nearest: L.grupe ? s.nearest || null : null,
  };
}

export function playIndex(scans, elapsed, loop = true) {
  if (!scans || !scans.length) return { i: -1, done: true };
  const period = scans[scans.length - 1].t + 100;                  // kao lidarsrc.FileLidar: +100 ms posle poslednjeg
  let e = Math.max(0, elapsed);
  if (e >= period) {
    if (!loop) return { i: scans.length - 1, done: true };
    e %= period;
  }
  let lo = 0, hi = scans.length - 1;                               // poslednji krug sa t <= e
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (scans[mid].t <= e) lo = mid; else hi = mid - 1;
  }
  return { i: lo, done: false };
}

export function fmtAge(ms) {
  if (ms == null || !Number.isFinite(ms)) return '–';
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function fmtGroup(g) {
  return g ? `${g.dist} mm, ${Math.round(g.angle)}°` : 'nema';
}

// Redovi kartice Lidar: [naziv, vrednost, klasa, title]. Podatak koji izvor nema: „nema sa robota“ (nikad lažna nula).
export function statsRows(scan, stages, now) {
  if (!scan) return [];
  const n = Array.isArray(scan.pts) ? scan.pts.length >> 1 : 0;
  const s = stages || null, pose = scanPose(scan);
  const age = scan.wall == null ? null : now - scan.wall;
  const rows = [
    ['Hz', typeof scan.hz === 'number' ? scan.hz.toFixed(1) : 'nema sa robota', '', 'krugova u sekundi (meri lidar na ESP-u)'],
    ['tačaka', s && pose ? `${n} · u stolu ${s.in.length} · van ${s.out.length}` : String(n), '', 'tačke kruga (bin po stepenu)'],
    ['starost kruga', fmtAge(age), age > STALE_MS ? 'warn' : '', 'koliko je prošlo od poslednjeg kruga'],
    ['poza', pose ? `${Math.round(pose[0])}, ${Math.round(pose[1])} · ${Math.round(pose[2])}°` : 'nema poze', pose ? '' : 'warn',
      pose ? 'poza robota kad je krug stigao' : 'nema poze (STM32 nije povezan ili snimak bez poze): prikaz samo oko robota'],
    ['najbliža grupa', s ? fmtGroup(s.nearest) + (s.nearest ? ` · ${s.nearest.n} t.` : '') : '…', s && s.nearest ? 'hl' : '',
      'izračunao laptop: najbliža tačka grupe od centra robota, ugao pravca grupe (+ levo)'],
    ['najbliža tačka (ESP)', Array.isArray(scan.near) ? `${scan.near[0]} mm, ${scan.near[1]}°` : '–', '',
      'izračunao robot: lib/lidar.py _closest (najbliži bin, ugao + levo)'],
  ];
  return rows;
}

export const BUSY_MEC = { RESET: 'robot je naoružan', NAORUZAN: 'robot je naoružan', POZA: 'robot je naoružan',
  MEC: 'meč traje' };                               // ESP32/lib/match.py armed: upload odbija sve osim LOG/STOP/STAT

export function robotLidarView(st = {}, sent = {}) {
  const ses = st.session, robot = !!(ses && ses.kind === 'robot');
  if (!robot) {
    const reason = ses ? 'samo uz ROBOT sesiju (u simulaciji: ESP meni → Lidar test)' : 'samo uz ROBOT sesiju (Vožnja → ROBOT → Pokreni sesiju)';
    return { robot, on: false, state: null, onDisabled: true, recDisabled: true, reason };
  }
  const busy = st.running ? `taktika ${st.running} radi` : BUSY_MEC[st.robotMec] || null;
  const reason = busy ? `${busy}: ESP odbija LIDAR ON/OFF dok taktika radi, dok je naoružan ili dok meč traje (i sam gasi lidar)` : '';
  const seen = !!st.robotLidarSeen;                // telemetrija javlja stanje lidara: to je istina; inače ono što je panel poslao
  const state = seen ? st.robotLidar || null : sent.state || null;
  const on = seen ? !!state && state !== 'off' : !!sent.on;
  return { robot, on, state, onDisabled: !!busy, recDisabled: !!busy && !sent.rec, reason };
}

const clean = p => {
  const d = DEFAULT_PREFS, o = p && typeof p === 'object' ? p : {};
  const L = o.layers && typeof o.layers === 'object' ? o.layers : {};
  return {
    src: o.src === 'snimak' ? 'snimak' : 'sesija',
    file: typeof o.file === 'string' ? o.file : null,
    layers: Object.fromEntries(LAYERS.map(l => [l.id, typeof L[l.id] === 'boolean' ? L[l.id] : d.layers[l.id]])),
    range: RANGES.includes(o.range) ? o.range : d.range,
    loop: typeof o.loop === 'boolean' ? o.loop : d.loop,
  };
};

export function loadPrefs(storage = globalThis.localStorage) {
  try { return clean(JSON.parse((storage && storage.getItem(PREFS_KEY)) || '{}')); } catch (e) { return clean({}); }
}

export function savePrefs(p, storage = globalThis.localStorage) {
  try { if (storage) storage.setItem(PREFS_KEY, JSON.stringify(clean(p))); } catch (e) { /* ignore */ }
}
