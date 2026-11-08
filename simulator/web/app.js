// Eurosim UI: run a tactic in the simulator, then play back the recording (speed, pause,
// frame / step stepping, scrubbing). All data comes from one recording (server: /api/run).
import { FieldView } from './view3d.js';
import { Charts } from './charts.js';
import { EspPanel } from './esp.js';

const $ = id => document.getElementById(id);
const SIDE_NAME = { plava: 'Blue', zuta: 'Yellow' };
const REASON = { BLOCKED: 'blocked', TIMEOUT: 'timeout', PREEMPTED: 'preempted', MATCH_OVER: 'match over',
  STOPPED: 'stopped', INVALID: 'rejected', NOREPLY: 'no reply', SUPERSEDED: 'superseded', STOP: 'STOP' };
const FIELD_X = 3000;
let REF_SIDE = 'zuta';                // strana za koju se pišu taktike (ESP32/lib/tac.py), stiže sa servera

let info, view, charts, esp, run = null;
let opponents = [], oppSel = -1;
let ref = null;                       // reference run for comparing (pinned or loaded)
let ed = null;                        // {editor, api, name, sha, saved} when the editor is open
let live = null;                       // {ws, raw: {meta, frames, events}, follow, dirty, last}
const play = { t: 0, playing: false, speed: 1, last: 0 };

// ---------------- recording -> run ----------------

function buildRun(d) {
  const cols = d.cols, ts = cols.t;
  const frameAt = t => {                                   // last frame with t <= t
    let lo = 0, hi = ts.length - 1;
    if (hi < 0) return 0;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (ts[m] <= t) lo = m; else hi = m - 1; }
    return lo;
  };
  const steps = [], byIdx = {}, tactics = [], pendingLine = {}, excLines = [];
  for (const [t, kind, x] of d.events) {
    if (kind === 'line') { pendingLine[x[0]] = x[1]; continue; }
    if (kind === 'exception') { if (x.line) excLines.push(x.line); continue; }
    if (kind === 'tactic') {
      tactics.push({ t, name: x[0], side: x[1] });
      for (const k in byIdx) delete byIdx[k];
    } else if (kind === 'step') {
      const s = { idx: x[0], name: x[1], timeout: x[2], next: x[3], t, end: null, ok: null, reason: null, dur: null,
        target: null, line: pendingLine[x[0]] || null };
      delete pendingLine[x[0]];
      steps.push(s); byIdx[x[0]] = s;
    } else if (kind === 'step_end') {
      const s = byIdx[x[0]];
      if (s) Object.assign(s, { end: t, ok: x[2], reason: x[3], dur: x[4] });
    }
  }
  for (const [t, kind, x] of d.events) {                     // GOTO target -> step started at that time
    if (kind !== 'rx' || x.name !== 'GOTO') continue;
    let s = null;
    for (const c of steps) if (c.t <= t + 1) s = c;
    if (s && !s.target) s.target = [x.f.x, x.f.y, x.f.flags & 2 ? null : x.f.theta / 100];   // 2 = NO_THETA
  }
  const log = [];
  for (const [t, kind, x] of d.events) {
    if (kind === 'log') log.push({ t, cls: /^GRESKA|PREKID/.test(x) ? 'err' : '', text: x });
    else if (kind === 'sim') log.push({ t, cls: 'sim', text: '[sim] ' + x.text });
    else if (kind === 'rx' || kind === 'tx') {
      const f = Object.entries(x.f || {}).map(([k, v]) => `${k}=${v}`).join(' ');
      log.push({ t, cls: 'proto', proto: true,
        text: `${kind === 'rx' ? 'ESP→STM' : 'STM→ESP'} ${x.name} #${x.seq} ${f}` });
    }
  }
  const screens = d.events.filter(e => e[1] === 'screen').map(([t, , x]) => ({ t, ...x }));
  const screenAt = t => {
    let r = null;
    for (const sc of screens) { if (sc.t <= t) r = sc; else break; }
    return r;
  };
  return { ...d, frameAt, steps, tactics, excLines, log, screens, screenAt, duration: ts.length ? ts[ts.length - 1] : 0 };
}

// ---------------- formatting ----------------

const f0 = v => v == null ? '–' : Math.round(v).toString();
const f1 = v => v == null ? '–' : v.toFixed(1);
const f2 = v => v == null ? '–' : v.toFixed(2);
const secs = ms => (ms / 1000).toFixed(2);

function stateCells(c, i) {
  const t = c.t[i];
  const dx = Math.hypot(c.x[i] - c.ox[i], c.y[i] - c.oy[i]);
  const match = c.match[i];
  const rem = match == null ? '–' : Math.max(0, (100000 - match) / 1000).toFixed(1) + ' s';
  const ir = c.ir[i] ? ((c.ir[i] & 1 ? 'front ' : '') + (c.ir[i] & 2 ? 'back' : '')) : '–';
  const act = c.act && c.act[i] ? Object.entries(c.act[i]).map(([k, v]) => `${k}=${v}`).join(' ') : '–';
  return [
    ['time', secs(t) + ' s'], ['match left', rem],
    ['flow', c.mec[i] || '–'], ['STM32', c.link[i] ? 'link ok' : 'no link', c.link[i] ? 'good' : 'bad'],
    ['x / y', `${f0(c.x[i])} / ${f0(c.y[i])}`], ['angle', f1(c.th[i]) + '°'],
    ['odom x/y', `${f0(c.ox[i])} / ${f0(c.oy[i])}`], ['odom ∠', f1(c.oth[i]) + '°'],
    ['odom err', f1(dx) + ' mm', dx > 10 ? 'warn' : ''], ['STM phase', c.reg[i] === '' || c.reg[i] == null ? (c.phase[i] || '–') : `${c.phase[i]} ${c.reg[i]}/${c.ms[i]}`],
    ['v', f2(c.v[i]) + ' m/s'], ['v ref', f2(c.v_ref[i])],
    ['ω', f2(c.w[i]) + ' r/s'], ['ω ref', f2(c.w_ref[i])],
    ['wheel L', f2(c.vl[i])], ['wheel R', f2(c.vr[i])],
    ['IR', ir, c.ir[i] ? 'warn' : ''], ['stuck', c.stuck[i] ? 'YES' : 'no', c.stuck[i] ? 'bad' : ''],
    ['actuators', act],
  ];
}

// ---------------- panels ----------------

