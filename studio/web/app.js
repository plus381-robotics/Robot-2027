// Eurosim UI: ponašanje iza panela okvira varijante A (shell/layout.js, web/panels/): simulacija taktike i puštanje
// snimka (vreme, koraci, dnevnik, stanje, grafici), editor, sesija uživo / sa robotom, protivnici i kamenolomi,
// poređenje i lista snimaka. Paneli premeštaju DOM delove (id-jevi ostaju), app.js ih vezuje po id-ju i piše u store
// ono što traka i paneli prikazuju. Odvojeno: repo (repo.js), profil (profil.js), Komande (komande.js), server (core/api.js).
import { migratedNotice } from './core/migrated.js';
import { FieldView } from './view3d.js';
import { Charts } from './charts.js';
import { EspPanel } from './esp.js';
import { mirrorX } from './side.js';
import { buildRun, appendRun, snapshotRun, LIDAR_HOLD_MS } from './core/run.js';
import { createStore } from './core/store.js';
import { connect } from './core/session.js';
import { mountShell } from './shell/layout.js';
import './panels/index.js';                    // paneli okvira (prijava pri uvozu)
import { snapshotAt } from './shell/strip.js';
import { logLines, errorCount } from './core/log.js';
import { api } from './core/api.js';
import { mountRepo } from './repo.js';
import { mountProfile } from './profil.js';
import { renderCommands } from './komande.js';
import { mountIzvori } from './panels/izvori.js';
import { loadSources, lidarSpec } from './core/izvori.js';
import { SESSION_LOCK } from './core/snimci.js';      // dok sesija radi: Snimci zaključani, Sačuvaj i ▶ Pokreni sivi
import { timeKey } from './core/keys.js';               // vreme (razmak, strelice) i Ctrl+Enter po prostoru

const $ = id => document.getElementById(id);
// Most ka novom okviru (statusna traka, bočna traka): stari kod piše ovde ono što traka treba. Polja: shell/strip.js.
// caps: mogućnosti sesije iz poruke hello (null bez sesije); edUnsaved: editor ima nesačuvan tekst (Live / Pošalji ga
// koriste: napomena u redu komandi Vožnja, core/voznja.js). Snimci (panels/snimci.js): runs = lista sačuvanih snimaka
// (GET /api/runs?detail=1, null dok ne stigne), runName = sačuvan snimak koji se gleda, refName = sačuvan snimak koji je
// referenca (null: nesačuvan, npr. simulacija ili sesija), refLabel = ime reference za prikaz (i nesačuvane; null = nema).
// Referenca (?ref=1) se učitava bez menjanja serverovog „poslednjeg“ snimka: Sačuvaj snimak čuva ono što se gleda.
// repo: null kad aplikacija nije u timskom repou (stavka Repo se ne vidi), inače značka za stavku Repo (web/repo.js).
// Senzori → Lidar (panels/lidar.js): lidarScan = poslednji krug sesije (događaj "lidar" + wall: performance.now(), kind),
// lidarReply = poslednji odgovor na komandu ["lidar", ...] (ROBOT: Upali lidar, Snimi krugove); robotMec, robotLidar,
// robotLidarSeen = stanje meča i lidara iz poslednjeg paketa telemetrije (ROBOT; i bez STM32-a).
const store = createStore({ ws: 'taktike', drive: 'sim', session: null, caps: null, paused: false, speed: null, telemetry: null,
  linkAge: null, linkState: null, connAge: null, snap: null, notice: null, edUnsaved: false, running: null,
  runs: null, runName: null, refName: null, refLabel: null, repo: null,
  sources: loadSources(), lidarFiles: [], helloSource: null, lidarScan: null, lidarReply: null,
  robotMec: null, robotLidar: null, robotLidarSeen: false,
  sensOpen: 'lidar' });      // id otvorenog detalja u Senzorima (null = pregled); Zadatak 7 menja na null
const STRANA = { zuta: 'Žuta', plava: 'Plava' };        // i kartica rezultata (#result) i naslovi taktika u Koracima
const REASON = { BLOCKED: 'blokiran', TIMEOUT: 'isteklo vreme', PREEMPTED: 'prekinut novom komandom', MATCH_OVER: 'kraj meča',
  STOPPED: 'zaustavljen', INVALID: 'odbijen', NOREPLY: 'nema odgovora', SUPERSEDED: 'zamenjen', STOP: 'STOP' };
let REF_SIDE = 'zuta';                // strana za koju se pišu taktike (ESP32/lib/tac.py), stiže sa servera

let info, view, charts, esp, run = null;
let shell = null;                     // mountShell(...): setBadge, openCard (bočne kartice)
let repo = null, profile = null;      // web/repo.js, web/profil.js: dijalozi iz bočne trake (toggle)
let izvori = null;                    // panels/izvori.js: blok Izvori (open/close/toggle)
let opponents = [], oppSel = -1;
let ref = null;                       // reference run for comparing (pinned or loaded)
let ed = null;                        // {editor, api, name, sha, saved} when the editor is open
let edOpening = null;                 // Promise dok se editor otvara (bočna traka Taktike ne sme da ga otvori dvaput)
let live = null;                       // {s (core/session.js), kind, raw: {meta, frames, events}, follow, dirty, lidarSrc}
const play = { t: 0, playing: false, speed: 1, last: 0 };

// ---------------- formatting ----------------

const f0 = v => v == null ? '–' : Math.round(v).toString();
const f1 = v => v == null ? '–' : v.toFixed(1);
const f2 = v => v == null ? '–' : v.toFixed(2);
const secs = ms => (ms / 1000).toFixed(2);

function stateCells(c, i) {
  const t = c.t[i];
  const dx = c.ox[i] == null || c.oy[i] == null ? null : Math.hypot(c.x[i] - c.ox[i], c.y[i] - c.oy[i]);
  const match = c.match[i];
  const rem = match == null ? '–' : Math.max(0, (100000 - match) / 1000).toFixed(1) + ' s';
  const act = c.act && c.act[i] ? Object.entries(c.act[i]).map(([k, v]) => `${k}=${v}`).join(' ') : '–';
  return [
    ['vreme', secs(t) + ' s'], ['do kraja', rem],
    ['tok', c.mec[i] || '–'], ['STM32', c.link[i] ? 'veza ok' : 'nema veze', c.link[i] ? 'good' : 'bad'],
    ['x / y', `${f0(c.x[i])} / ${f0(c.y[i])}`], ['ugao', f1(c.th[i]) + '°'],
    ['odom x/y', `${f0(c.ox[i])} / ${f0(c.oy[i])}`], ['odom ∠', c.oth[i] == null ? '–' : f1(c.oth[i]) + '°'],
    ['greška odom', dx == null ? '–' : f1(dx) + ' mm', dx > 10 ? 'warn' : ''], ['faza STM', c.reg[i] === '' || c.reg[i] == null ? (c.phase[i] || '–') : `${c.phase[i]} ${c.reg[i]}/${c.ms[i]}`],
    ['v', f2(c.v[i]) + ' m/s'], ['v zadato', f2(c.v_ref[i])],
    ['ω', c.w[i] == null ? '–' : f2(c.w[i]) + ' r/s'], ['ω zadato', f2(c.w_ref[i])],
    ['točak L', f2(c.vl[i])], ['točak D', f2(c.vr[i])],
    ['zaglavljen', c.stuck[i] == null ? '–' : c.stuck[i] ? 'DA' : 'ne', c.stuck[i] ? 'bad' : ''], ['aktuatori', act],   // IR: slika ispod (#irPanel)
  ];
}

// ---- IR senzori odozgo (plan U2): lepeza na stvarnom mestu svakog senzora, napred gore ----

const irMirror = n => n.replace('L', 'r').replace('R', 'L').replace('r', 'R');   // plava: levo <-> desno
let irState = { raw: 0, mask: 0xFF };

function buildIrBox() {
  // Izgled A: robot odozgo (napred gore), u svakom uglu dva dugmeta: gornji (U, iznad kutija) i donji (D).
  const sens = info.profile.ir_sensors || [], corner = {};
  sens.forEach((s, k) => {
    const key = (s.x > 0 ? 'F' : 'B') + (s.y > 0 ? 'L' : 'R');               // y > 0 = levo
    (corner[key] = corner[key] || []).push(k);
  });
  const cell = (key, side) => {
    const ks = (corner[key] || []).slice().sort((i, j) => sens[j].z - sens[i].z);   // gornji prvi
    const rows = ks.map(k => {
      const lvl = `<span class="ir-lvl">${sens[k].z > 200 ? 'gornji' : 'donji'}</span>`;
      const chip = `<button type="button" class="ir-s" data-k="${k}"></button>`;
      return side === 'L' ? lvl + chip : chip + lvl;
    }).join('');
    return `<div class="ir-cn ir-${side}"><span class="ir-ct" data-k="${ks[0]}">${key}</span>${rows}</div>`;
  };
  const box = $('irBox');
  box.innerHTML = cell('FL', 'L') + '<div class="ir-robot" title="robot odozgo, napred gore">▲</div>' + cell('FR', 'R') +
    cell('BL', 'L') + cell('BR', 'R');
  for (const g of box.querySelectorAll('.ir-s')) g.onclick = () => {
    if (!live || live.kind) return;                            // samo Live simulacija
    liveSend(['ir_mask', irState.mask ^ (1 << +g.dataset.k)]);
  };
}

function renderIr(raw, mask) {                                 // raw == null: robot ne šalje IR, bez lažne nule
  const none = raw == null;
  irState = { raw: none ? 0 : raw, mask };
  raw = irState.raw;
  const sens = info.profile.ir_sensors || [], blue = (run && run.meta && run.meta.side) === 'plava';
  const name = s => (blue ? irMirror(s.name) : s.name);       // imena kao u taktici (žuta)
  $('irBox').querySelectorAll('.ir-s').forEach(g => {
    const k = +g.dataset.k, on = !!(mask & (1 << k)), sees = !!(raw & (1 << k));
    g.className = 'ir-s ' + (on ? (sees ? 'hit' : 'on') : (sees ? 'off hit' : 'off')) + (live && !live.kind ? ' click' : '');
    g.textContent = name(sens[k]);
    g.title = `${name(sens[k])}: ${sens[k].z > 200 ? 'gornji (iznad kutija)' : 'donji'} · ${on ? 'uključen' : 'isključen'}` +
      (none ? ' · nema podataka sa robota' : sees ? ' · nešto vidi' : '') + (live && !live.kind ? ' · klik: uključi / isključi' : '');
  });
  $('irBox').querySelectorAll('.ir-ct').forEach(t => { t.textContent = name(sens[+t.dataset.k]).slice(0, 2); });
  const off = sens.filter((s, k) => !(mask & (1 << k))).map(name), sees = sens.filter((s, k) => raw & (1 << k)).map(name);
  $('irText').innerHTML = `<span class="dim">F/B napred/nazad · L/R levo/desno · U gornji (iznad kutija) / D donji</span><br>` +
    `vidi: <b>${none ? 'nema podataka sa robota' : sees.join(' ') || '–'}</b> · isključeni: <b>${off.join(' ') || '–'}</b>` +
    (blue ? ' <span class="dim">(plava: imena kao u taktici, L/R zamenjeni)</span>' : '');
}

