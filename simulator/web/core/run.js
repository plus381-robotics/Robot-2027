// Snimak -> "run" (koraci, log, ekrani, lidar...). Bez DOM-a, da ga može da uveze i `node --test`.
//   buildRun(d)                      d = {meta, result, events, cols}: ceo snimak odjednom
//   appendRun(run, frames, events)   dopuna novim frame-ovima (liste dict-ova) i događajima; stare događaje ne prolazi ponovo
//   hasData(run, key)                kolona postoji i nije sva null
//   snapshotRun(run)                 nezavisna kopija (appendRun deli nizove sa živim snimkom koji i dalje raste)

export const LIDAR_HOLD_MS = 400;     // tačke lidara se brišu kad ovoliko nema novog kruga (lidar stao)

// Kolone koje robot ne šalje (snimak v2 ih nema): ponašaju se kao sve-null ("–" u tabeli, bez grafika).
export const OPT_COLS = ['ox', 'oy', 'oth', 'w', 'vl', 'vr', 'v_ref', 'w_ref', 'reg', 'ms', 'stuck', 'ir'];

export function colHasData(cols, key) {
  const c = cols && cols[key];
  return !!c && c.some(v => v != null);
}

export function hasData(run, key) {
  const n = run.cols[key] ? run.cols[key].length : 0;
  const cache = run._has || (run._has = {});
  const h = cache[key];
  if (h && (h.v || h.n === n)) return h.v;          // "ima" ostaje; "nema" se proverava tek kad stigne novih frame-ova
  const v = colHasData(run.cols, key);
  cache[key] = { n, v };
  return v;
}

// Stanje koje se prenosi između dopuna (događaji ne smeju da se prolaze ponovo).
function newState() {
  return { byIdx: {}, pendingLine: {}, gotos: [] };
}

function resolveGoto(steps, g) {                    // GOTO cilj -> korak koji je krenuo u to vreme
  let s = null;
  for (const c of steps) if (c.t <= g.t + 1) s = c;
  g.s = null;
  if (s && !s.target) { s.target = g.target; g.s = s; }
}

function addEvents(run, events) {
  const st = run._st, steps = run.steps;
  const nSteps = steps.length, gotos = [];
  for (const ev of events) {
    const [t, kind, x] = ev;
    if (kind === 'line') { st.pendingLine[x[0]] = x[1]; continue; }
    if (kind === 'exception') { if (x.line) run.excLines.push(x.line); continue; }
    if (kind === 'tactic') {
      run.tactics.push({ t, name: x[0], side: x[1] });
      for (const k in st.byIdx) delete st.byIdx[k];
    } else if (kind === 'step') {
      const s = { idx: x[0], name: x[1], timeout: x[2], next: x[3], t, end: null, ok: null, reason: null, dur: null,
        target: null, line: st.pendingLine[x[0]] || null };
      delete st.pendingLine[x[0]];
      steps.push(s); st.byIdx[x[0]] = s;
    } else if (kind === 'step_end') {
      const s = st.byIdx[x[0]];
      if (s) Object.assign(s, { end: t, ok: x[2], reason: x[3], dur: x[4] });
    } else if (kind === 'rx' && x.name === 'GOTO') {
      gotos.push({ t, target: [x.f.x, x.f.y, x.f.flags & 2 ? null : x.f.theta / 100], s: null });   // 2 = NO_THETA
    } else if (kind === 'log') run.log.push({ t, cls: /^GRESKA|PREKID/.test(x) ? 'err' : '', text: x });
    else if (kind === 'sim') run.log.push({ t, cls: 'sim', text: '[sim] ' + x.text });
    else if (kind === 'buzzer') run.log.push({ t, cls: 'sim', text: '[buzzer] ' + x.kind });
    if (kind === 'rx' || kind === 'tx') {
      const f = Object.entries(x.f || {}).map(([k, v]) => `${k}=${v}`).join(' ');
      run.log.push({ t, cls: 'proto', proto: true,
        text: `${kind === 'rx' ? 'ESP→STM' : 'STM→ESP'} ${x.name} #${x.seq} ${f}` });
    } else if (kind === 'elements') run.elEvents.push({ t, list: x });     // gurnuti kamenolomi
    else if (kind === 'screen') run.screens.push({ t, ...x });
    else if (kind === 'lidar') run.lidars.push({ t, ...x });              // krugovi lidara
  }
  // GOTO: korak sa t <= t_goto + 1 može da stigne i u kasnijoj dopuni, pa se GOTO-i u tom prozoru razrešavaju iznova.
  const win = steps.length > nSteps ? steps[nSteps].t : Infinity;
  const redo = st.gotos.filter(g => g.t + 1 >= win);
  for (const g of redo) if (g.s) { g.s.target = null; g.s = null; }
  for (const g of redo) resolveGoto(steps, g);
  for (const g of gotos) resolveGoto(steps, g);
  st.gotos.push(...gotos);
}

function finish(run) {
  const ts = run.cols.t;
  run.duration = ts.length ? ts[ts.length - 1] : 0;
  return run;
}

export function buildRun(d) {
  const cols = d.cols || {};
  if (!cols.t) cols.t = [];
  const ts = cols.t;
  for (const k of OPT_COLS) if (!cols[k]) cols[k] = ts.map(() => null);
  const run = { ...d, cols, events: d.events || [], steps: [], tactics: [], excLines: [], log: [], screens: [], lidars: [],
    elEvents: [], duration: 0, _st: newState() };
  run.frameAt = t => {                                       // last frame with t <= t
    const ts = run.cols.t;
    let lo = 0, hi = ts.length - 1;
    if (hi < 0) return 0;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (ts[m] <= t) lo = m; else hi = m - 1; }
    return lo;
  };
  run.screenAt = t => {
    let r = null;
    for (const sc of run.screens) { if (sc.t <= t) r = sc; else break; }
    return r;
  };
  run.lidarAt = t => {                           // poslednji krug do t; posle LIDAR_HOLD_MS bez novog: lidar ne radi
    let r = null;
    for (const s of run.lidars) { if (s.t <= t) r = s; else break; }
    return r && t - r.t <= LIDAR_HOLD_MS ? r : null;
  };
  addEvents(run, run.events);
  return finish(run);
}

// Dopuna: novi frame-ovi (lista dict-ova, kao iz live poruke) i novi događaji. Vraća novi objekat koji deli nizove i stanje
// sa starim (pa se `run.live` i slično postavlja iznova).
export function appendRun(run, frames, events) {
  const cols = run.cols;
  if (frames.length) {
    const n0 = cols.t.length;
    const keys = new Set([...Object.keys(cols), ...OPT_COLS]);
    for (const f of frames) for (const k in f) keys.add(k);
    for (const k of keys) {
      if (!cols[k]) cols[k] = new Array(n0).fill(null);
      const c = cols[k];
      for (const f of frames) c.push(f[k] ?? null);
    }
  }
  if (events.length) {
    for (const e of events) run.events.push(e);
    addEvents(run, events);
  }
  return finish({ ...run });
}

// Nezavisna kopija snimka: kolone i događaji se kopiraju, koraci/log se prave iznova (kao buildRun). Za "zakači kao
// referencu" tokom Live-a: rezultat appendRun deli nizove sa snimkom koji i dalje raste.
export function snapshotRun(run) {
  const cols = {};
  for (const k of Object.keys(run.cols)) cols[k] = run.cols[k].slice();
  return buildRun({ meta: { ...(run.meta || {}) }, result: run.result || {}, events: run.events.slice(), cols });
}