function renderState(i) {
  const c = run.cols;
  $('stgrid').innerHTML = stateCells(c, i).map(([k, v, cls]) =>
    `<span class="k">${k}</span><span class="v ${cls || ''}">${v}</span>`).join('');
  const t = c.t[i];
  const s = [...run.steps].reverse().find(s => s.t <= t);
  const active = s && (s.end == null || s.end > t);
  $('stepname').textContent = s ? `${s.idx}. ${s.name}` : (c.tac[i] ? 'starting…' : '—');
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
  $('stepnext').textContent = s ? (active ? `running ${secs(t - s.t)} s${s.timeout ? ' / timeout ' + secs(s.timeout) + ' s' : ''}` :
    `finished: ${s.ok ? 'OK' : (REASON[s.reason] || s.reason || 'fail')}`) + (s.next ? ` · next: ${s.next}` : '') : '';
  const m = c.match[i];
  $('matchtime').textContent = m == null ? '' : `match ${secs(m)} s`;
}

function renderSteps() {
  const tb = $('steps').querySelector('tbody');
  tb.innerHTML = '';
  const heads = run.tactics.length > 1 ? [...run.tactics] : [];
  for (const s of run.steps) {
    while (heads.length && heads[0].t <= s.t) {
      const h = heads.shift(), tr = document.createElement('tr');
      tr.innerHTML = `<td></td><td colspan="3" class="dim">▶ ${h.name} · ${SIDE_NAME[h.side] || h.side} · ${secs(h.t)} s</td>`;
      tr.onclick = () => seek(h.t);
      tb.appendChild(tr);
    }
    const tr = document.createElement('tr');
    const res = s.ok == null ? '<span class="res-run">…</span>' : s.ok ? '<span class="res-ok">OK</span>' :
      `<span class="res-fail">${REASON[s.reason] || s.reason || 'FAIL'}</span>`;
    tr.innerHTML = `<td><i class="swatch" style="background:${stepColor(s.idx)}"></i>${s.idx}</td><td title="${s.name}">${s.name}</td><td>${res}</td><td>${s.dur == null ? '' : secs(s.dur)}</td>`;
    tr.onmouseenter = () => view.highlightStep(s.idx);
    tr.onmouseleave = () => view.highlightStep(0);
    tr.onclick = () => { seek(s.t); if (ed && s.line && edShowsRun()) ed.editor.reveal(s.line, false); };
    s.row = tr;
    tb.appendChild(tr);
  }
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
  const el = $('log'), proto = $('showProto').checked;
  el.innerHTML = '';
  run.logEls = [];
  for (const e of run.log) {
    if (e.proto && !proto) continue;
    const d = document.createElement('div');
    d.className = e.cls;
    d.innerHTML = `<span class="t">${secs(e.t)}</span>`;
    d.appendChild(document.createTextNode(e.text));
    d.onclick = () => seek(e.t);
    el.appendChild(d);
    run.logEls.push([e.t, d]);
  }
  logShown = -1;
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
    el.innerHTML = `<b>ROBOT</b> <span class="dim">${run.meta.host} · ${run.meta.tactic || 'no tactic'} · ${SIDE_NAME[run.meta.side] || ''}</span>
      <div class="dim">${secs(run.duration)} s of telemetry · steps OK ${done}/${run.steps.length}${n >= 0 ? ` · last pose ${f0(c.x[n])}, ${f0(c.y[n])}, ${f1(c.th[n])}°` : ''}</div>
      ${bad.map(s => `<div>step ${s.idx} “${s.name}”: ${REASON[s.reason] || s.reason}</div>`).join('')}
      <div class="dim small">pose = robot odometry · 10 Hz telemetry: very short steps may be missed</div>`;
    return;
  }
  const fail = r.fail ? `<div>failed at step ${r.fail[0]} “${r.fail[1]}”: ${REASON[r.fail[2]] || r.fail[2]}</div>` : '';
  const warn = [];
  if (r.start_in_zone === false) warn.push('robot does not start inside its own start zone');
  if (r.errors && r.errors.length) warn.push(...r.errors.slice(-3));
  el.className = r.ok ? 'ok' : 'fail';
  el.style.display = 'block';
  el.innerHTML = `<b>${r.ok ? 'OK' : 'NOT OK'}</b> <span class="dim">${run.meta.tactic} · ${SIDE_NAME[run.meta.side]} · ${run.meta.mode === 'mec' ? 'match' : 'test'}</span>
    ${r.how ? `<div>stopped: ${r.how}</div>` : ''}${fail}
    <div class="dim">steps ${r.done ?? 0}/${r.steps ?? 0} · tactic ${r.ms != null ? secs(r.ms) + ' s' : '–'} · end ${f0(r.pose[0])}, ${f0(r.pose[1])}, ${f1(r.pose[2])}°
    · in own zone at end: ${r.in_own_zone ? 'yes' : 'no'}</div>
    ${warn.map(w => `<div style="color:var(--warn)">⚠ ${w}</div>`).join('')}`;
}

// Timeline (plan S9): traka koraka (od početka do kraja, boja kao na stolu, crveno = neuspeh), zastavice
// NAORUŽAN / ČINČ / upozorenja, senka faze napada (85-100 s meča) i os u sekundama meča.
const STEP_COLORS = ['#4cc9f0', '#f72585', '#b5e48c', '#ffd166', '#9d4edd', '#ff8c42', '#06d6a0', '#ef476f'];
const stepColor = idx => STEP_COLORS[(idx - 1 + STEP_COLORS.length) % STEP_COLORS.length];

function runFlags(r) {
  const out = [];
  for (const l of r.log) {
    if (/^NAORUZAN/.test(l.text)) out.push({ t: l.t, k: 'armed', label: 'ARMED', title: l.text });
    else if (/^CINC: start/.test(l.text)) out.push({ t: l.t, k: 'cord', label: 'CORD', title: 'cord pulled: the match starts' });
    else if (/STM32 restart|nema veze|pad veze|STM32 se ne javlja|ESP restart/.test(l.text)) out.push({ t: l.t, k: 'warn', label: '⚠', title: l.text });
    else if (/^KRAJ meca/.test(l.text)) out.push({ t: l.t, k: 'end', label: 'END', title: 'match over' });
  }
  return out;
}