function renderState(i) {
  const c = run.cols;
  renderIr(c.ir && c.ir[i] != null ? c.ir[i] : null, c.irm && c.irm[i] != null ? c.irm[i] : 0xFF);   // frame bez IR: null, ne 0
  $('stgrid').innerHTML = stateCells(c, i).map(([k, v, cls]) =>
    `<span class="k">${k}</span><span class="v ${cls || ''}">${v}</span>`).join('');
  const t = c.t[i];
  const s = [...run.steps].reverse().find(s => s.t <= t);
  const active = s && (s.end == null || s.end > t);
  $('stepname').textContent = s ? `${s.idx}. ${s.name}` : (c.tac[i] ? 'počinje…' : '—');
  $('stepcount').textContent = c.n[i] ? `${s ? s.idx : 0}/${c.n[i]}` : (s ? `#${s.idx}` : '');
  const bar = $('stepbar');
  if (s && active && s.timeout) {
    const p = (t - s.t) / s.timeout;
    bar.style.width = Math.min(100, p * 100) + '%';
    bar.classList.toggle('over', p > 1);
  } else {
    bar.style.width = s && !active ? '100%' : '0';
    bar.classList.remove('over');
  }
  $('stepnext').textContent = s ? (active ? `traje ${secs(t - s.t)} s${s.timeout ? ' / timeout ' + secs(s.timeout) + ' s' : ''}` :
    `završen: ${s.ok ? 'OK' : (REASON[s.reason] || s.reason || 'neuspeh')}`) + (s.next ? ` · sledeći: ${s.next}` : '') : '';
  const m = c.match[i];
  $('matchtime').textContent = m == null ? '' : `meč ${secs(m)} s`;
}

function renderSteps() {
  const tb = $('steps').querySelector('tbody');
  tb.innerHTML = '';
  const heads = run.tactics.length > 1 ? [...run.tactics] : [];
  for (const s of run.steps) {
    while (heads.length && heads[0].t <= s.t) {
      const h = heads.shift(), tr = document.createElement('tr');
      tr.innerHTML = `<td></td><td colspan="3" class="dim">▶ ${h.name} · ${STRANA[h.side] || h.side} · ${secs(h.t)} s</td>`;
      tr.onclick = () => seek(h.t);
      tb.appendChild(tr);
    }
    const tr = document.createElement('tr');
    const res = s.ok == null ? '<span class="res-run">…</span>' : s.ok ? '<span class="res-ok">OK</span>' :
      `<span class="res-fail">${REASON[s.reason] || s.reason || 'neuspeh'}</span>`;
    tr.innerHTML = `<td><i class="swatch" style="background:${stepColor(s.idx)}"></i>${s.idx}</td><td title="${s.name}">${s.name}</td><td>${res}</td><td>${s.dur == null ? '' : secs(s.dur)}</td>`;
    tr.onmouseenter = () => view.highlightStep(s.idx);
    tr.onmouseleave = () => view.highlightStep(0);
    tr.onclick = () => { seek(s.t); if (ed && s.line && edShowsRun()) ed.editor.reveal(s.line, false); };
    s.row = tr;
    tb.appendChild(tr);
  }
  if (shell) shell.setBadge('koraci', run.steps.length);
}

function updateSteps(t) {
  for (const s of run.steps) {
    s.row.classList.toggle('future', s.t > t);
    const cur = s.t <= t && (s.end == null || s.end > t);
    if (cur && !s.row.classList.contains('cur')) s.row.scrollIntoView({ block: 'nearest' });
    s.row.classList.toggle('cur', cur);
  }
}

let logShown = -1;
function renderLog() {
  const el = $('log');
  el.innerHTML = '';
  run.logEls = [];
  for (const e of logLines(run.log, { proto: $('showProto').checked, errorsOnly: $('logErrOnly').checked })) {
    const d = document.createElement('div');
    d.className = e.cls;
    d.innerHTML = `<span class="t">${secs(e.t)}</span>`;
    d.appendChild(document.createTextNode(e.text));
    d.onclick = () => seek(e.t);
    el.appendChild(d);
    run.logEls.push([e.t, d]);
  }
  logShown = -1;
  if (shell) shell.setBadge('dnevnik', errorCount(run.log) || '');      // bez grešaka: bez broja
}

function updateLog(t) {
  const els = run.logEls;
  let k = -1;
  for (let j = 0; j < els.length; j++) { if (els[j][0] <= t) k = j; else break; }
  if (k === logShown) return;
  els.forEach(([tt, d], j) => { d.classList.toggle('future', j > k); d.classList.toggle('cur', j === k); });
  if (k >= 0) els[k][1].scrollIntoView({ block: 'nearest' });
  logShown = k;
}

function renderResult() {
  const r = run.result, el = $('result');
  if (r.robot) {                                // snimak sa robota (telemetrija): nema stvarne poze ni ishoda
    const c = run.cols, n = c.t.length - 1;
    const done = run.steps.filter(s => s.ok === true).length, bad = run.steps.filter(s => s.ok === false);
    el.className = bad.length ? 'fail' : 'ok';
    el.style.display = 'block';
    el.innerHTML = `<b>ROBOT</b> <span class="dim">${run.meta.host} · ${run.meta.tactic || 'bez taktike'} · ${STRANA[run.meta.side] || ''}</span>
      <div class="dim">${secs(run.duration)} s telemetrije · koraci OK ${done}/${run.steps.length}${n >= 0 ? ` · poslednja poza ${f0(c.x[n])}, ${f0(c.y[n])}, ${f1(c.th[n])}°` : ''}</div>
      ${bad.map(s => `<div>korak ${s.idx} „${s.name}“: ${REASON[s.reason] || s.reason}</div>`).join('')}
      <div class="dim small">poza = odometrija robota · telemetrija 10 Hz: vrlo kratak korak može da se ne vidi</div>`;
    return;
  }
  const fail = r.fail ? `<div>neuspeh na koraku ${r.fail[0]} „${r.fail[1]}“: ${REASON[r.fail[2]] || r.fail[2]}</div>` : '';
  const warn = [];
  if (r.start_in_zone === false) warn.push('robot ne kreće iz svoje startne zone');
  if (r.errors && r.errors.length) warn.push(...r.errors.slice(-3));
  el.className = r.ok ? 'ok' : 'fail';
  el.style.display = 'block';
  el.innerHTML = `<b>${r.ok ? 'OK' : 'NIJE OK'}</b> <span class="dim">${run.meta.tactic} · ${STRANA[run.meta.side] || run.meta.side} · ${run.meta.mode === 'mec' ? 'meč' : 'test'}</span>
    ${r.how ? `<div>taktika stala: ${r.how}</div>` : ''}${fail}
    <div class="dim">koraci ${r.done ?? 0}/${r.steps ?? 0} · taktika ${r.ms != null ? secs(r.ms) + ' s' : '–'} · kraj ${f0(r.pose[0])}, ${f0(r.pose[1])}, ${f1(r.pose[2])}°
    · na kraju u svojoj zoni: ${r.in_own_zone ? 'da' : 'ne'}</div>
    ${warn.map(w => `<div style="color:var(--warn)">⚠ ${w}</div>`).join('')}`;
}

// Timeline (plan S9): traka koraka (od početka do kraja, boja kao na stolu, crveno = neuspeh), zastavice
// NAORUŽAN / ČINČ / upozorenja, senka faze napada (85-100 s meča) i os u sekundama meča.
const STEP_COLORS = ['#4cc9f0', '#f72585', '#b5e48c', '#ffd166', '#9d4edd', '#ff8c42', '#06d6a0', '#ef476f'];
const stepColor = idx => STEP_COLORS[(idx - 1 + STEP_COLORS.length) % STEP_COLORS.length];

function runFlags(r) {
  const out = [];
  for (const l of r.log) {
    if (/^NAORUZAN/.test(l.text)) out.push({ t: l.t, k: 'armed', label: 'NAORUŽAN', title: l.text });
    else if (/^CINC: start/.test(l.text)) out.push({ t: l.t, k: 'cord', label: 'ČINČ', title: 'činč povučen: meč počinje' });
    else if (/STM32 restart|nema veze|pad veze|STM32 se ne javlja|ESP restart/.test(l.text)) out.push({ t: l.t, k: 'warn', label: '⚠', title: l.text });
    else if (/^KRAJ meca/.test(l.text)) out.push({ t: l.t, k: 'end', label: 'KRAJ', title: 'kraj meča' });
  }
  return out;
}

