// Statusna traka (varijanta A): Izvor · Veza · Poza · Meč · Korak · Detekcija · ⚠ n · ■ STOP.
// Traka prati sesiju uživo; bez sesije pokazuje snimak u trenutku kursora. Polje bez podatka se ne prikazuje, a
// Izvor, Veza, Meč i STOP su uvek tu.
//   snapshotAt(run, t, {irNames})  -> {pose, match, step, det, errors, label, robot, tactic}   (čisto, bez DOM-a)
//                                     tactic = ime taktike koja je poslednja krenula do t (događaj "tactic"), ili null
//   stripView(state)               -> tekstovi i klase za svako polje                  (čisto, bez DOM-a)
//   mountStrip(el, ctx)            -> crta traku iz ctx.store; STOP = ctx.command(['stop']); u polju Veza „Poveži robota“
//                                     (ctx.openConnect) i „Prekini“ (ctx.disconnect) po linkView
// Stanje (store) piše app.js (most ka starom UI-ju):
//   session   null | {kind: 'sim'|'robot', host, virtual, lidar}    sesija radi
//   paused, speed                                                    sim sesija (poruke data)
//   telemetry null (još nema poruke data) | false (nijedan paket robota) | true
//   running   ROBOT: taktika koja na robotu sada radi (data.running; null = nijedna)
//   linkAge   ms od poslednjeg paketa robota (data.age), linkState/connAge: poruka "state" servera
//   snap      snapshotAt(...) ili null;  notice {text, err, id}: kratka poruka ispod trake

import { hasData } from '../core/run.js';

export const SRC_COLOR = { SIM: '#1f5f99', ROBOT: '#c62828', HIBRID: '#8a5a00', SNIMAK: '#3a4250' };
export const STALE_MS = 1500, LOST_MS = 5000;      // kao server.py: podaci stari / veza izgubljena
export const MATCH_MS = 100000;

export function snapshotAt(run, t, opts = {}) {
  if (!run || !run.cols || !run.cols.t || !run.cols.t.length) return null;
  const c = run.cols, i = run.frameAt(t);
  const at = k => (c[k] && c[k][i] != null ? c[k][i] : null);
  const x = at('x'), y = at('y');
  const pose = x == null || y == null ? null : { x, y, th: at('th') };
  let s = null;
  for (const st of run.steps) if (st.t <= t) s = st;           // poslednji korak koji je krenuo do t
  let step = null;
  if (s) {
    const active = s.end == null || s.end > t;
    step = { idx: s.idx, n: at('n'), name: s.name, active,
      frac: active ? (s.timeout ? (t - s.t) / s.timeout : null) : 1, ok: s.ok };
  }
  let det = null;
  if (hasData(run, 'ir')) {
    const ir = at('ir');
    if (ir != null) {
      const names = (opts.irNames || []).filter((n, k) => ir & (1 << k));
      det = names.length ? 'IR ' + names.join(' ') : 'ništa';
    }
  }
  let errors = 0;
  for (const e of run.log) { if (e.t > t) break; if (e.cls === 'err') errors++; }
  let tactic = null;                                           // taktika koja stvarno radi (i ona pokrenuta sa ESP menija)
  for (const k of run.tactics || []) { if (k.t <= t) tactic = k.name; else break; }
  const meta = run.meta || {};
  return { pose, match: { state: at('mec'), ms: at('match') }, step, det, errors,
    label: meta.tactic || '', robot: !!meta.host, tactic };
}

export function matchView(m) {
  if (!m) return { text: 'miruje', cls: 'idle' };
  const { state, ms } = m;
  if (state === 'KRAJ' || (ms != null && ms >= MATCH_MS)) return { text: 'KRAJ', cls: 'end' };
  if (state === 'NAORUZAN') return { text: 'NAORUŽAN', cls: 'armed' };
  if (ms != null) return { text: `MEČ ${(Math.max(0, MATCH_MS - ms) / 1000).toFixed(1)} s`, cls: 'run' };
  if (state === 'POZA') return { text: 'POZA', cls: 'armed' };
  return { text: 'miruje', cls: 'idle' };
}

export const linkStateOf = age => (age > LOST_MS ? 'lost' : age > STALE_MS ? 'stale' : 'ok');

