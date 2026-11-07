// Eurosim UI: run a tactic in the simulator, then play back the recording (speed, pause,
// frame / step stepping, scrubbing). All data comes from one recording (server: /api/run).
import { FieldView } from './view3d.js';
import { Charts } from './charts.js';

const $ = id => document.getElementById(id);
const SIDE_NAME = { plava: 'Blue', zuta: 'Yellow' };
const REASON = { BLOCKED: 'blocked', TIMEOUT: 'timeout', PREEMPTED: 'preempted', MATCH_OVER: 'match over',
  STOPPED: 'stopped', INVALID: 'rejected', NOREPLY: 'no reply', SUPERSEDED: 'superseded', STOP: 'STOP' };
const FIELD_X = 3000, REF_SIDE = 'plava';

let info, view, charts, run = null;
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
  const steps = [], byIdx = {};
  for (const [t, kind, x] of d.events) {
    if (kind === 'step') {
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
  return { ...d, frameAt, steps, log, duration: ts.length ? ts[ts.length - 1] : 0 };
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
  for (const s of run.steps) {
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
  play.t = Math.max(0, Math.min(run.duration, t));
  if (!keepPlaying) setPlaying(false);
  show();
}

function show() {
  const i = run.frameAt(play.t);
  view.setFrame(i);
  renderState(i);
  updateSteps(play.t);
  updateLog(play.t);
  charts.setTime(play.t);
  $('slider').value = i;
  $('time').textContent = `${secs(play.t)} / ${secs(run.duration)} s`;
}

function setPlaying(p) {
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

function load(d, label) {
  run = buildRun(d);
  view.setRun(run);
  view.setVisibility({ odom: $('showOdom').checked, targets: $('showTargets').checked });
  charts.setRun(run);
  renderSteps(); renderLog(); renderResult(); renderMarks();
  $('slider').max = Math.max(0, run.cols.t.length - 1);
  $('save').disabled = false;
  msg(label);
  seek(0);
  setPlaying(true);
}

async function simulate() {
  const body = { tactic: $('tactic').value, side: $('side').value, mode: $('mode').value };
  localStorage.setItem('eurosim.sel', JSON.stringify(body));
  $('run').disabled = true;
  msg(`simulating ${body.tactic}…`);
  try {
    const d = await api('/api/run', body);
    load(d, `${body.tactic}: simulated ${secs(d.result.sim_ms)} s in ${d.wall_s} s`);
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

  $('run').onclick = simulate;
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