function renderMarks() {
  const D = run.duration || 1, pct = t => (Math.max(0, Math.min(D, t)) / D * 100) + '%';
  const st = $('bandSteps'); st.innerHTML = '';
  run.steps.forEach((s, k) => {
    const end = s.end ?? (run.steps[k + 1] ? run.steps[k + 1].t : D);
    const b = document.createElement('div');
    b.className = 'bstep' + (s.ok === false ? ' fail' : '') + (s.end == null ? ' open' : '');
    b.style.left = pct(s.t); b.style.width = `calc(${(Math.max(end - s.t, 0) / D * 100)}% - 1px)`;
    b.style.setProperty('--c', stepColor(s.idx));
    b.textContent = `${s.idx} ${s.name}`;
    b.title = `${s.idx}. ${s.name}\n${secs(s.t)} s → ${s.end != null ? secs(s.end) + ' s' : '…'}` +
      (s.ok === false ? `\nNEUSPEH: ${REASON[s.reason] || s.reason || ''}` : s.ok ? '\nOK' : '') + '\nklik: skoči ovde';
    b.onclick = () => seek(s.t);
    b.onmouseenter = () => view.highlightStep(s.idx);
    b.onmouseleave = () => view.highlightStep(0);
    st.appendChild(b);
  });
  const fl = $('bandFlags'); fl.innerHTML = '';
  const flags = runFlags(run);
  const cord = flags.find(f => f.k === 'cord');
  if (cord) {                                        // faza napada: 85..100 s od činča
    const a = document.createElement('div'); a.className = 'attack';
    a.style.left = pct(cord.t + 85000); a.style.width = `calc(${pct(cord.t + 100000)} - ${pct(cord.t + 85000)})`;
    a.title = 'faza napada (85-100 s meča)';
    if (cord.t + 85000 < D) fl.appendChild(a);
  }
  for (const f of flags) {
    const e = document.createElement('div'); e.className = 'flag ' + f.k; e.style.left = pct(f.t);
    e.textContent = f.label; e.title = `${secs(f.t)} s: ${f.title}`; e.onclick = () => seek(f.t);
    fl.appendChild(e);
  }
  // os: sekunde meča kad postoji činč, inače vreme simulacije
  const ax = $('bandAxis'); ax.innerHTML = '';
  const span = (D - (cord ? cord.t : 0)) / 1000;
  const t0 = cord ? cord.t : 0, stepS = span > 60 ? 10 : span > 15 ? 5 : 1;
  for (let s = 0; t0 + s * 1000 <= D; s += stepS) {
    const e = document.createElement('span'); e.style.left = pct(t0 + s * 1000); e.textContent = s + (s === 0 ? (cord ? ' s meča' : ' s') : '');
    ax.appendChild(e);
  }
  charts.setSteps(run.steps.map(s => ({ t: s.t, idx: s.idx, color: stepColor(s.idx), fail: s.ok === false })));
}

// ---------------- playback ----------------

function seek(t, keepPlaying = false) {
  if (!run) return;
  if (live && !keepPlaying) setFollow(false);
  play.t = Math.max(0, Math.min(run.duration, t));
  if (!keepPlaying) setPlaying(false);
  show();
}

function show() {
  if (!run.cols.t || !run.cols.t.length) return;
  const i = run.frameAt(play.t);
  showElementsAt(play.t);
  esp.setScreen(run.screenAt(play.t));
  view.setLidar(run.lidarAt(play.t));
  edMarks();
  view.setFrame(i);
  renderState(i);
  updateSteps(play.t);
  updateLog(play.t);
  charts.setTime(play.t);
  if (ref) view.setCompareTime(play.t - alignOf(run) + alignOf(ref));
  $('slider').value = i;
  $('time').textContent = `${secs(play.t)} / ${secs(run.duration)} s`;
  if (!live) bridgeSnap(play.t);                // bez sesije traka pokazuje snimak u trenutku kursora
}

// ---------------- most ka statusnoj traci (store) ----------------

function irNames() {                            // imena IR senzora kao u taktici (plava: L/R zamenjeni)
  const sens = (info && info.profile && info.profile.ir_sensors) || [], blue = (run && run.meta && run.meta.side) === 'plava';
  return sens.map(s => (blue ? irMirror(s.name) : s.name));
}

function bridgeSnap(t) {
  store.set({ snap: run ? snapshotAt(run, t, { irNames: irNames() }) : null });
}

function bridgeSession() {                      // sesija počela / završila: traka kreće iz početnog stanja veze
  const L = live;                               // caps stižu porukom hello (sessionHello); do tada nijedna komanda
  store.set({ session: L ? { kind: L.kind === 'robot' ? 'robot' : 'sim', host: L.host || L.lidarHost || null, virtual: !!L.virtual,
    lidar: L.lidarSrc || 'sim', edText: !!L.edText } : null, caps: null,
    paused: false, speed: null, telemetry: null, linkAge: null, linkState: null, connAge: null, running: null,
    runName: null, helloSource: null, lidarScan: null, lidarReply: null, robotMec: null, robotLidar: null, robotLidarSeen: false });   // sesija nije sačuvan snimak (Snimci ga ne ističu)
  $('speed').hidden = !!L;                     // brzina puštanja snimka; u sesiji važi brzina iz reda komandi Vožnja
  // Dok sesija radi Sačuvaj snimak bi sačuvao serverov „poslednji“ snimak (ne sesiju na ekranu), a brza simulacija ne
  // radi: oba dugmeta siva sa razlogom (lista Snimci je prigušena, klik odbija loadRun). Posle kraja sesije: kao pre.
  const sv = $('save'), rb = $('run');
  sv.dataset.title ??= sv.title; rb.dataset.title ??= rb.title;
  sv.disabled = !!L || !run;
  sv.title = L ? SESSION_LOCK.save : sv.dataset.title;
  rb.title = L ? SESSION_LOCK.run : rb.dataset.title;
  if (L) {                                      // nova sesija kreće na ×1, bez pauze: red komandi to i pokazuje
    $('pace').value = '1';
    $('pauseBtn').textContent = '⏸ Pauza'; $('pauseBtn').classList.remove('on');
  }
}

function sessionHello(s) {                      // hello: red komandi Vožnja i kartica ESP po mogućnostima sesije;
  s.on('hello', m => {                          // source = izvori koje sesija stvarno koristi (Izvori, samo čitanje)
    if (live && live.s === s) store.set({ caps: [...(m.capabilities || [])].sort(), helloSource: m.source || null });
  });
}

function notice(text, err = true) {             // kratka poruka ispod trake (i u staroj liniji poruka)
  const n = store.get().notice;
  store.set({ notice: { text, err, id: (n ? n.id : 0) + 1 } });
  msg(text, err);
}

// Komanda sesiji iz okvira (STOP iz trake, Esc): nikad ne propada nečujno.
function sessionCommand(c) {
  const name = c[0] === 'stop' ? 'STOP' : String(c[0]);
  if (!live) { notice(`${name}: nijedna sesija ne radi`, false); return false; }
  if (liveSend(c)) return true;
  notice(`${name} nije poslat: veza zatvorena`);
  return false;
}

function setPlaying(p) {
  if (live) { if (p) setFollow(true); else setFollow(false); return; }
  if (p && run && play.t >= run.duration) play.t = 0;
  play.playing = p && !!run;
  play.last = performance.now();
  $('play').textContent = play.playing ? '⏸' : '▶';
}

function tick(now) {
  if (play.playing && run) {
    play.t += (now - play.last) * play.speed;
    if (play.t >= run.duration) { play.t = run.duration; setPlaying(false); }
    show();
  }
  play.last = now;
  requestAnimationFrame(tick);
}

function stepJump(dir) {
  if (!run) return;
  const times = run.steps.map(s => s.t);
  const t = play.t;
  const target = dir > 0 ? times.find(x => x > t + 1) : [...times].reverse().find(x => x < t - 1);
  seek(target ?? (dir > 0 ? run.duration : 0));
}

function frameJump(dir) {
  if (!run) return;
  const i = Math.max(0, Math.min(run.cols.t.length - 1, run.frameAt(play.t) + dir));
  seek(run.cols.t[i]);
}

// ---------------- server ----------------

// Poruka (panels/poruka.js, desni kraj reda komandi u svakom prostoru); err = crveno.
// act = {label, title, fn}: dugme uz poruku (npr. „Otvori u Snimcima“ posle kraja sesije); sledeća poruka ga sklanja.
function msg(text, err = false, act = null) {
  const m = $('msg'); m.textContent = text; m.className = 'msg' + (err ? ' err' : ''); m.title = text;
  const b = $('msgAct');
  b.hidden = !act;
  if (act) { b.textContent = act.label; b.title = act.title || ''; b.onclick = () => { b.hidden = true; act.fn(); }; }
}

// runName: ime sačuvanog snimka (Snimci ga ističu u listi); null za simulaciju, sesiju i ostalo.
function load(d, label, keepTime = null, runName = null) {
  run = buildRun(d);
  store.set({ runName });
  view.setRun(run);
  elShownKey = null;
  drawElements();
  view.setVisibility({ odom: $('showOdom').checked, targets: $('showTargets').checked });
  charts.setRun(run);
  renderSteps(); renderLog(); renderResult(); renderMarks();
  $('slider').max = Math.max(0, run.cols.t.length - 1);
  $('save').disabled = false;
  if (label) msg(label);
  if (d.meta && d.meta.obstacles) {
    opponents = d.meta.obstacles.map(o => ({ ...o }));
    if (oppSel >= opponents.length || keepTime == null) oppSel = -1;     // ponovljena simulacija: izbor ostaje
    refreshOpponents();
  }
  if (keepTime != null) { seek(keepTime); return; }
  seek(0);
  setPlaying(true);
}

let simSeq = 0;                                 // samo odgovor poslednje simulacije se prikazuje

async function simulate(keepTime = null) {
  if (live) return;
  const seq = ++simSeq;
  const body = { tactic: $('tactic').value, side: $('side').value, mode: $('mode').value, obstacles: opponents,
    elements: elementsArg() };
  try { localStorage.setItem('eurosim.sel', JSON.stringify(body)); } catch (e) { /* ignore */ }
  if (ed) { body.tactic = ed.name; body.source = ed.editor.text(); }
  $('run').disabled = true;
  msg(`simuliram ${body.tactic}…`);
  try {
    const d = await api('/api/run', body);
    if (seq !== simSeq || live) return;         // u međuvremenu pokrenuta novija (npr. izmena protivnika) ili sesija: zastarela
    load(d, `${body.tactic}: simulirano ${secs(d.result.sim_ms)} s za ${d.wall_s} s`, keepTime);
    if (ed && d.diagnostics) edDiagnostics(d.diagnostics);
  } catch (e) {
    if (seq !== simSeq) return;
    if (ed && e.data && e.data.diagnostics) edDiagnostics(e.data.diagnostics);
    msg(e.message.split('\n')[0], true);
    console.error(e);
  } finally {
    if (seq === simSeq) $('run').disabled = !!live;
  }
}

function fillRuns(list) {                      // „Uporedi sa…“ u redu komandi Snimci
  const opt = n => { const o = document.createElement('option'); o.textContent = n; return o; };
  const sel = $('cmpRun');
  sel.innerHTML = '<option value="">Uporedi sa…</option>';
  sel.append(...list.map(opt));
}