// Veza: tekst i boja polja + koje dugme nudi (connect = „Poveži robota“, disconnect = „Prekini“).
// Hibrid = SIM sesija sa lidar != 'sim': 'robot' -> „lidar: host“, boja po starosti poslednjeg skena
// (st.lidarScan.wall, isti sat kao now); 'file' -> „lidar iz snimka“. Hibrid nema dugme (Završi je u Vožnji).
export function linkView(st, now = performance.now()) {
  const s = st.session;
  if (!s) return { cls: 'idle', text: 'nije povezano', connect: true, disconnect: false };
  if (s.kind !== 'robot') {
    const no = { connect: false, disconnect: false };
    if (s.lidar === 'robot') {
      const scan = st.lidarScan;
      const fresh = scan && scan.wall != null && now - scan.wall <= STALE_MS;
      return { cls: fresh ? 'ok' : 'warn', text: `lidar: ${s.host || 'robot'}`, ...no };
    }
    const hybridFile = s.lidar && s.lidar !== 'sim';
    if (st.speed == null) return { cls: 'idle', text: 'pokretanje…', ...no };
    if (hybridFile) return { cls: st.paused ? 'warn' : 'ok', text: 'lidar iz snimka', ...no };
    return st.paused ? { cls: 'warn', text: 'simulacija na pauzi', ...no } : { cls: 'ok', text: `simulacija radi · ×${st.speed}`, ...no };
  }
  const rob = (cls, text) => ({ cls, text, connect: false, disconnect: true });
  if (st.telemetry == null) return rob('idle', 'povezivanje…');
  if (!st.telemetry || st.linkAge == null) return rob(st.linkState === 'lost' ? 'bad' : 'warn', 'nema telemetrije');
  const k = linkStateOf(st.linkAge);
  if (k === 'lost') return rob('bad', `veza izgubljena ${Math.round(st.linkAge / 1000)} s`);
  if (k === 'stale') return rob('warn', `podaci stari ${(st.linkAge / 1000).toFixed(1)} s`);
  return rob('ok', 'povezan');
}

// Može li „Poveži robota“: samo bez sesije; inače razlog zašto ne.
export function connectView(st) {
  const s = st.session;
  if (!s) return { ok: true, reason: null };
  if (s.kind === 'robot') return { ok: false, reason: 'Već je povezan: Prekini pa poveži ponovo' };
  return { ok: false, reason: 'Sesija radi: prvo Završi u Vožnji' };
}

// U sesiji podnaslov nosi i taktiku koja radi: ROBOT iz telemetrije (running; null = ne radi nijedna), SIM iz
// snimka sesije (poslednji događaj "tactic"), npr. „virtuelni · primer“, „Live · kamenolomi“.
export function sourceView(st) {
  const s = st.session, snap = st.snap;
  let v;
  if (s && s.kind === 'robot') v = { kind: 'ROBOT', sub: s.virtual ? 'virtuelni' : s.host || '' };
  else if (s && s.lidar && s.lidar !== 'sim') v = { kind: 'HIBRID', sub: s.lidar === 'robot' ? 'lidar sa robota' : 'lidar iz snimka' };
  else if (s) v = { kind: 'SIM', sub: 'Live' };
  else if (snap) v = { kind: 'SNIMAK', sub: snap.label || '' };
  else v = { kind: 'SIM', sub: 'spremno' };
  const tac = !s ? null : s.kind === 'robot' ? st.running : snap && snap.tactic;
  if (tac) v.sub = v.sub ? `${v.sub} · ${tac}` : tac;
  return { ...v, color: SRC_COLOR[v.kind] };
}

const r0 = v => (v == null ? '–' : String(Math.round(v)));

export function stripView(st) {
  const s = st.session, snap = st.snap;
  let pose = null;
  if (snap && snap.pose) pose = { text: `${r0(snap.pose.x)}, ${r0(snap.pose.y)} · ${r0(snap.pose.th)}°`, cls: '' };
  else if (s && s.kind === 'robot' && st.telemetry) pose = { text: 'nema poze (STM32)', cls: 'warn' };
  let step = null;
  if (snap && snap.step) {
    const k = snap.step;
    step = { text: `${k.n ? `${k.idx}/${k.n}` : `#${k.idx}`} ${k.name}`,
      frac: k.frac == null ? null : Math.max(0, Math.min(1, k.frac)), over: k.frac != null && k.frac > 1 && k.active,
      fail: k.ok === false };
  }
  return {
    src: sourceView(st),
    link: linkView(st),
    pose,
    match: matchView(snap && snap.match),
    step,
    det: snap && snap.det != null ? snap.det : null,
    errors: (snap && snap.errors) || 0,
    stopIdle: !s,
  };
}

// ---------------- DOM ----------------