function renderMarks() {
  $('marks').innerHTML = '';
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
      (s.ok === false ? `\nFAILED: ${s.reason || ''}` : s.ok ? '\nOK' : '') + '\nclick: jump here';
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
    a.title = 'attack phase (85-100 s of the match)';
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
    const e = document.createElement('span'); e.style.left = pct(t0 + s * 1000); e.textContent = s + (s === 0 ? (cord ? ' s match' : ' s') : '');
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
  esp.setScreen(run.screenAt(play.t));
  edMarks();
  view.setFrame(i);
  renderState(i);
  updateSteps(play.t);
  updateLog(play.t);
  charts.setTime(play.t);
  if (ref) view.setCompareTime(play.t - alignOf(run) + alignOf(ref));
  $('slider').value = i;
  $('time').textContent = `${secs(play.t)} / ${secs(run.duration)} s`;
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

function msg(text, err = false) { const m = $('msg'); m.textContent = text; m.className = 'msg' + (err ? ' err' : ''); m.title = text; }

async function api(path, body) {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json();
  if (!r.ok || d.error) { const e = new Error(d.error || r.statusText); e.data = d; e.status = r.status; throw e; }
  return d;
}

function load(d, label, keepTime = null) {
  run = buildRun(d);
  view.setRun(run);
  view.setElements(d.meta && d.meta.elements ? d.meta.elements : []);
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

async function simulate(keepTime = null) {
  if (live) return;
  const body = { tactic: $('tactic').value, side: $('side').value, mode: $('mode').value, obstacles: opponents,
    elements: $('showElements').checked };
  localStorage.setItem('eurosim.sel', JSON.stringify(body));
  if (ed) { body.tactic = ed.name; body.source = ed.editor.text(); }
  $('run').disabled = true;
  msg(`simulating ${body.tactic}…`);
  try {
    const d = await api('/api/run', body);
    load(d, `${body.tactic}: simulated ${secs(d.result.sim_ms)} s in ${d.wall_s} s`, keepTime);
    if (ed && d.diagnostics) edDiagnostics(d.diagnostics);
  } catch (e) {
    if (ed && e.data && e.data.diagnostics) edDiagnostics(e.data.diagnostics);
    msg(e.message.split('\n')[0], true);
    console.error(e);
  } finally {
    $('run').disabled = false;
  }
}

function fillRuns(list) {
  const s = $('runs');
  s.innerHTML = '<option value="">Saved runs…</option>' + list.map(n => `<option>${n}</option>`).join('');
  $('cmpRun').innerHTML = '<option value="">compare with…</option>' + list.map(n => `<option>${n}</option>`).join('');
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
  if (!list.length) el.innerHTML = '<div class="info">no problems found</div>';
  const n = list.filter(d => d.severity === 'error').length, w = list.filter(d => d.severity === 'warning').length;
  $('edCount').textContent = n || w ? `${n} error${n === 1 ? '' : 's'}, ${w} warning${w === 1 ? '' : 's'}` : '✓';
}

function edState() {
  const dirty = ed.editor.text() !== ed.saved;
  $('edState').textContent = (ed.sha ? '' : 'new · ') + (dirty ? '● unsaved' : 'saved') + ` · ESP32/tactics/${ed.name}.py`;
  $('edState').classList.toggle('dirty', dirty);
  return dirty;
}

function fillTacticSelects() {
  const names = [...info.tactics];
  if (ed && !names.includes(ed.name)) names.push(ed.name);
  const opts = names.map(t => `<option>${t}</option>`).join('');
  const cur = $('tactic').value;
  $('tactic').innerHTML = info.tactics.map(t => `<option>${t}</option>`).join('');
  if (info.tactics.includes(cur)) $('tactic').value = cur;
  $('edFile').innerHTML = opts;
  if (ed) { $('edFile').value = ed.name; if (info.tactics.includes(ed.name)) $('tactic').value = ed.name; }
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
    const note = p.error ? `draft: line ${p.error.line}: ${p.error.msg}` : p.truncated ? `draft ${p.truncated}`
      : `draft: ${p.cmds.filter(c => c.kind !== 'turn').length} moves, ~${p.t.toFixed(1)} s`;
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
  const tx = side === REF_SIDE ? fx : FIELD_X - fx;          // u koordinatama taktike (žuta)
  view.setCursorPoint([fx, fy], `x = ${Math.round(tx)} mm from the left edge · y = ${Math.round(fy)} mm from the bottom`);
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
      if (dr.sha === sha) { text = dr.text; msg(`${name}: restored your unsaved changes`); }
      else { localStorage.removeItem('eurosim.draft.' + name); msg(`${name}: file changed on disk, an old unsaved draft was dropped`, true); }
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
    msg(info.where && info.where.mode !== 'repo' ? `saved ONLY on this computer: ${info.where.tactics}/${ed.name}.py`
      : `saved ESP32/tactics/${ed.name}.py`);
    repoRefresh();
  } catch (e) {
    if (e.status === 409 && !force &&
        confirm(`ESP32/tactics/${ed.name}.py was changed on disk after you opened it.\n\nOverwrite it with your version?`)) {
      ed.sha = e.data.sha;
      return edSave(true);
    }
    msg(e.message, true);
  }
}

const NAME_OK = n => /^[A-Za-z_][A-Za-z0-9_]{0,40}$/.test(n);

function askName(title, def) {
  const name = (prompt(title + '\n(letters, digits and _, not starting with a digit)', def) || '').trim();
  if (!name) return null;
  if (!NAME_OK(name)) { msg('name: letters, digits and _ only, not starting with a digit', true); return null; }
  return name;
}

async function edSaveAs() {
  const name = askName(`Save "${ed.name}" as:`, ed.name + '_2');
  if (!name || name === ed.name) return;
  let sha = null;
  if (info.tactics.includes(name)) {
    if (!confirm(`ESP32/tactics/${name}.py already exists.\n\nOverwrite it with this text?`)) return;
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
  if (!ed.sha) { msg('save the tactic first', true); return; }
  if (ed.editor.text() !== ed.saved) { msg('save your changes before renaming', true); return; }
  const name = askName(`Rename "${ed.name}" to:`, ed.name);
  if (!name || name === ed.name) return;
  try {
    await api('/api/tactic/rename', { name: ed.name, new: name });
    info = await api('/api/info');
    ed.name = name; $('tactic').value = name;
    fillTacticSelects(); edState();
    msg(`renamed to ESP32/tactics/${name}.py`);
  } catch (e) { msg(e.message, true); }
}

async function edDelete() {
  if (!confirm(`Delete ESP32/tactics/${ed.name}.py?\n\nIn the repo you can get it back with git; outside the repo it is gone.`)) return;
  try {
    await api('/api/tactic/delete', { name: ed.name });
    try { localStorage.removeItem('eurosim.draft.' + ed.name); } catch (e) { /* ignore */ }
    info = await api('/api/info');
    msg(`deleted ${ed.name}`);
    await edLoad(info.tactics.includes('primer') ? 'primer' : info.tactics[0]);
  } catch (e) { msg(e.message, true); }
}

function edNew() {
  const name = askName('Name of the new tactic:', 'nova');
  if (!name) return;
  if (info.tactics.includes(name)) { msg(`${name} already exists`, true); return; }
  ed.name = name; ed.sha = null; ed.saved = '';
  ed.editor.setText(ed.api.template);
  fillTacticSelects();
  edChanged(ed.editor.text());
}

// ---- panel Commands: Gambit Micro običnim jezikom (plan S4); opisi iz eurosim/apidoc.py, potpisi iz tac.py ----

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function tableSvg(ex) {                            // mala slika stola sa osama i tačkom iz primera
  const m = /\((\d+),\s*(\d+)/.exec(ex || '');
  const W = 240, H = 160, sx = W / 3000, sy = H / 2000;
  const pt = m ? [+m[1], +m[2]] : null;
  return `<svg class="tbl" viewBox="-52 -8 ${W + 62} ${H + 30}" width="${W + 62}" height="${H + 30}">
    <rect x="0" y="0" width="${W}" height="${H}" fill="#24302b" stroke="#6b7785"/>
    <rect x="0" y="${H - 1250 * sy}" width="${500 * sx}" height="${500 * sy}" fill="#f7b50055"/>
    <rect x="${W - 500 * sx}" y="${H - 1250 * sy}" width="${500 * sx}" height="${500 * sy}" fill="#2f7fc155"/>
    <text x="-4" y="${H + 12}" fill="#c8d0da" font-size="10" text-anchor="end">0,0</text>
    <text x="${W}" y="${H + 12}" fill="#ff9b9b" font-size="10" text-anchor="end">x 3000 →</text>
    <text x="-4" y="6" fill="#9bee9b" font-size="10" text-anchor="end">y 2000</text>
    ${pt ? `<line x1="0" y1="${H - pt[1] * sy}" x2="${pt[0] * sx}" y2="${H - pt[1] * sy}" stroke="#ffd166" stroke-dasharray="3 2"/>
    <line x1="${pt[0] * sx}" y1="${H}" x2="${pt[0] * sx}" y2="${H - pt[1] * sy}" stroke="#ffd166" stroke-dasharray="3 2"/>
    <circle cx="${pt[0] * sx}" cy="${H - pt[1] * sy}" r="4" fill="#ffd166"/>
    <text x="${pt[0] * sx + 6}" y="${H - pt[1] * sy - 5}" fill="#ffd166" font-size="10">x=${pt[0]}, y=${pt[1]}</text>` : ''}
    <text x="${250 * sx}" y="${H - 1000 * sy + 3}" fill="#f7b500" font-size="9" text-anchor="middle">start</text>
  </svg>`;
}

function renderApiHelp() {
  if (!ed) return;
  const f = $('apiFilter').value.toLowerCase().trim();
  const groups = {};
  for (const [name, fn] of Object.entries(ed.api.funcs)) {
    const h = fn.help || { group: 'Other', say: fn.doc, params: [], ret: '', example: '' };
    if (f && !(name + ' ' + h.say + ' ' + fn.doc).toLowerCase().includes(f)) continue;
    (groups[h.group] = groups[h.group] || []).push([name, fn, h]);
  }
  const order = ['Motion', 'Actuators', 'Waiting', 'Match time', 'Where is the robot', 'Other'];
  const parts = [`<p class="coords">${esc(ed.api.coords || '')}</p>`];
  for (const g of order.concat(Object.keys(groups).filter(k => !order.includes(k)))) {
    if (!groups[g]) continue;
    parts.push(`<h4>${esc(g)}</h4>`);
    for (const [name, fn, h] of groups[g]) {
      const params = (h.params || []).map(([p, t]) => {
        const d = (fn.params.find(x => x[0] === p) || [])[1];
        const note = d == null || /default|optional/i.test(t) ? '' : d === 'None' ? ' <span class="dim">(optional)</span>' : ` <span class="dim">(default ${esc(d)})</span>`;
        return `<tr><td><code>${esc(p)}</code>${d == null ? ' <span class="req">required</span>' : ''}</td><td>${esc(t)}${note}</td></tr>`;
      }).join('');
      parts.push(`<details class="cmd"${f ? ' open' : ''}><summary><code>${esc(name)}</code> <span>${esc(h.say)}</span></summary>
        <div class="sig"><code>${esc(fn.sig)}</code></div>
        ${params ? `<table>${params}</table>` : ''}
        ${h.ret ? `<p><b>Gives back:</b> ${esc(h.ret)}</p>` : ''}
        ${h.xy ? tableSvg(h.example) : ''}
        ${h.example ? `<pre>${esc(h.example)}</pre><button class="ins" data-ex="${esc(h.example.split('\n')[0].split('#')[0].trim())}">Insert into code</button>` : ''}
      </details>`);
    }
  }
  parts.push(`<h4>Actuator names</h4><p>${ed.api.actuators.map(a => `<code>${esc(a)}</code>`).join(' ') || '–'} <span class="dim">(ESP32/config.py ACTUATORS)</span></p>`);
  $('apiList').innerHTML = parts.join('');
  for (const b of $('apiList').querySelectorAll('button.ins')) b.onclick = () => { ed.editor.insertLine(b.dataset.ex); };
}

function toggleCommands(show) {
  const d = $('apiDrawer');
  d.hidden = show === undefined ? !d.hidden : !show;
  $('edCmdBtn').classList.toggle('on', !d.hidden);
  if (!d.hidden) { renderApiHelp(); $('apiFilter').focus(); }
}

async function toggleEditor() {
  if (ed) {
    $('editorPane').hidden = true; $('main').classList.remove('editing'); $('edBtn').classList.remove('on');
    view.setPreview(null); view.setCursorPoint(null); clearTimeout(autoSimTimer); toggleCommands(false);
    ed.editor.view.destroy(); ed = null;
    fillTacticSelects();
    return;
  }
  const { TacticEditor } = await import('./editor.js');
  const tapi = await api('/api/tacapi');
  $('editorPane').hidden = false; $('main').classList.add('editing'); $('edBtn').classList.add('on');
  ed = { api: tapi, name: $('tactic').value, sha: null, saved: '' };
  ed.editor = new TacticEditor($('edHost'), { api: tapi, onChange: edChanged, onRun: () => simulate(), onSave: () => edSave(), onSaveAs: () => edSaveAs(),
    onEdit: () => edPreview(), onCursor: line => edCursor(line) });
  renderApiHelp();
  await edLoad(ed.name);
}

// ---------------- live ----------------

function liveSend(c) {
  if (live && live.ws.readyState === 1) live.ws.send(JSON.stringify(c));
}

function setFollow(on) {
  if (!live) return;
  live.follow = on;
  $('followBtn').classList.toggle('on', on);
  $('rFollow').classList.toggle('on', on);
  $('play').textContent = on ? '⏸' : '▶';
}

function liveColumns(frames) {
  const cols = {};
  const keys = new Set();
  for (const f of frames) for (const k in f) keys.add(k);
  for (const k of keys) cols[k] = frames.map(f => f[k] ?? null);
  return cols;
}

function liveRebuild() {
  const L = live;
  if (!L || !L.dirty || !L.raw.frames.length) return;
  L.dirty = false;
  const d = { meta: L.raw.meta || {}, result: {}, events: L.raw.events, cols: liveColumns(L.raw.frames) };
  const first = !run || run.live !== L;
  run = buildRun(d);
  run.live = L;
  view.setRun(run);
  view.setVisibility({ odom: $('showOdom').checked, targets: $('showTargets').checked });
  if (first) charts.setRun(run); else charts.update(run);
  renderSteps(); renderLog(); renderMarks();
  $('slider').max = Math.max(0, run.cols.t.length - 1);
  if (L.follow) play.t = run.duration;
  show();
}

async function startLive() {
  if (live) return;
  setPlaying(false);
  const q = new URLSearchParams({ tactic: $('tactic').value, side: $('side').value, obstacles: JSON.stringify(opponents),
    elements: $('showElements').checked ? '1' : '0' });
  if (ed) {                                     // editor text (saved or not) is the tactic in Live too
    try { q.set('stage', (await api('/api/stage', { name: ed.name, source: ed.editor.text() })).stage); }
    catch (e) { msg(e.message, true); return; }
  }
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/live?${q}`);
  live = { ws, raw: { meta: null, frames: [], events: [] }, follow: true, dirty: false, screen: null };
  $('liveGroup').hidden = false;
  $('liveBtn').classList.add('live-on'); $('liveBtn').textContent = '● LIVE';
  $('run').disabled = true; $('result').style.display = 'none';
  esp.setEnabled(true);
  setFollow(true);
  msg('live: robot is on, ESP connected to STM32 · use the ESP buttons or Arm / Run test');
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.type === 'data') {
      const L = live; if (!L) return;
      if (m.meta) L.raw.meta = m.meta;
      $('bandCord').hidden = m.mec !== 'NAORUZAN';         // naoružan: čeka činč (dugme na timeline-u)
      if (m.frames.length) { L.raw.frames.push(...m.frames); L.dirty = true; }
      if (m.events.length) {
        L.raw.events.push(...m.events); L.dirty = true;
        for (const e of m.events) if (e[1] === 'screen') L.screen = { t: e[0], ...e[2] };
      }
      if (L.follow) {
        if (L.screen) esp.setScreen(L.screen);
        const f = m.frames[m.frames.length - 1];
        if (f) {
          view.setPose(f);
          $('time').textContent = `${secs(f.t)} s · live ×${m.speed}${m.paused ? ' · paused' : ''}`;
        }
      }
      $('pauseBtn').textContent = m.paused ? '▶' : '⏸';
      $('pauseBtn').classList.toggle('on', m.paused);
    } else if (m.type === 'end') {
      stopLiveUi();
      load(m.run, 'live session ended: replay it or save it', 1e12);
    } else if (m.type === 'error') {
      msg('live: ' + m.error.split('\n')[0], true);
      console.error(m.error);
    }
  };
  ws.onclose = () => { if (live) { stopLiveUi(); msg('live connection closed', true); } };
}

function stopLiveUi() {
  if (!live) return;
  try { live.ws.close(); } catch (e) { /* ignore */ }
  live = null;
  $('bandCord').hidden = true;
  $('liveGroup').hidden = true;
  $('robotGroup').hidden = true;
  $('robotBtn').classList.remove('live-on');
  $('liveBtn').disabled = false; $('robotBtn').disabled = false;
  $('liveBtn').classList.remove('live-on'); $('liveBtn').textContent = '● Live';
  $('run').disabled = false;
  esp.setEnabled(false);
}

// ---------------- robot (F5) ----------------

function liveData(m) {                          // shared by Live and Robot: append, follow
  const L = live; if (!L) return null;
  if (m.meta) L.raw.meta = m.meta;
  if (m.frames.length) { L.raw.frames.push(...m.frames); L.dirty = true; }
  if (m.events.length) { L.raw.events.push(...m.events); L.dirty = true; }
  const f = m.frames[m.frames.length - 1];
  if (L.follow && f) view.setPose(f);
  return f;
}

function startRobot(host, password, label) {
  if (live) return;
  setPlaying(false);
  $('robotConnect').hidden = true;
  const q = new URLSearchParams({ host, password });
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/robot?${q}`);
  live = { kind: 'robot', ws, raw: { meta: null, frames: [], events: [] }, follow: true, dirty: false, host };
  $('robotGroup').hidden = false;
  $('robotBtn').classList.add('live-on');
  $('liveBtn').disabled = true; $('robotBtn').disabled = true;
  $('run').disabled = true; $('result').style.display = 'none';
  $('robotStatus').textContent = 'connecting…'; $('robotStatus').className = 'pill';
  esp.setEnabled(false); esp.setScreen(null);
  esp.hint.textContent = 'the robot does not stream its screen';
  setFollow(true);
  msg(`robot ${label || host}: connecting…`);
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.type === 'data') {
      const f = liveData(m);
      const st = $('robotStatus');
      if (m.age == null) { st.textContent = 'no telemetry'; st.className = 'pill bad'; }
      else if (m.age > 1500) { st.textContent = `no data ${secs(m.age)} s`; st.className = 'pill bad'; }
      else { st.textContent = `● ${host}` + (m.mec && m.mec !== 'NEMA' ? ` · ${m.mec}` : '') + (m.running ? ` · ${m.running}` : ''); st.className = 'pill ok'; }
      if (f && live.follow) $('time').textContent = `${secs(f.t)} s · robot`;
    } else if (m.type === 'reply') {
      const text = `${m.cmd}: ${m.ok ? 'OK' : 'ERR'} ${(m.lines || []).slice(-2).join(' · ')}`;
      msg(text, !m.ok);
      if (m.cmd === 'STAT' && m.ok) msg(`robot ${host}: connected · ` + (m.lines || []).slice(0, 3).join(' · '));
    } else if (m.type === 'end') {
      stopLiveUi();
      if (m.run) load(m.run, 'robot session ended: replay it, save it or compare it with a simulation', 1e12);
      else msg('robot disconnected (no telemetry received)');
    } else if (m.type === 'error') {
      msg('robot: ' + m.error.split('\n')[0], true);
    }
  };
  ws.onclose = () => { if (live && live.kind === 'robot') { stopLiveUi(); msg('robot connection closed', true); } };
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

function setRef(r, name) {
  ref = r;
  view.setCompare(r);
  $('cmpName').textContent = r ? `reference: ${name}` : '';
  $('cmpClear').hidden = !r;
  if (run) show();
}

// ---------------- profile (F4) ----------------

async function openProfile(file) {
  const d = file ? await api('/api/profile', { file }) : await api('/api/profile');
  const info2 = file ? await api('/api/profile') : d;
  $('profFile').innerHTML = (info2.files || []).map(f => `<option>${f}</option>`).join('');
  $('profFile').value = d.file.split(/[\\/]/).pop();
  $('profPath').textContent = d.file;
  const body = $('profBody');
  body.innerHTML = '';
  for (const sec of d.sections) {
    const h = document.createElement('h4'); h.textContent = sec.name || 'general'; body.appendChild(h);
    for (const it of sec.items) {
      const row = document.createElement('div'); row.className = 'pr';
      const key = (sec.name ? sec.name + '.' : '') + it.key;
      const isBool = typeof it.value === 'boolean';
      row.innerHTML = `<span>${it.key}</span><input data-key="${key}" ${isBool ? 'type="checkbox"' : ''}>` +
        `<span class="c ${/\(P\)/.test(it.comment) ? 'p' : ''}"></span>`;
      const inp = row.querySelector('input');
      if (isBool) inp.checked = it.value; else inp.value = it.value;
      inp.dataset.orig = isBool ? String(it.value) : String(it.value);
      inp.oninput = inp.onchange = () => inp.classList.toggle('changed', (isBool ? String(inp.checked) : inp.value) !== inp.dataset.orig);
      row.querySelector('.c').textContent = it.comment;
      row.querySelector('.c').title = it.comment;
      body.appendChild(row);
    }
  }
  $('profDialog').hidden = false;
}

async function saveProfile() {
  const changes = {};
  for (const inp of document.querySelectorAll('#profBody input.changed')) {
    changes[inp.dataset.key] = inp.type === 'checkbox' ? inp.checked : (isNaN(+inp.value) ? inp.value : +inp.value);
  }
  try {
    const d = await api('/api/profile', { file: $('profFile').value, changes });
    info = await api('/api/info');
    msg(`profile saved (${Object.keys(changes).length} change(s)): ${d.file} · press Simulate to use it`);
    $('profDialog').hidden = true;
  } catch (e) { msg(e.message, true); }
}

// ---------------- repo kao radni prostor (plan S10) ----------------

function showRepoBanner() {
  const w = info.where || {};
  const b = $('repoBanner');
  if (w.mode === 'repo') { b.hidden = true; document.body.classList.remove('has-banner'); document.title = 'Eurosim'; return; }
  let local = false;
  try { local = sessionStorage.getItem('eurosim.norepo') === '1'; } catch (e) { /* ignore */ }
  b.hidden = false; document.body.classList.add('has-banner');
  b.classList.toggle('local', local);
  $('rbLocal').hidden = local;
  $('repoBannerText').textContent = local
    ? `⚠ No repo: tactics and profiles are saved ONLY on this computer (${w.home}). Nobody else sees them.`
    : '⚠ Eurosim is not in the Robot-2027 repo. Tactics and the robot profile are NOT saved to the team repo and ' +
      'nobody else will see them. Start it from the cloned repo (start.bat / start.sh), or:';
  document.title = 'Eurosim (NO REPO)';
}

async function repoOpen() {
  const def = (info.where.user_home || '') + (info.where.user_home && info.where.user_home.includes('\\') ? '\\' : '/') + 'Robot-2027';
  const path = prompt('Folder of the Robot-2027 repo on this computer (where ESP32 and simulator are):', def);
  if (!path) return;
  try { const d = await api('/api/repo/open', { path }); await repoSwitched(d); } catch (e) { alert(e.message); }
}

async function repoClone() {
  const parent = prompt('Clone the team repo into which folder? (a Robot-2027 folder is made inside it)\n' +
    'Needs Git; GitHub may ask you to sign in.', info.where.user_home || '');
  if (!parent) return;
  msg('cloning Robot-2027 from GitHub… (this can take a minute)');
  try { const d = await api('/api/repo/clone', { parent }); await repoSwitched(d); } catch (e) { msg(e.message, true); alert(e.message); }
}

async function repoSwitched(d) {
  if (d.note) alert(d.note);
  location.reload();                                // sve (taktike, profil, putanje) iz novog repoa
}

async function repoRefresh(fetch = false) {
  if (!info.where || info.where.mode !== 'repo') { $('repoBtn').hidden = true; return null; }
  let st;
  try { st = await api('/api/repo/status' + (fetch ? '?fetch=1' : '')); } catch (e) { st = { error: e.message }; }
  const badge = $('repoBadge');
  const n = (st.changed || []).length, behind = st.behind || 0, prof = (st.profile_changed_upstream || []).length;
  badge.hidden = !(n || behind || prof);
  badge.textContent = [behind ? `↓${behind}` : '', prof ? '! profile' : '', n ? `●${n}` : ''].filter(Boolean).join(' ');
  badge.title = [behind ? `${behind} new commit(s) on GitHub: Pull latest` : '', prof ? 'the robot profile was changed on GitHub' : '',
    n ? `${n} changed file(s) not saved to GitHub` : ''].filter(Boolean).join('\n');
  if (!$('repoDialog').hidden) renderRepo(st);
  return st;
}

function renderRepo(st) {
  $('repoRoot').textContent = st.root || '';
  const b = [];
  if (st.error) b.push(`<p class="err">${esc(st.error)}</p>`);
  if (st.branch) b.push(`<p>branch <b>${esc(st.branch)}</b> · ${esc(st.commit || '')}</p>`);
  if (st.behind != null) b.push(`<p>${st.behind ? `<span class="warn">${st.behind} new on GitHub</span>` : 'up to date with GitHub'}` +
    `${st.ahead ? ` · ${st.ahead} of yours not pushed yet` : ''}</p>`);
  else if (st.branch) b.push('<p class="dim">this branch is not on GitHub yet</p>');
  if ((st.profile_changed_upstream || []).length) b.push(`<p class="warn">The robot profile was changed on GitHub (${st.profile_changed_upstream.map(esc).join(', ')}): Pull latest.</p>`);
  const ch = st.changed || [];
  b.push(ch.length ? `<p>Changed here, not on GitHub yet:</p><ul>${ch.map(c => `<li><code>${esc(c.state)}</code> ${esc(c.file)}</li>`).join('')}</ul>`
    : '<p class="dim">No changed tactics or profiles.</p>');
  $('repoBody').innerHTML = b.join('');
}

// ---------------- start ----------------

async function main() {
  info = await api('/api/info');
  REF_SIDE = info.ref_side || REF_SIDE;
  $('tactic').innerHTML = info.tactics.map(t => `<option>${t}</option>`).join('');
  try {
    const sel = JSON.parse(localStorage.getItem('eurosim.sel') || '{}');
    for (const k of ['tactic', 'side', 'mode']) if (sel[k]) $(k).value = sel[k];
  } catch (e) { /* ignore */ }
  fillRuns(info.runs);
  showRepoBanner();
  $('rbOpen').onclick = repoOpen;
  $('rbClone').onclick = repoClone;
  $('rbLocal').onclick = () => { try { sessionStorage.setItem('eurosim.norepo', '1'); } catch (e) { /* ignore */ } showRepoBanner(); };
  $('repoBtn').onclick = async () => {
    const d = $('repoDialog'); d.hidden = !d.hidden;
    if (!d.hidden) { $('repoBody').textContent = 'checking GitHub…'; renderRepo(await repoRefresh(true) || {}); }
  };
  $('repoClose').onclick = () => { $('repoDialog').hidden = true; };
  $('repoFetch').onclick = async () => { $('repoBody').textContent = 'checking GitHub…'; renderRepo(await repoRefresh(true) || {}); };
  $('repoPull').onclick = async () => {
    try { renderRepo(await api('/api/repo/pull', {})); info = await api('/api/info'); fillTacticSelects(); msg('pulled the latest from GitHub'); repoRefresh(); }
    catch (e) { alert(e.message); }
  };
  $('repoSave').onclick = async () => {
    try { renderRepo(await api('/api/repo/save', { message: $('repoMsg').value })); $('repoMsg').value = ''; msg('saved to GitHub'); repoRefresh(); }
    catch (e) { alert(e.message); }
  };
  repoRefresh();
  view = new FieldView($('view'), info);
  charts = new Charts($('charts'), t => seek(t));
  view.onHover = p => {
    if (!p) { $('cursor').textContent = ''; return; }
    const side = run ? run.meta.side : $('side').value;
    const tx = side === REF_SIDE ? p[0] : FIELD_X - p[0];
    $('cursor').textContent = `field ${Math.round(p[0])}, ${Math.round(p[1])}` +
      (side !== REF_SIDE ? `   ·   in tactic (${SIDE_NAME[REF_SIDE]}) ${Math.round(tx)}, ${Math.round(p[1])}` : '') +
      '   (double-click: copy)';
  };
  view.onPreviewClick = line => { if (ed) ed.editor.reveal(line); };
  view.onAltPick = p => {                                   // Alt+klik: tačka sa mape u editor (koordinate taktike)
    if (!ed) { msg('open the editor to put a point into a tactic (Alt+click)'); return; }
    const side = $('side').value;
    const x = Math.round((side === REF_SIDE ? p[0] : FIELD_X - p[0]) / 10) * 10, y = Math.round(p[1] / 10) * 10;
    ed.editor.putPoint(x, y);
    msg(`goto ${x}, ${y} (tactic coordinates, ${SIDE_NAME[REF_SIDE]} side)`);
  };
  view.onPick = p => {
    const side = run ? run.meta.side : $('side').value;
    const x = side === REF_SIDE ? p[0] : FIELD_X - p[0];
    const s = `${Math.round(x)}, ${Math.round(p[1])}`;
    navigator.clipboard?.writeText(s);
    msg(`copied ${s} (tactic coordinates)`);
  };

  $('run').onclick = () => simulate();
  esp = new EspPanel($('espPanel'), c => liveSend(c));
  esp.setEnabled(false);
  try { opponents = JSON.parse(localStorage.getItem('eurosim.opp') || '[]'); } catch (e) { opponents = []; }
  view.onOppSelect = i => { oppSel = i; refreshOpponents(); };
  view.onOppMove = (i, final) => {
    if (i === oppSel) { $('oppX').value = opponents[i].x; $('oppY').value = opponents[i].y; }
    opponentsChanged(final);
  };
  refreshOpponents();
  $('addOpp').onclick = () => {
    opponents.push({ name: 'opponent ' + (opponents.length + 1), x: 1500, y: 1000, w: 300, h: 300, th: 0, z: 350, r: 0 });
    oppSel = opponents.length - 1;
    refreshOpponents();
    opponentsChanged(true);
  };
  $('oppDel').onclick = () => { opponents.splice(oppSel, 1); oppSel = -1; refreshOpponents(); opponentsChanged(true); };
  for (const id of ['oppX', 'oppY', 'oppW', 'oppH', 'oppTh', 'oppZ', 'oppRound']) $(id).onchange = editOpponent;
  $('liveBtn').onclick = () => (live ? liveSend(['quit']) : startLive());
  $('robotBtn').onclick = () => { $('robotConnect').hidden = !$('robotConnect').hidden; };
  $('rCancel').onclick = () => { $('robotConnect').hidden = true; };
  $('rConnect').onclick = () => {
    localStorage.setItem('eurosim.host', $('rHost').value);
    startRobot($('rHost').value.trim(), $('rPass').value);
  };
  $('rHost').value = localStorage.getItem('eurosim.host') || 'eurokik.local';
  $('rVirtual').onclick = async () => {
    msg('starting a virtual robot (real ESP code, simulated STM32) on 127.0.0.1…');
    try {
      const d = await api('/api/vrobot', { action: 'start', tactic: curTactic(), side: $('side').value, obstacles: opponents });
      startRobot(d.host, d.password, 'virtual (127.0.0.1)');
    } catch (e) { msg(e.message, true); }
  };
  $('rPush').onclick = () => { const [n, src] = robotTactic(); liveSend(['push', n, src]); msg(`sending ${n}…`); };
  $('rRun').onclick = () => {
    const [n, src] = robotTactic();
    if (live && live.host !== '127.0.0.1' &&
        !confirm(`Run "${n}" on ${live.host} now (${SIDE_NAME[$('side').value]})?\n\nTHE ROBOT WILL MOVE. Free space, hand on the motor switch.`)) return;
    liveSend(['push', n, src]); liveSend(['run', n, $('side').value]); msg(`running ${n} on the robot…`);
  };
  $('rStop').onclick = () => liveSend(['stop']);
  $('rFollow').onclick = () => setFollow(!live.follow);
  $('rEnd').onclick = () => liveSend(['quit']);
  $('profBtn').onclick = () => ($('profDialog').hidden ? openProfile().catch(e => msg(e.message, true)) : ($('profDialog').hidden = true));
  $('profClose').onclick = () => { $('profDialog').hidden = true; };
  $('profSave').onclick = saveProfile;
  $('profFile').onchange = e => openProfile(e.target.value).catch(er => msg(er.message, true));
  $('cmpPin').onclick = () => { if (run) setRef(run, `${run.meta.tactic || '?'} (${run.meta.mode})`); };
  $('cmpClear').onclick = () => setRef(null);
  $('cmpRun').onchange = async e => {
    const n = e.target.value; e.target.value = '';
    if (!n) return;
    try { setRef(buildRun(await api('/api/runs/' + encodeURIComponent(n))), n); } catch (er) { msg(er.message, true); }
  };
  $('endBtn').onclick = () => liveSend(['quit']);
  $('armBtn').onclick = () => liveSend(['arm', curTactic(), $('side').value]);
  $('testBtn').onclick = () => liveSend(['test', curTactic(), $('side').value]);
  document.querySelector('#espPanel .ov-title').onclick = () => $('espPanel').classList.toggle('collapsed');
  $('result').onclick = () => $('result').classList.toggle('mini');
  view.setElements($('showElements').checked ? info.field.elements : []);
  $('showElements').onchange = e => {
    view.setElements(e.target.checked ? info.field.elements : []);
    if (run && !live) simulate(play.t);
  };
  $('rulesLook').onchange = e => view.setTableLook(e.target.checked ? 'rules' : 'grid');
  $('edBtn').onclick = () => toggleEditor().catch(e => msg('editor: ' + e.message, true));
  $('edFile').onchange = e => edLoad(e.target.value);
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
  $('edRun').onclick = () => simulate();
  $('apiFilter').oninput = renderApiHelp;
  $('edCmdBtn').onclick = () => toggleCommands();
  $('apiClose').onclick = () => toggleCommands(false);
  for (const b of document.querySelectorAll('.ed-tabs button')) {
    b.onclick = () => {
      for (const o of document.querySelectorAll('.ed-tabs button')) { o.classList.toggle('on', o === b); $(o.dataset.tab).hidden = o !== b; }
    };
  }
  window.addEventListener('beforeunload', e => { if (ed && ed.editor.text() !== ed.saved) e.preventDefault(); });
  $('cordBtn').onclick = () => liveSend(['cord']);
  $('bandCord').onclick = () => liveSend(['cord']);
  $('stopBtn').onclick = () => liveSend(['stop']);
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
  const vis = () => view.setVisibility({ odom: $('showOdom').checked, targets: $('showTargets').checked });
  $('showOdom').onchange = () => { vis(); if (run) show(); };
  $('showTargets').onchange = vis;
  $('showIr').onchange = e => view.setShowIr(e.target.checked);
  const pref = (k, el, apply) => {                 // izbor u Show ▾ se pamti (localStorage)
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
    const name = prompt('Name for this run (saved in simulator/runs/):', '');
    if (name === null) return;
    try { const d = await api('/api/runs/save', { name }); fillRuns(d.runs); msg(`saved ${d.saved}`); }
    catch (e) { msg(e.message, true); }
  };
  $('runs').onchange = async e => {
    const n = e.target.value; if (!n) return;
    try { load(await api('/api/runs/' + encodeURIComponent(n)), `loaded ${n}`); } catch (er) { msg(er.message, true); }
    e.target.value = '';
  };
  document.addEventListener('keydown', e => {
    const tg = e.target;
    if (tg.isContentEditable || (tg.closest && tg.closest('.cm-editor'))) return;
    if (tg.tagName === 'TEXTAREA' || tg.tagName === 'SELECT' ||
        (tg.tagName === 'INPUT' && !['range', 'checkbox', 'button'].includes(tg.type))) return;
    if (e.key === ' ') { e.preventDefault(); setPlaying(!play.playing); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); e.shiftKey ? stepJump(-1) : frameJump(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); e.shiftKey ? stepJump(1) : frameJump(1); }
    else if (e.key === 'Home') seek(0);
    else if (e.key === 'End') run && seek(run.duration);
    else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) simulate();
    else if (e.key === 'Escape' && live && live.kind === 'robot') liveSend(['stop']);
  });
  requestAnimationFrame(tick);
  const w = info.where || {};
  msg(w.mode === 'standalone' ? `standalone: tactics, profiles and runs in ${w.home}` : `repo ${w.root}: tactics in ESP32/tactics`);
  document.querySelector('.brand').title = JSON.stringify(w, null, 1);
}

window.eurosim = { get ed() { return ed; }, get run() { return run; }, get view() { return view; }, play, edMarks };   // za testove i konzolu
main().catch(e => msg('cannot start: ' + e.message, true));