// Lista u Snimcima (sa detaljima: datum, izvor, taktika, ishod); i „Uporedi sa…“ istim redom (najnoviji prvi).
let runsSeq = 0;
async function refreshRuns() {
  const seq = ++runsSeq;
  try {
    const rows = await api('/api/runs?detail=1');
    if (seq !== runsSeq) return;
    store.set({ runs: rows });
    fillRuns(rows.map(r => r.name));
  } catch (e) {
    if (seq !== runsSeq) return;
    if (store.get().runs == null) store.set({ runs: [] });
    msg('lista snimaka: ' + e.message, true);
  }
}

// Klik u listi Snimci (ranije „Load run…“ u meniju „⋯ Runs“). Dok sesija radi odbija: učitavanje bi zamenilo snimak
// sesije na stolu, protivnike (sledeći „+ Protivnik“ bi ih poslao u sesiju) i serverov „poslednji“ snimak.
async function loadRun(n) {
  if (live) { notice(SESSION_LOCK.load); return; }
  try {
    const d = await api('/api/runs/' + encodeURIComponent(n));
    if (live) { notice(SESSION_LOCK.load); return; }          // sesija pokrenuta dok je snimak stizao
    load(d, `učitan snimak ${n}`, null, n);
  } catch (er) { msg(er.message, true); }
}

const OPEN_SNIMCI = { label: 'Otvori u Snimcima', title: 'Prostor Snimci: sačuvaj ovaj snimak, uporedi ga sa drugim (📌 Referenca, Uporedi sa…)',
  fn: () => shell && shell.go('snimci') };

// ---------------- kamenolomi (plan E3): izmenjen sto, scenariji ----------------

let tableEl = null, elSel = -1, elShownKey = null;     // tableEl: izmenjeni kamenolomi (null = po pravilima)

const curElements = () => (tableEl ? tableEl : JSON.parse(JSON.stringify(info.field.elements)));
const elementsArg = () => ($('showElements').checked ? (tableEl || true) : false);

function drawElements() {                       // trenutno (izmenljivo) stanje stola; za vreme puštanja: showElementsAt
  elShownKey = 'edit';
  const list = $('showElements').checked ? curElements() : [];
  if (elSel >= list.length) elSel = -1;
  view.setElements(list, { editable: $('showElements').checked, sel: elSel });
  refreshElPanel();
}

function showElementsAt(t) {                    // snimak: kamenolomi kako ih je robot (ili protivnik) pomerio
  if (!run || !run.elEvents || !run.elEvents.length) { if (elShownKey !== 'edit') drawElements(); return; }
  let k = -1;
  for (let j = 0; j < run.elEvents.length && run.elEvents[j].t <= t; j++) k = j;
  const key = k < 0 ? 'edit' : 'ev' + k;
  if (key === elShownKey) return;
  if (k < 0) { drawElements(); return; }
  elShownKey = key;
  view.setElements(run.elEvents[k].list, { editable: false });
}

function refreshElPanel() {
  const list = $('showElements').checked ? curElements() : [];
  const e = view.elements[elSel] || list[elSel];
  $('elEdit').hidden = !e || elSel < 0;
  if (!e || elSel < 0) return;
  $('elName').textContent = e.name || '';
  $('elStones').textContent = e.stones ?? 3;
  $('elPos').textContent = `${Math.round(e.x)}, ${Math.round(e.y)} · ${e.th || 0}°`;
}

function elEdit(fn) {
  const l = curElements();
  if (!l[elSel]) return;
  fn(l[elSel]);
  if (l[elSel].stones === 0) { l.splice(elSel, 1); elSel = -1; }
  tableEl = l;
  drawElements();
  elementsChanged(true);
}

let elTimer = null;
function elementsChanged(final, fromView = false) {   // fromView: kamenolom prevučen mišem (pozicija je u view.elements)
  if (fromView && view.elements.length && elShownKey === 'edit') tableEl = view.elements.map(e => ({ ...e }));
  try { localStorage.setItem('eurosim.el', JSON.stringify(tableEl)); } catch (e) { /* ignore */ }
  refreshElPanel();
  if (live) {
    clearTimeout(elTimer);
    elTimer = setTimeout(() => liveSend(['elements', $('showElements').checked ? curElements() : []]), final ? 0 : 100);
  } else if (final && run) simulate(play.t);
}

async function fillScenarios() {
  try {
    const d = await api('/api/scenarios');
    $('scenLoad').innerHTML = '<option value="">učitaj scenario…</option>' + d.scenarios.map(n => `<option>${n}</option>`).join('');
  } catch (e) { /* ignore */ }
}

async function saveScenario() {
  const name = askName('Sačuvaj sto (kamenolome) i protivnike kao scenario:', 'scenario');
  if (!name) return;
  try {
    await api('/api/scenarios/save', { name, elements: curElements(), opponents });
    fillScenarios(); msg(`scenario ${name} sačuvan (studio/scenarios/${name}.json)`);
  } catch (e) { msg(e.message, true); }
}

async function loadScenario(name) {
  try {
    const d = await api('/api/scenarios/' + encodeURIComponent(name));
    tableEl = d.elements || null; opponents = d.opponents || [];
    $('showElements').checked = true; elSel = -1; oppSel = -1;
    drawElements(); refreshOpponents(); saveOpponents();
    elementsChanged(true);
    msg(`scenario ${name}`);
  } catch (e) { msg(e.message, true); }
}

// ---------------- opponents ----------------

function saveOpponents() {
  try { localStorage.setItem('eurosim.opp', JSON.stringify(opponents)); } catch (e) { /* ignore */ }
}

function refreshOpponents() {
  view.setOpponents(opponents, oppSel);
  const o = opponents[oppSel];
  $('oppEdit').hidden = !o;
  if (!o) return;
  $('oppName').textContent = o.name || '';
  const round = !!o.r;
  $('oppX').value = o.x; $('oppY').value = o.y;
  $('oppW').value = round ? o.r * 2 : o.w; $('oppH').value = o.h; $('oppH').disabled = round;
  $('oppTh').value = o.th || 0; $('oppZ').value = o.z || 350; $('oppRound').checked = round;
  $('oppTac').innerHTML = '<option value="">stoji</option>' + (info.opp_tactics || []).map(n => `<option>${n}</option>`).join('');
  $('oppTac').value = o.tactic || ''; $('oppSeed').value = o.seed || 1;
}

let oppTimer = null;
function opponentsChanged(final) {
  saveOpponents();
  if (live) {                                   // live: send at most every 100 ms while dragging
    if (final || !oppTimer) {
      clearTimeout(oppTimer);
      oppTimer = setTimeout(() => { oppTimer = null; liveSend(['obstacles', opponents]); }, final ? 0 : 100);
    }
  } else if (final && run) {
    simulate(play.t);                           // fast mode: re-run, stay at the same moment
  }
}

function editOpponent() {
  const o = opponents[oppSel]; if (!o) return;
  const round = $('oppRound').checked;
  o.x = +$('oppX').value; o.y = +$('oppY').value; o.th = +$('oppTh').value; o.z = +$('oppZ').value;
  o.tactic = $('oppTac').value || undefined; o.seed = Math.max(1, +$('oppSeed').value || 1);
  if (round) { o.r = Math.max(10, +$('oppW').value / 2); } else { o.r = 0; o.w = +$('oppW').value; o.h = +$('oppH').value; }
  refreshOpponents();
  opponentsChanged(true);
}

// ---------------- editor ----------------

const curTactic = () => (ed ? ed.name : $('tactic').value);
const edShowsRun = () => !!(ed && run && run.meta && run.meta.tactic === ed.name);
let edMarkKey = '';

function edMarks() {
  if (!ed) return;
  let m = {};
  if (edShowsRun()) {
    const t = play.t;
    let cur = null;
    const fail = [];
    for (const s of run.steps) {
      if (!s.line || s.t > t) continue;
      cur = s;
      if (s.ok === false && s.end != null && s.end <= t) fail.push(s.line);
    }
    m = { cur: cur && cur.line, fail, err: t >= run.duration - 1 || !live ? run.excLines : [] };
  }
  const key = JSON.stringify(m);
  if (key === edMarkKey) return;
  const scroll = !!(m.cur && JSON.parse(edMarkKey || '{}').cur !== m.cur && (play.playing || (live && live.follow)));
  edMarkKey = key;
  ed.editor.setMarks({ ...m, scroll });
}

function edDiagnostics(list) {
  ed.diags = list;
  ed.editor.setDiagnostics(list);
  const el = $('edProblems');
  el.innerHTML = '';
  const order = { error: 0, warning: 1, info: 2 };
  const sorted = [...list].sort((a, b) => order[a.severity] - order[b.severity] || a.line - b.line);
  for (const d of sorted) {
    const div = document.createElement('div');
    div.className = d.severity;
    div.innerHTML = `<span class="ln">${d.line}:${(d.col || 0) + 1}</span>`;
    div.appendChild(document.createTextNode(`${d.severity === 'error' ? '✖' : d.severity === 'warning' ? '⚠' : 'ℹ'} ${d.msg}`));
    div.onclick = () => ed.editor.reveal(d.line);
    el.appendChild(div);
  }
  if (!list.length) el.innerHTML = '<div class="info">nema problema</div>';
  const n = list.filter(d => d.severity === 'error').length, w = list.filter(d => d.severity === 'warning').length;
  $('edCount').textContent = n || w ? `greške: ${n} · upozorenja: ${w}` : '✓';
}

function edState() {
  const dirty = ed.editor.text() !== ed.saved;
  store.set({ edUnsaved: dirty });                 // Vožnja: „koristi se tekst iz editora (nesačuvan)“
  $('edState').textContent = (ed.sha ? '' : 'nova · ') + (dirty ? '● nesačuvano' : 'sačuvano') + ` · ESP32/tactics/${ed.name}.py`;
  $('edState').classList.toggle('dirty', dirty);
  return dirty;
}

function fillTacticSelects() {                  // jedna lista taktika (gore); editor uvek prikazuje izabranu
  const names = [...info.tactics];
  if (ed && !names.includes(ed.name)) names.push(ed.name);        // nova, još nesačuvana taktika iz editora
  const cur = ed ? ed.name : $('tactic').value;
  $('tactic').innerHTML = names.map(t => `<option>${t}</option>`).join('');
  if (names.includes(cur)) $('tactic').value = cur;
}

