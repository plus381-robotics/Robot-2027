// Eurosim UI: run a tactic in the simulator, then play back the recording (speed, pause,
// frame / step stepping, scrubbing). All data comes from one recording (server: /api/run).
import { FieldView } from './view3d.js';
import { Charts } from './charts.js';
import { EspPanel } from './esp.js';

const $ = id => document.getElementById(id);
const SIDE_NAME = { plava: 'Blue', zuta: 'Yellow' };
const REASON = { BLOCKED: 'blocked', TIMEOUT: 'timeout', PREEMPTED: 'preempted', MATCH_OVER: 'match over',
  STOPPED: 'stopped', INVALID: 'rejected', NOREPLY: 'no reply', SUPERSEDED: 'superseded', STOP: 'STOP' };
const FIELD_X = 3000, REF_SIDE = 'plava';

let info, view, charts, esp, run = null;
let opponents = [], oppSel = -1;
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
  const steps = [], byIdx = {}, tactics = [];
  for (const [t, kind, x] of d.events) {
    if (kind === 'tactic') {
      tactics.push({ t, name: x[0], side: x[1] });
      for (const k in byIdx) delete byIdx[k];
    } else if (kind === 'step') {
      const s = { idx: x[0], name: x[1], timeout: x[2], next: x[3], t, end: null, ok: null, reason: null, dur: null, target: null };
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
    if (s && !s.target) s.target = [x.f.x, x.f.y];
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
  return { ...d, frameAt, steps, tactics, log, screens, screenAt, duration: ts.length ? ts[ts.length - 1] : 0 };
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
    ['odom err', f1(dx) + ' mm', dx > 10 ? 'warn' : ''], ['STM phase', `${c.phase[i]} ${c.reg[i]}/${c.ms[i]}`],
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
    tr.innerHTML = `<td>${s.idx}</td><td title="${s.name}">${s.name}</td><td>${res}</td><td>${s.dur == null ? '' : secs(s.dur)}</td>`;
    tr.onclick = () => seek(s.t);
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

function renderMarks() {
  const el = $('marks'); el.innerHTML = '';
  const D = run.duration || 1;
  for (const s of run.steps) {
    const i = document.createElement('i');
    i.style.left = (s.t / D * 100) + '%';
    if (s.ok === false) i.className = 'fail';
    i.title = `${s.idx}. ${s.name}`;
    el.appendChild(i);
  }
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
  view.setFrame(i);
  renderState(i);
  updateSteps(play.t);
  updateLog(play.t);
  charts.setTime(play.t);
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
  if (!r.ok || d.error) throw new Error(d.error || r.statusText);
  return d;
}

function load(d, label, keepTime = null) {
  run = buildRun(d);
  view.setRun(run);
  view.setVisibility({ odom: $('showOdom').checked, targets: $('showTargets').checked });
  charts.setRun(run);
  renderSteps(); renderLog(); renderResult(); renderMarks();
  $('slider').max = Math.max(0, run.cols.t.length - 1);
  $('save').disabled = false;
  if (label) msg(label);
  if (d.meta && d.meta.obstacles) { opponents = d.meta.obstacles.map(o => ({ ...o })); oppSel = -1; refreshOpponents(); }
  if (keepTime != null) { seek(keepTime); return; }
  seek(0);
  setPlaying(true);
}

async function simulate(keepTime = null) {
  if (live) return;
  const body = { tactic: $('tactic').value, side: $('side').value, mode: $('mode').value, obstacles: opponents };
  localStorage.setItem('eurosim.sel', JSON.stringify(body));
  $('run').disabled = true;
  msg(`simulating ${body.tactic}…`);
  try {
    const d = await api('/api/run', body);
    load(d, `${body.tactic}: simulated ${secs(d.result.sim_ms)} s in ${d.wall_s} s`, keepTime);
  } catch (e) {
    msg(e.message.split('\n')[0], true);
    console.error(e);
  } finally {
    $('run').disabled = false;
  }
}

function fillRuns(list) {
  const s = $('runs');
  s.innerHTML = '<option value="">Saved runs…</option>' + list.map(n => `<option>${n}</option>`).join('');
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

// ---------------- live ----------------

function liveSend(c) {
  if (live && live.ws.readyState === 1) live.ws.send(JSON.stringify(c));
}

function setFollow(on) {
  if (!live) return;
  live.follow = on;
  $('followBtn').classList.toggle('on', on);
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

function startLive() {
  if (live) return;
  setPlaying(false);
  const q = new URLSearchParams({ tactic: $('tactic').value, side: $('side').value, obstacles: JSON.stringify(opponents) });
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
  $('liveGroup').hidden = true;
  $('liveBtn').classList.remove('live-on'); $('liveBtn').textContent = '● Live';
  $('run').disabled = false;
  esp.setEnabled(false);
}

// ---------------- start ----------------

async function main() {
  info = await api('/api/info');
  $('tactic').innerHTML = info.tactics.map(t => `<option>${t}</option>`).join('');
  try {
    const sel = JSON.parse(localStorage.getItem('eurosim.sel') || '{}');
    for (const k of ['tactic', 'side', 'mode']) if (sel[k]) $(k).value = sel[k];
  } catch (e) { /* ignore */ }
  fillRuns(info.runs);
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
  $('endBtn').onclick = () => liveSend(['quit']);
  $('armBtn').onclick = () => liveSend(['arm', $('tactic').value, $('side').value]);
  $('testBtn').onclick = () => liveSend(['test', $('tactic').value, $('side').value]);
  $('cordBtn').onclick = () => liveSend(['cord']);
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
    if (tg.tagName === 'TEXTAREA' || tg.tagName === 'SELECT' ||
        (tg.tagName === 'INPUT' && !['range', 'checkbox', 'button'].includes(tg.type))) return;
    if (e.key === ' ') { e.preventDefault(); setPlaying(!play.playing); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); e.shiftKey ? stepJump(-1) : frameJump(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); e.shiftKey ? stepJump(1) : frameJump(1); }
    else if (e.key === 'Home') seek(0);
    else if (e.key === 'End') run && seek(run.duration);
    else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) simulate();
  });
  requestAnimationFrame(tick);
  msg('choose a tactic and press Simulate');
}

main().catch(e => msg('cannot start: ' + e.message, true));