const HTML = `
  <span class="st-src" id="stripSrc" title="Izvor podataka"><b></b><small></small></span>
  <div class="st-f st-link" title="Veza sa izvorom"><span class="k">Veza</span><div class="st-lrow"><span class="v" id="stripLink"><i class="dot"></i><span></span></span>
    <button class="st-lbtn" id="stripConnect" type="button" aria-haspopup="dialog" title="Poveži se sa pravim ili virtuelnim robotom (host, lozinka)">Poveži robota</button>
    <button class="st-lbtn" id="stripDisc" type="button" title="Prekini vezu sa robotom; sesija ostaje kao snimak">Prekini</button></div></div>
  <div class="st-f st-pose" id="stripPoseF"><span class="k">Poza x, y · θ</span><span class="v mono" id="stripPose"></span></div>
  <div class="st-f st-match" id="stripMatchF"><span class="k">Meč</span><span class="v mono" id="stripMatch"></span></div>
  <div class="st-f st-shrink st-step" id="stripStepF"><span class="k">Korak</span><span class="v" id="stripStep"></span>
    <div class="st-stepbar"><i id="stripStepBar"></i></div></div>
  <div class="st-f st-shrink st-det" id="stripDetF"><span class="k">Detekcija</span><span class="v" id="stripDet"></span></div>
  <button class="st-err" id="stripErr" title="Greške u dnevniku (klik: prikaži poslednju)"></button>
  <button class="st-stop" id="stripStop" title="STOP: zaustavi robota (i Esc, iz svakog prostora)">■ STOP</button>`;

export function mountStrip(el, ctx) {
  el.innerHTML = HTML;
  el.setAttribute('role', 'status');
  const q = id => el.querySelector('#' + id);
  const setText = (node, text) => { if (node.textContent !== text) node.textContent = text; };
  const notice = document.createElement('div');
  notice.id = 'stripNotice'; notice.className = 'st-notice'; notice.hidden = true;
  document.body.appendChild(notice);
  let noticeId = null, noticeTimer = null;

  q('stripStop').onclick = () => ctx.command(['stop']);
  q('stripErr').onclick = () => {
    if (ctx.store.get().ws === 'test') ctx.go('voznja');
    ctx.legacy && ctx.legacy.showErrors();
  };
  q('stripConnect').onclick = () => ctx.openConnect && ctx.openConnect(q('stripConnect'));   // dok sesija radi: poruka, bez prozorčića
  q('stripDisc').onclick = () => ctx.disconnect && ctx.disconnect();
  q('stripSrc').onclick = () => { if (ctx.store.get().session) ctx.go('voznja'); };    // klik na izvor: prostor sesije

  function render(st) {
    const v = stripView(st);
    el.style.setProperty('--srcc', v.src.color);
    document.documentElement.style.setProperty('--srcc', v.src.color);
    setText(q('stripSrc').querySelector('b'), v.src.kind);
    setText(q('stripSrc').querySelector('small'), v.src.sub);
    q('stripSrc').title = `Izvor podataka: ${v.src.kind}${v.src.sub ? ' · ' + v.src.sub : ''}`;
    const link = q('stripLink');
    link.querySelector('.dot').className = 'dot ' + v.link.cls;
    setText(link.querySelector('span'), v.link.text);
    link.title = v.link.text;
    q('stripConnect').hidden = !v.link.connect;
    q('stripDisc').hidden = !v.link.disconnect;
    q('stripPoseF').hidden = !v.pose;
    if (v.pose) { setText(q('stripPose'), v.pose.text); q('stripPose').className = 'v mono ' + v.pose.cls; }
    q('stripMatchF').className = 'st-f st-match ' + v.match.cls;
    setText(q('stripMatch'), v.match.text);
    q('stripStepF').hidden = !v.step;
    if (v.step) {
      setText(q('stripStep'), v.step.text);
      q('stripStep').title = v.step.text;
      const bar = q('stripStepBar');
      bar.style.width = v.step.frac == null ? '0' : Math.round(v.step.frac * 100) + '%';
      bar.className = v.step.over || v.step.fail ? 'over' : '';
    }
    q('stripDetF').hidden = v.det == null;
    if (v.det != null) { setText(q('stripDet'), v.det); q('stripDet').title = v.det; }
    q('stripErr').hidden = !v.errors;
    setText(q('stripErr'), `⚠ ${v.errors}`);
    q('stripStop').classList.toggle('idle', v.stopIdle);
    const n = st.notice;
    if (n && n.id !== noticeId) {
      noticeId = n.id;
      notice.textContent = n.text;
      notice.className = 'st-notice' + (n.err ? ' err' : '');
      notice.hidden = false;
      clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => { notice.hidden = true; }, 5000);
    }
  }
  ctx.store.subscribe(render);
  render(ctx.store.get());
  return { render };
}