let edCheckSeq = 0;
async function edCheck() {
  const seq = ++edCheckSeq;
  try {
    const d = await api('/api/check', { source: ed.editor.text() });
    if (seq === edCheckSeq && ed) edDiagnostics(d.diagnostics);
  } catch (e) { /* server busy or gone: ignore */ }
}

// ---- nacrt putanje dok se piše (plan S7) i krst za x, y (plan S8) ----

let edPrevSeq = 0, autoSimTimer = null;
async function edPreview() {
  if (!ed) return;
  const seq = ++edPrevSeq;
  try {
    const p = await api('/api/preview', { source: ed.editor.text(), side: $('side').value, mode: $('mode').value });
    if (seq !== edPrevSeq || !ed) return;
    ed.preview = p;
    view.setPreview(p);
    edCursor(ed.editor.cursorLine());
    const note = p.error ? `nacrt: red ${p.error.line}: ${p.error.msg}` : p.truncated ? `nacrt: ${p.truncated}`
      : `nacrt: ${p.cmds.filter(c => c.kind !== 'turn').length} pokreta, ~${p.t.toFixed(1)} s`;
    $('edDraft').textContent = note;
    $('edDraft').className = 'dim small' + (p.error ? ' err' : '');
    clearTimeout(autoSimTimer);                            // auto-sim: prava simulacija kad se stane sa kucanjem
    if ($('autoSim').checked && !live && !p.error && !p.truncated && p.t < 40) autoSimTimer = setTimeout(() => simulate(play.t), 1200);
  } catch (e) { /* server zauzet: sledeća izmena */ }
}

function edCursor(line) {
  if (!ed) return;
  view.highlightPreview(line);
  const p = ed.preview, side = $('side').value;
  const c = p && p.cmds ? [...p.cmds].reverse().find(k => k.line === line && k.target) : null;
  if (!c) { view.setCursorPoint(null); return; }
  const [fx, fy] = c.target;
  const tx = mirrorX(fx, side, REF_SIDE);          // u koordinatama taktike (žuta)
  view.setCursorPoint([fx, fy], `x = ${Math.round(tx)} mm od leve ivice · y = ${Math.round(fy)} mm od donje ivice`);
}

function edChanged(text) {
  if (!ed) return;
  const dirty = edState();
  try {
    if (dirty) localStorage.setItem('eurosim.draft.' + ed.name, JSON.stringify({ text, sha: ed.sha }));
    else localStorage.removeItem('eurosim.draft.' + ed.name);
  } catch (e) { /* ignore */ }
  edCheck();
}

async function edLoad(name) {
  let source = '', sha = null;
  try { const d = await api('/api/tactic/' + encodeURIComponent(name)); source = d.source; sha = d.sha; }
  catch (e) { msg(e.message, true); return; }
  ed.name = name; ed.sha = sha; ed.saved = source;
  let text = source;
  try {
    const dr = JSON.parse(localStorage.getItem('eurosim.draft.' + name) || 'null');
    if (dr && dr.text !== source) {
      if (dr.sha === sha) { text = dr.text; msg(`${name}: vraćene su tvoje nesačuvane izmene`); }
      else { localStorage.removeItem('eurosim.draft.' + name); msg(`${name}: fajl je promenjen na disku, stari nesačuvan nacrt je odbačen`, true); }
    }
  } catch (e) { /* ignore */ }
  ed.editor.setText(text);
  edMarkKey = '';
  fillTacticSelects();
  edState();
  edCheck();
  edPreview();
  if (run) edMarks();
}

async function edSave(force = false) {
  const body = { name: ed.name, source: ed.editor.text(), sha: ed.sha };
  try {
    const d = await api('/api/tactic/save', body);
    ed.sha = d.sha; ed.saved = body.source.endsWith('\n') ? body.source : body.source + '\n';
    try { localStorage.removeItem('eurosim.draft.' + ed.name); } catch (e) { /* ignore */ }
    info = await api('/api/info');
    fillTacticSelects();
    edState();
    msg(info.where && info.where.mode !== 'repo' ? `sačuvano SAMO na ovom računaru: ${info.where.tactics}/${ed.name}.py`
      : `sačuvano ESP32/tactics/${ed.name}.py`);
    repo.refresh();
  } catch (e) {
    if (e.status === 409 && !force &&
        confirm(`ESP32/tactics/${ed.name}.py je promenjen na disku pošto si ga otvorio.\n\nDa ga zamenim tvojom verzijom?`)) {
      ed.sha = e.data.sha;
      return edSave(true);
    }
    msg(e.message, true);
  }
}

const NAME_OK = n => /^[A-Za-z_][A-Za-z0-9_]{0,40}$/.test(n);

function askName(title, def) {
  const name = (prompt(title + '\n(slova, cifre i _, ne počinje cifrom)', def) || '').trim();
  if (!name) return null;
  if (!NAME_OK(name)) { msg('ime: samo slova, cifre i _, ne počinje cifrom', true); return null; }
  return name;
}

async function edSaveAs() {
  const name = askName(`Sačuvaj „${ed.name}“ kao:`, ed.name + '_2');
  if (!name || name === ed.name) return;
  let sha = null;
  if (info.tactics.includes(name)) {
    if (!confirm(`ESP32/tactics/${name}.py već postoji.\n\nDa ga zamenim ovim tekstom?`)) return;
    try { sha = (await api('/api/tactic/' + encodeURIComponent(name))).sha; } catch (e) { msg(e.message, true); return; }
  }
  const old = ed.name, oldSha = ed.sha, oldSaved = ed.saved;
  ed.name = name; ed.sha = sha;
  try { localStorage.removeItem('eurosim.draft.' + old); } catch (e) { /* ignore */ }
  await edSave(true);
  if (ed.sha === sha) { ed.name = old; ed.sha = oldSha; ed.saved = oldSaved; fillTacticSelects(); edState(); return; }   // nije sačuvano
  $('tactic').value = name;
}

async function edRename() {
  if (!ed.sha) { msg('prvo sačuvaj taktiku', true); return; }
  if (ed.editor.text() !== ed.saved) { msg('sačuvaj izmene pre preimenovanja', true); return; }
  const name = askName(`Preimenuj „${ed.name}“ u:`, ed.name);
  if (!name || name === ed.name) return;
  try {
    await api('/api/tactic/rename', { name: ed.name, new: name });
    info = await api('/api/info');
    ed.name = name; $('tactic').value = name;
    fillTacticSelects(); edState();
    msg(`preimenovano u ESP32/tactics/${name}.py`);
  } catch (e) { msg(e.message, true); }
}

async function edDelete() {
  if (!confirm(`Obrisati ESP32/tactics/${ed.name}.py?\n\nU repou se vraća preko git-a; van repoa ga više nema.`)) return;
  try {
    await api('/api/tactic/delete', { name: ed.name });
    try { localStorage.removeItem('eurosim.draft.' + ed.name); } catch (e) { /* ignore */ }
    info = await api('/api/info');
    msg(`obrisano: ${ed.name}`);
    await edLoad(info.tactics.includes('primer') ? 'primer' : info.tactics[0]);
  } catch (e) { msg(e.message, true); }
}

function edNew() {
  const name = askName('Ime nove taktike:', 'nova');
  if (!name) return;
  if (info.tactics.includes(name)) { msg(`${name} već postoji`, true); return; }
  ed.name = name; ed.sha = null; ed.saved = '';
  ed.editor.setText(ed.api.template);
  fillTacticSelects();
  edChanged(ed.editor.text());
}

// Kartica Komande: Gambit Micro običnim jezikom (web/komande.js); „Ubaci u kod“ stavlja primer u kod.
function renderApiHelp() {
  if (!ed) return;
  renderCommands($('apiList'), ed.api, $('apiFilter').value, line => ed.editor.insertLine(line));
}

// Kartice ispod koda: Problemi | Komande (Gambit Micro; ranije fioka „📖 Commands“ preko stola).
function edTab(id) {
  for (const o of document.querySelectorAll('.ed-tabs button')) { o.classList.toggle('on', o.dataset.tab === id); $(o.dataset.tab).hidden = o.dataset.tab !== id; }
  if (id === 'edCommands') $('apiFilter').focus();
}

// Red komandi Taktika: „✎ Editor“ samo dok je editor zatvoren, auto-simulacija samo dok je otvoren.
function edToolbar(open) {
  $('edOpen').hidden = open;
  const a = $('autoSimWrap');
  if (a) a.hidden = !open;
}

// Otvaranje: prostor Taktike (bočna traka) i „✎ Editor“; zatvaranje: „×“ u traci editora. Promena prostora editor
// samo sakrije (panel editor postoji samo u Taktikama), ne zatvara ga: tekst i nesačuvane izmene ostaju.
function openEditor() {
  if (ed || edOpening) return;
  edOpening = toggleEditor().catch(e => msg('editor: ' + e.message, true)).finally(() => { edOpening = null; });
}

async function toggleEditor() {
  if (ed) {
    $('editorPane').hidden = true; edToolbar(false);                     // panel editor prati hidden
    view.setPreview(null); view.setCursorPoint(null);
    ed.editor.flush();                                                   // poslednje izmene (< 600 ms) u nacrt
    clearTimeout(autoSimTimer);                                          // (flush može da pokrene edCheck, ne i auto-sim)
    ed.editor.view.destroy(); ed = null;
    store.set({ edUnsaved: false });                                     // Live / Pošalji sada koriste fajl
    fillTacticSelects();
    return;
  }
  const { TacticEditor } = await import('./editor.js');
  const tapi = await api('/api/tacapi');
  $('editorPane').hidden = false; edToolbar(true);
  ed = { api: tapi, name: $('tactic').value, sha: null, saved: '' };
  ed.editor = new TacticEditor($('edHost'), { api: tapi, onChange: edChanged, onRun: () => simulate(), onSave: () => edSave(), onSaveAs: () => edSaveAs(),
    onEdit: () => edPreview(), onCursor: line => edCursor(line) });
  renderApiHelp();
  await edLoad(ed.name);
}

// ---------------- live ----------------

function liveSend(c) {                          // true = poslato (ili čeka otvaranje veze), false = nema sesije / veza zatvorena
  return !!(live && live.s.command(c));
}

function setFollow(on) {                        // „Prati“: vreme prati sesiju uživo
  if (!live) return;
  live.follow = on;
  $('followBtn').classList.toggle('on', on);
  $('play').textContent = on ? '⏸' : '▶';
}

function liveRebuild() {
  const L = live;
  if (!L || !L.dirty || !L.raw.frames.length) return;
  L.dirty = false;
  const first = !run || run.live !== L;
  if (first) { run = buildRun({ meta: {}, result: {}, events: [], cols: {} }); L.done = { f: 0, e: 0 }; }
  run = appendRun(run, L.raw.frames.slice(L.done.f), L.raw.events.slice(L.done.e));   // samo ono što je novo
  L.done = { f: L.raw.frames.length, e: L.raw.events.length };
  run.meta = L.raw.meta || {};
  run.live = L;
  view.setRun(run);
  view.setVisibility({ odom: $('showOdom').checked, targets: $('showTargets').checked });
  if (first) charts.setRun(run); else charts.update(run);
  renderSteps(); renderLog(); renderMarks();
  $('slider').max = Math.max(0, run.cols.t.length - 1);
  if (L.follow) play.t = run.duration;
  show();
  bridgeSnap(run.duration);                     // traka prati sesiju uživo i kad se vreme vrati unazad
}

async function startLive() {
  if (live) return;
  setPlaying(false);
  const q = new URLSearchParams({ tactic: $('tactic').value, side: $('side').value, obstacles: JSON.stringify(opponents),
    elements: (a => (a === true ? '1' : a === false ? '0' : JSON.stringify(a)))(elementsArg()) });
  const src = lidarSpec(store.get().sources, store.get().lidarFiles);   // Izvori: odakle dolaze krugovi lidara (hibrid b)
  const lidarHost = src === 'robot' ? ($('rHost').value.trim() || 'eurokik.local') : null;   // traka u hibridu: „lidar: host“
  if (src === 'robot') {
    q.set('lidar', 'robot:' + lidarHost);
    if ($('rPass').value) q.set('lidar_pw', $('rPass').value);
  } else if (src !== 'sim') q.set('lidar', src);
  if (ed) {                                     // editor text (saved or not) is the tactic in Live too
    try { q.set('stage', (await api('/api/stage', { name: ed.name, source: ed.editor.text() })).stage); }
    catch (e) { msg(e.message, true); return; }
  }
  if (live) return;                             // u međuvremenu (await iznad) pokrenuta druga sesija
  const s = connect({ engine: 'sim', ...Object.fromEntries(q) });      // /ws/session (isto što i stari /ws/live)
  live = { s, raw: { meta: null, frames: [], events: [] }, follow: true, dirty: false, screen: null, lidarSrc: src, lidarHost,
    edText: !!(ed && ed.editor.text() !== ed.saved) };                // pokrenuta sa nesačuvanim tekstom editora
  store.set({ drive: 'sim' });                    // izbor u bočnoj traci = vrsta sesije
  sessionHello(s);
  bridgeSession();                                // red komandi Vožnja: Naoruži, Povuci činč, Test... Završi (po hello)
  $('run').disabled = true; $('result').style.display = 'none';
  esp.setEnabled(true);
  setFollow(true);
  msg('uživo: robot je upaljen, ESP povezan sa STM32 · ESP tasteri ili Naoruži / Test');
  const mine = () => live && live.s === s;
  s.on('data', m => {
    if (!mine()) return;
    const L = live;
    store.set({ paused: !!m.paused, speed: m.speed ?? 1 });
    if (m.meta) { L.raw.meta = m.meta; setRealtime(!!m.meta.realtime, m.meta.lidar_source); }
    $('bandCord').hidden = m.mec !== 'NAORUZAN';         // naoružan: čeka činč (dugme na timeline-u)
    if (m.frames.length) { L.raw.frames.push(...m.frames); L.dirty = true; }
    if (m.events.length) {
      L.raw.events.push(...m.events); L.dirty = true;
      for (const e of m.events) {
        if (e[1] === 'screen') L.screen = { t: e[0], ...e[2] };
        else if (e[1] === 'lidar') L.lidar = { t: e[0], ...e[2] };
        else if (e[1] === 'buzzer') esp.buzz(e[2], m.speed || 1);
      }
      lidarToStore(m.events, 'sim');
    }
    if (L.follow) {
      if (L.screen) esp.setScreen(L.screen);
      view.setLidar(L.lidar && m.t - L.lidar.t <= LIDAR_HOLD_MS ? L.lidar : null);
      const f = m.frames[m.frames.length - 1];
      if (f) {
        view.setPose(f);
        $('time').textContent = `${secs(f.t)} s · uživo ×${m.speed}${m.paused ? ' · pauza' : ''}`;
      }
    }
    const pb = $('pauseBtn'), pt = m.paused ? '▶ Nastavi' : '⏸ Pauza';
    if (pb.textContent !== pt) { pb.textContent = pt; pb.title = m.paused ? 'Nastavi simulaciju' : 'Pauziraj simulaciju'; }
    pb.classList.toggle('on', !!m.paused);
  });
  s.on('end', m => {
    if (live && !mine()) return;                 // kraj neke ranije sesije: ne dira trenutnu
    stopLiveUi();
    load(m.run, null, 1e12);
    msg('sesija uživo je završena: pusti je ili sačuvaj', false, OPEN_SNIMCI);
  });
  s.on('error', m => {
    if (!mine()) return;
    msg('uživo: ' + m.error.split('\n')[0], true);
    console.error(m.error);
  });
  s.on('close', ev => sessionClosed(s, ev, 'veza sesije uživo je zatvorena'));
}

// Veza sesije zatvorena: stari UI se gasi; komanda koja je čekala otvaranje (npr. STOP) a nije poslata se javlja.
function sessionClosed(s, ev, text) {
  const stop = (ev.unsent || []).some(c => c[0] === 'stop');
  if (live && live.s === s) { stopLiveUi(); msg(text, true); }
  if (stop) notice('STOP nije poslat: veza zatvorena');
}

// Pravi uređaj u Live-u (lidar sa robota): brzina ×1 i bez pauze, jer uređaj radi u stvarnom vremenu.
function setRealtime(on, source) {
  $('pace').disabled = on; $('pauseBtn').disabled = on;
  if (on) { $('pace').value = '1'; msg('uživo sa pravim lidarom (' + source + '): radi na ×1, bez pauze'); }
}

function lidarToStore(events, kind) {           // poslednji krug iz paketa -> Senzori → Lidar (store.lidarScan)
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e[1] === 'lidar') { store.set({ lidarScan: { t: e[0], ...e[2], wall: performance.now(), kind } }); return; }
  }
}

function fillLidarSources() {                   // snimci lidara za Izvori (lidar: snimak)
  store.set({ lidarFiles: info.lidar_files || [] });
}

function stopLiveUi() {
  if (!live) return;
  view.setLidar(null);
  setRealtime(false);
  api('/api/info').then(i => { info = i; fillLidarSources(); }).catch(() => {});   // nov snimak lidara u listi
  try { live.s.close(); } catch (e) { /* ignore */ }
  if (live.virtual) api('/api/vrobot', { action: 'stop' }).catch(() => {});   // virtuelni robot ne sme da ostane da radi
  live = null;
  bridgeSession();                              // red komandi Vožnja: opet „▶ Pokreni sesiju“
  $('bandCord').hidden = true;
  $('run').disabled = false;
  esp.setEnabled(false);
}

// ---------------- robot (F5) ----------------

function liveData(m) {                          // shared by Live and Robot: append, follow
  const L = live; if (!L) return null;
  if (m.meta) L.raw.meta = m.meta;
  if (m.frames.length) { L.raw.frames.push(...m.frames); L.dirty = true; }
  if (m.events.length) {
    L.raw.events.push(...m.events); L.dirty = true;
    for (const e of m.events) if (e[1] === 'lidar') { L.lidar = { t: e[0], ...e[2] }; L.lidarWall = performance.now(); }   // lidar pravog robota
    lidarToStore(m.events, 'robot');
  }
  const f = m.frames[m.frames.length - 1];
  if (L.follow && f) view.setPose(f);
  if (f) L.tLast = f.t;                         // vreme robota (telemetrija); lidar stao = nema novog kruga
  if (L.follow) {                               // bez frame-ova (STM32 nije povezan) nema vremena robota: staro po satu
    const age = L.tLast != null ? L.tLast - L.lidar?.t : performance.now() - L.lidarWall;
    view.setLidar(L.lidar && age <= 2 * LIDAR_HOLD_MS ? L.lidar : null);
  }
  return f;
}

function startRobot(host, password, label, virtual = false) {
  if (live) return;
  setPlaying(false);
  if (izvori) izvori.close();
  const s = connect({ engine: 'robot', host, password });         // /ws/session (isto što i stari /ws/robot)
  live = { kind: 'robot', s, raw: { meta: null, frames: [], events: [] }, follow: true, dirty: false, host, virtual };
  store.set({ drive: 'robot' });                  // izbor u bočnoj traci = vrsta sesije (npr. dijalog otvoren iz SIM-a)
  sessionHello(s);
  bridgeSession();                                // red komandi Vožnja: Pošalji, Pošalji i pokreni... Prekini vezu (po hello)
  $('run').disabled = true; $('result').style.display = 'none';
  esp.setEnabled(false); esp.setScreen(null);     // kartice ESP nema uz robota (robot ne šalje ekran)
  setFollow(true);
  msg(`robot ${label || host}: povezivanje…`);
  const mine = () => live && live.s === s;
  s.on('data', m => {
    if (!mine()) return;
    const f = liveData(m);
    store.set({ telemetry: m.age != null, linkAge: m.age ?? null,      // age null = još nijedan paket (traka: Veza)
      running: m.running || null,                                      // taktika koja radi na robotu (traka: Izvor)
      robotMec: m.esp_mec ?? null, robotLidar: m.lidar_state ?? null, robotLidarSeen: !!m.lidar_seen });   // Senzori → Lidar
    if (f && live.follow) $('time').textContent = `${secs(f.t)} s · robot`;
  });
  s.on('state', m => {                            // server: veza ok / stale (> 1.5 s) / lost (> 5 s), šalje se na promenu
    if (mine()) store.set({ linkState: m.link, connAge: m.age ?? null });
  });
  s.on('reply', m => {
    if (!mine()) return;
    const text = `${m.cmd}: ${m.ok ? 'OK' : 'ERR'} ${(m.lines || []).slice(-2).join(' · ')}`;
    msg(text, !m.ok);
    if (m.cmd === 'lidar') store.set({ lidarReply: m });            // Senzori → Lidar: Upali lidar, Snimi krugove
    if (m.cmd === 'STAT' && m.ok) msg(`robot ${host}: povezan · ` + (m.lines || []).slice(0, 3).join(' · '));
  });
  s.on('end', m => {
    if (live && !mine()) return;
    stopLiveUi();
    if (m.run) {
      load(m.run, null, 1e12);
      msg('sesija sa robotom je završena: pusti je, sačuvaj ili uporedi sa simulacijom', false, OPEN_SNIMCI);
    }
    else msg('veza sa robotom je prekinuta (telemetrija nije stigla)');
  });
  s.on('error', m => { if (mine()) msg('robot: ' + m.error.split('\n')[0], true); });
  s.on('close', ev => sessionClosed(s, ev, 'veza sa robotom je zatvorena'));
}

function robotTactic() {
  const name = curTactic();
  return [name, ed && ed.name === name ? ed.editor.text() : null];
}

// ---------------- compare ----------------

function alignOf(r) {                           // time of the first tactic start (0 if none)
  const e = r && r.events && r.events.find(x => x[1] === 'tactic');
  return e ? e[0] : 0;
}

function setRef(r, name, saved = null) {       // saved: ime sačuvanog snimka (lista u Snimcima ga označi 📌)
  ref = r;
  view.setCompare(r);
  $('cmpName').textContent = r ? `referenca: ${name}` : '';
  $('cmpName').title = r ? `Referenca (crta se preko snimka): ${name}` : '';
  $('cmpClear').hidden = !r;
  store.set({ refName: r ? saved : null, refLabel: r ? name : null });
  if (run) show();
}

// ---------------- start ----------------

async function main() {
  info = await api('/api/info');
  fillLidarSources();
  REF_SIDE = info.ref_side || REF_SIDE;
  $('tactic').innerHTML = info.tactics.map(t => `<option>${t}</option>`).join('');
  try {
    const sel = JSON.parse(localStorage.getItem('eurosim.sel') || '{}');
    for (const k of ['tactic', 'side', 'mode']) if (sel[k]) $(k).value = sel[k];
  } catch (e) { /* ignore */ }
  refreshRuns();                                  // Snimci i „Uporedi sa…“ (detaljna lista)
  const setInfo = i => { info = i; };
  repo = mountRepo({ store, msg, getInfo: () => info, setInfo, onPulled: fillTacticSelects });   // traka, dijalog, značka
  profile = mountProfile({ msg, setInfo });
  view = new FieldView($('view'), info);
  buildIrBox(); renderIr(0, 0xFF);
  charts = new Charts($('charts'), t => seek(t));
  view.onHover = p => {
    if (!p) { $('cursor').textContent = ''; return; }
    const side = run ? run.meta.side : $('side').value;
    const tx = mirrorX(p[0], side, REF_SIDE);
    $('cursor').textContent = `sto ${Math.round(p[0])}, ${Math.round(p[1])}` +
      (side !== REF_SIDE ? `   ·   u taktici (${STRANA[REF_SIDE]}) ${Math.round(tx)}, ${Math.round(p[1])}` : '') +
      '   (dupli klik: kopiraj · Alt+klik: u editor)';
  };
  view.onPreviewClick = line => { if (ed) ed.editor.reveal(line); };
  view.onAltPick = p => {                                   // Alt+klik: tačka sa mape u editor (koordinate taktike)
    if (!ed) { msg('Alt+klik ubacuje tačku u taktiku: otvori editor (Taktike, ✎ Editor)'); return; }
    if (store.get().ws !== 'taktike') { msg('Alt+klik ubacuje tačku u editor: samo u Taktikama (tamo je editor)'); return; }
    const side = $('side').value;
    const x = Math.round(mirrorX(p[0], side, REF_SIDE) / 10) * 10, y = Math.round(p[1] / 10) * 10;
    ed.editor.putPoint(x, y);
    msg(`goto ${x}, ${y} (koordinate taktike, strana ${STRANA[REF_SIDE]})`);
  };
  view.onPick = p => {
    const side = run ? run.meta.side : $('side').value;
    const x = mirrorX(p[0], side, REF_SIDE);
    const s = `${Math.round(x)}, ${Math.round(p[1])}`;
    navigator.clipboard?.writeText(s);
    msg(`kopirano ${s} (koordinate taktike)`);
  };

  $('run').onclick = () => simulate();
  shell = mountShell({ store, command: sessionCommand, legacy: {          // okvir: statusna traka, bočna traka, Esc = STOP
    notice,                                                               // npr. „Sesija radi: prvo je završi“
    openEditor,
    openRuns: () => { $('msgAct').hidden = true; refreshRuns(); },     // Snimci: lista sa diska (i posle git pull)
    loadRun,
    clearRef: () => setRef(null),                                    // ✕ na oznaci reference na stolu (panels/teren.js)
    openSources: anchor => izvori.toggle(anchor),                    // blok Izvori (dok sesija radi: samo čitanje)
    openRepo: () => repo.toggle(),                                   // stavke Repo i Profil u bočnoj traci
    openProfile: () => profile.toggle(),
    resizeView: () => { view.resize(); charts.resize(); },        // panel teren posle premeštanja
    showErrors: () => {
      if (shell) shell.openCard('dnevnik');                           // sklopljen (npr. u Taktikama): otvori ga
      const errs = $('log').querySelectorAll('div.err');
      if (errs.length) errs[errs.length - 1].scrollIntoView({ block: 'nearest' });
    },
  } });
  esp = new EspPanel($('espPanel'), c => liveSend(c));
  esp.setEnabled(false);
  try { opponents = JSON.parse(localStorage.getItem('eurosim.opp') || '[]'); } catch (e) { opponents = []; }
  // Uređivač protivnika / kamenoloma je u kartici Postavka stola: sklopljena se otvori, a njen sadržaj (kad nema mesta u
  // koloni, kartica se skuplja i skroluje sama) se pomeri tako da se uređivač vidi.
  const openSto = () => {
    shell.openCard('sto');
    const box = $('ws-sto'), edEl = !$('oppEdit').hidden ? $('oppEdit') : !$('elEdit').hidden ? $('elEdit') : null;
    if (box && edEl) box.scrollTop += edEl.getBoundingClientRect().top - box.getBoundingClientRect().top;
  };
  view.onOppSelect = i => { oppSel = i; refreshOpponents(); if (i >= 0) openSto(); };
  view.onOppMove = (i, final) => {
    if (i === oppSel) { $('oppX').value = opponents[i].x; $('oppY').value = opponents[i].y; }
    opponentsChanged(final);
  };
  refreshOpponents();
  $('addOpp').onclick = () => {
    opponents.push({ name: 'protivnik ' + (opponents.length + 1), x: 1500, y: 1000, w: 300, h: 300, th: 0, z: 350, r: 0 });
    oppSel = opponents.length - 1;
    refreshOpponents(); openSto();
    opponentsChanged(true);
  };
  $('addPami').onclick = () => {              // PAMI: mali robot na protivnikovoj strani, kreće u poslednjih 15 s
    const blue = $('side').value === 'zuta', n = opponents.filter(o => o.kind === 'pami').length;
    opponents.push({ name: 'PAMI ' + (n + 1), kind: 'pami', x: blue ? 2900 : 100, y: 1700 - n * 150, w: 150, h: 120, th: blue ? 180 : 0,
      z: 130, r: 0, tactic: (info.opp_tactics || []).includes('pami_napred') ? 'pami_napred' : undefined });
    oppSel = opponents.length - 1; refreshOpponents(); openSto(); opponentsChanged(true);
  };
  $('oppTac').onchange = editOpponent; $('oppSeed').onchange = editOpponent;
  $('oppDel').onclick = () => { opponents.splice(oppSel, 1); oppSel = -1; refreshOpponents(); opponentsChanged(true); };
  $('oppClose').onclick = () => { oppSel = -1; refreshOpponents(); };       // samo zatvori: protivnik ostaje
  for (const id of ['oppX', 'oppY', 'oppW', 'oppH', 'oppTh', 'oppZ', 'oppRound']) $(id).onchange = editOpponent;
  // Red komandi Vožnja (panels/voznja-alati.js): bez sesije „Izvori ▾“ i „▶ Pokreni sesiju“ (SIM: Live sa izabranim
  // lidarom; ROBOT: prozorčić „Poveži robota“ sa trake: host, lozinka, Poveži, Virtuelni robot).
  izvori = mountIzvori({ store, setDrive: d => shell.setDrive(d), openConnect: a => shell.openConnect(a) });
  $('sessStart').onclick = () => {
    if (live) return;
    if (store.get().drive === 'robot') shell.openConnect($('sessStart')); else startLive();
  };
  $('rHost').onchange = () => { try { localStorage.setItem('eurosim.host', $('rHost').value); } catch (e) { /* ignore */ } };
  $('rConnect').onclick = () => {
    try { localStorage.setItem('eurosim.host', $('rHost').value); } catch (e) { /* ignore */ }
    startRobot($('rHost').value.trim(), $('rPass').value);
  };
  let host = null;
  try { host = localStorage.getItem('eurosim.host'); } catch (e) { /* ignore */ }
  $('rHost').value = host || 'eurokik.local';
  $('rVirtual').onclick = async () => {
    msg('pokrećem virtuelnog robota (pravi ESP kod, simuliran STM32) na 127.0.0.1…');
    try {
      const d = await api('/api/vrobot', { action: 'start', tactic: curTactic(), side: $('side').value, obstacles: opponents });
      startRobot(d.host, d.password, 'virtual (127.0.0.1)', true);
    } catch (e) { msg(e.message, true); }
  };
  $('rPush').onclick = () => { const [n, src] = robotTactic(); liveSend(['push', n, src]); msg(`šaljem ${n}…`); };
  $('rRun').onclick = () => {
    const [n, src] = robotTactic();
    const strana = STRANA[$('side').value] || $('side').value;
    if (live && live.host !== '127.0.0.1' &&
        !confirm(`Pokrenuti „${n}“ na ${live.host} sada (${strana})?\n\nROBOT ĆE SE POMERITI. Slobodan prostor, ruka na prekidaču motora.`)) return;
    liveSend(['push', n, src]); liveSend(['run', n, $('side').value]); msg(`pokrećem ${n} na robotu…`);
  };
  $('cmpPin').onclick = () => {                 // tokom Live-a snimak i dalje raste (deli nizove): referenca je kopija
    if (!run) return;
    const saved = live ? null : store.get().runName;
    setRef(live ? snapshotRun(run) : run, saved || `${run.meta.tactic || '?'} (${run.meta.mode})`, saved);
  };
  $('cmpClear').onclick = () => setRef(null);
  $('cmpRun').onchange = async e => {
    const n = e.target.value; e.target.value = '';
    if (!n) return;
    try { setRef(buildRun(await api('/api/runs/' + encodeURIComponent(n) + '?ref=1')), n, n); } catch (er) { msg(er.message, true); }
  };
  $('endBtn').onclick = () => liveSend(['quit']);              // Završi (SIM) / Prekini vezu (ROBOT)
  $('armBtn').onclick = () => liveSend(['arm', curTactic(), $('side').value]);
  $('testBtn').onclick = () => liveSend(['test', curTactic(), $('side').value]);
  $('result').onclick = () => $('result').classList.toggle('mini');
  try { tableEl = JSON.parse(localStorage.getItem('eurosim.el') || 'null'); } catch (e) { tableEl = null; }
  drawElements();
  view.onElSelect = i => { elSel = i; drawElements(); if (i >= 0) openSto(); };
  view.onElMove = (i, final) => { if (final) elementsChanged(true, true); else refreshElPanel(); };
  $('showElements').onchange = () => { elSel = -1; drawElements(); elementsChanged(true); };
  $('elLess').onclick = () => elEdit(e => { e.stones = Math.max(0, (e.stones ?? 3) - 1); });
  $('elMore').onclick = () => elEdit(e => { e.stones = Math.min(6, (e.stones ?? 3) + 1); });
  $('elRot').onclick = () => elEdit(e => { e.th = ((e.th || 0) + 90) % 180; });
  $('elDel').onclick = () => { const l = curElements(); l.splice(elSel, 1); tableEl = l; elSel = -1; drawElements(); elementsChanged(true); };
  $('elClose').onclick = () => { elSel = -1; drawElements(); };
  $('elReset').onclick = () => { tableEl = null; elSel = -1; drawElements(); elementsChanged(true); msg('sto vraćen na pravila 2027'); };
  $('scenSave').onclick = saveScenario;
  $('scenLoad').onchange = e => { const n = e.target.value; e.target.value = ''; if (n) loadScenario(n); };
  fillScenarios();
  $('rulesLook').onchange = e => view.setTableLook(e.target.checked ? 'rules' : 'grid');
  $('edOpen').onclick = openEditor;
  $('edClose').onclick = () => { if (ed && !edOpening) toggleEditor(); };
  edToolbar(false);
  $('tactic').addEventListener('change', e => { if (ed) edLoad(e.target.value); });
  // Strana/taktika: u Live-u robot (dok miruje) prelazi na START izabrane strane (ranije je ostajao na
  // strani sa kojom je Live pokrenut); inače se prikazani snimak odmah ponovo simulira za novu stranu.
  const selChanged = () => {
    edPreview();
    if (live && live.kind !== 'robot') liveSend(['side', curTactic(), $('side').value]);
    else if (!live && run && run.meta && !run.meta.host) simulate();
  };
  $('side').addEventListener('change', selChanged);
  $('tactic').addEventListener('change', () => { if (live && live.kind !== 'robot') selChanged(); });
  $('edNew').onclick = edNew;
  $('edSave').onclick = () => edSave();
  $('edFileMenu').onchange = e => {
    const a = e.target.value; e.target.value = '';
    if (a === 'saveas') edSaveAs(); else if (a === 'rename') edRename(); else if (a === 'delete') edDelete();
  };
  $('viewMenuBtn').onclick = () => { $('viewMenu').hidden = !$('viewMenu').hidden; };
  document.addEventListener('pointerdown', e => {
    if (!$('viewMenu').hidden && !e.target.closest('#viewMenu, #viewMenuBtn')) $('viewMenu').hidden = true;
  });
  $('apiFilter').oninput = renderApiHelp;
  for (const b of document.querySelectorAll('.ed-tabs button')) b.onclick = () => edTab(b.dataset.tab);
  window.addEventListener('beforeunload', e => { if (ed && ed.editor.text() !== ed.saved) e.preventDefault(); });
  $('cordBtn').onclick = () => liveSend(['cord']);
  $('bandCord').onclick = () => liveSend(['cord']);
  $('pace').onchange = e => liveSend(['speed', +e.target.value]);
  $('pauseBtn').onclick = () => liveSend(['pause', !$('pauseBtn').classList.contains('on')]);
  $('followBtn').onclick = () => setFollow(!live.follow);
  setInterval(liveRebuild, 250);
  $('play').onclick = () => setPlaying(!play.playing);
  $('speed').onchange = e => { play.speed = +e.target.value; };
  $('prevFrame').onclick = () => frameJump(-1);
  $('nextFrame').onclick = () => frameJump(1);
  $('prevStep').onclick = () => stepJump(-1);
  $('nextStep').onclick = () => stepJump(1);
  $('slider').oninput = e => run && seek(run.cols.t[+e.target.value]);
  $('showProto').onchange = () => { if (run) { renderLog(); show(); } };
  $('logErrOnly').onchange = () => { if (run) { renderLog(); show(); } };
  const vis = () => view.setVisibility({ odom: $('showOdom').checked, targets: $('showTargets').checked });
  $('showOdom').onchange = () => { vis(); if (run) show(); };
  $('showTargets').onchange = vis;
  $('showIr').onchange = e => view.setShowIr(e.target.checked);
  $('showLidar').onchange = e => view.setShowLidar(e.target.checked);
  const pref = (k, el, apply) => {                 // izbor u Prikaz ▾ se pamti (localStorage)
    try { const v = localStorage.getItem('eurosim.' + k); if (v != null) { if (el.type === 'checkbox') el.checked = v === '1'; else el.value = v; } } catch (er) { /* ignore */ }
    const go = () => { apply(el.type === 'checkbox' ? el.checked : el.value);
      try { localStorage.setItem('eurosim.' + k, el.type === 'checkbox' ? (el.checked ? '1' : '0') : el.value); } catch (er) { /* ignore */ } };
    el.addEventListener('change', go); go();
  };
  pref('labels', $('labelMode'), v => view.setLabelMode(v));
  pref('legend', $('showLegend'), v => { $('legend').hidden = !v; });
  $('showDraft').onchange = e => view.setShowPreview(e.target.checked);
  $('mode').addEventListener('change', () => edPreview());
  $('markSize').onchange = e => { view.setMarkerScale(+e.target.value); try { localStorage.setItem('eurosim.mark', e.target.value); } catch (er) { /* ignore */ } };
  try { const k = localStorage.getItem('eurosim.mark'); if (k) { $('markSize').value = k; view.setMarkerScale(+k); } } catch (er) { /* ignore */ }
  $('follow').onchange = e => { view.follow = e.target.checked; };
  $('cam3d').onclick = () => { view.setCamera('3d'); $('cam3d').classList.add('on'); $('cam2d').classList.remove('on'); };
  $('cam2d').onclick = () => { view.setCamera('top'); $('cam2d').classList.add('on'); $('cam3d').classList.remove('on'); };
  $('save').onclick = async () => {
    const name = prompt('Ime snimka (čuva se u studio/runs/; prazno = datum_taktika_strana):', '');
    if (name === null) return;
    try {
      const d = await api('/api/runs/save', { name });
      fillRuns(d.runs);
      if (!live) store.set({ runName: d.saved });             // snimak koji gledaš je sada taj sačuvan
      msg(`sačuvan snimak ${d.saved}`);
      refreshRuns();
    } catch (e) { msg(e.message, true); }
  };
  document.addEventListener('keydown', e => {
    const tg = e.target;
    if (tg.isContentEditable || (tg.closest && tg.closest('.cm-editor'))) return;
    if (tg.tagName === 'TEXTAREA' || tg.tagName === 'SELECT' ||
        (tg.tagName === 'INPUT' && !['range', 'checkbox', 'button'].includes(tg.type))) return;
    const k = timeKey(e, store.get().ws);           // Senzori: vreme ne radi; Ctrl+Enter samo u Taktikama
    if (k === 'play') { e.preventDefault(); setPlaying(!play.playing); }
    else if (k === 'frame-' || k === 'frame+') { e.preventDefault(); frameJump(k === 'frame-' ? -1 : 1); }
    else if (k === 'step-' || k === 'step+') { e.preventDefault(); stepJump(k === 'step-' ? -1 : 1); }
    else if (k === 'home') seek(0);
    else if (k === 'end') run && seek(run.duration);
    else if (k === 'run') simulate();
    // Esc = STOP: shell/layout.js (hvatanje na window-u, radi i iz editora i polja), ne ovde
  });
  requestAnimationFrame(tick);
  const w = info.where || {};
  msg(w.mode === 'standalone' ? `bez repoa: taktike, profili i snimci u ${w.home}` : `repo ${w.root}: taktike u ESP32/tactics`);
  $('msg').title = JSON.stringify(w, null, 1);     // gde su fajlovi (ranije title natpisa „Eurosim“ u starom redu)
  const moved = migratedNotice(info.migrated);    // jednokratni prenos iz starog foldera simulator/
  if (moved) {                                    // posle završne msg(...) i mountShell: traka ga pokazuje, a u liniji ostaje ceo spisak
    notice(moved, false);
    $('msg').title = moved + '\n\n' + JSON.stringify(w, null, 1);
  }
}

window.eurosim = { get ed() { return ed; }, get run() { return run; }, get view() { return view; }, play, edMarks, store };   // za testove i konzolu
main().catch(e => {
  msg('ne mogu da pokrenem: ' + e.message, true);
  if ($('msg').closest('#parts')) {               // greška pre mountShell: poruka je još u skrivenom #parts
    const row = document.createElement('div');
    row.className = 'tool-row boot-msg';
    row.append($('msg'));
    $('content').prepend(row);
  }
});
