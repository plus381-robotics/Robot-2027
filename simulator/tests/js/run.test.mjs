// Testovi za web/core/run.js: buildRun, appendRun (inkrementalni snimak), hasData.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildRun, appendRun, hasData } from '../../web/core/run.js';

const fixture = () => JSON.parse(readFileSync(new URL('./fixtures/run_sve_komande.json', import.meta.url), 'utf8'));

// Realan snimak (sve_komande, 400 frame-ova) + događaji koje taj snimak nema (lidar, kamenolomi, izuzetak, druga taktika,
// GOTO tik uz početak koraka), sve poređano po vremenu.
function recording() {
  const d = fixture();
  const ev = d.events.slice();
  const t = d.cols.t;
  const at = k => t[Math.floor(t.length * k)];
  ev.push([at(0.2), 'lidar', { pts: [[1, 2]], n: 1 }], [at(0.5), 'lidar', { pts: [[3, 4]], n: 1 }],
    [at(0.3), 'elements', [[1, 2]]], [at(0.4), 'exception', { line: 12, msg: 'x' }],
    [at(0.6), 'tactic', ['druga', 'plava']], [at(0.6), 'line', [1, 'druga linija']],
    [at(0.6), 'step', [1, 'GOTO 1,2', 1000, null]], [at(0.6) + 1, 'rx', { name: 'GOTO', seq: 9, f: { x: 5, y: 6, theta: 900, flags: 0 } }],
    [at(0.7), 'step_end', [1, 'GOTO 1,2', true, null, 5]]);
  ev.sort((a, b) => a[0] - b[0]);                       // stabilan: redosled istog t ostaje
  const frames = t.map((_, i) => Object.fromEntries(Object.keys(d.cols).map(k => [k, d.cols[k][i]])));
  return { d, events: ev, frames };
}

const FIELDS = ['meta', 'result', 'events', 'cols', 'steps', 'tactics', 'excLines', 'log', 'screens', 'lidars', 'elEvents', 'duration'];
const plain = x => JSON.parse(JSON.stringify(x));

function assertSame(a, b) {
  for (const k of FIELDS) assert.deepEqual(plain(a[k]), plain(b[k]), k);
  const last = a.duration;
  for (const t of [0, 1, last * 0.1, last * 0.37, last * 0.5, last * 0.8, last, last + 5000]) {
    assert.equal(a.frameAt(t), b.frameAt(t), 'frameAt ' + t);
    assert.deepEqual(plain(a.screenAt(t)), plain(b.screenAt(t)), 'screenAt ' + t);
    assert.deepEqual(plain(a.lidarAt(t)), plain(b.lidarAt(t)), 'lidarAt ' + t);
  }
}

function incremental(rec, fcuts, ecuts) {
  let run = buildRun({ meta: rec.d.meta, result: rec.d.result, events: [], cols: {} });
  const fb = [0, ...fcuts, rec.frames.length], eb = [0, ...ecuts, rec.events.length];
  for (let i = 0; i < fb.length - 1; i++) run = appendRun(run, rec.frames.slice(fb[i], fb[i + 1]), rec.events.slice(eb[i], eb[i + 1]));
  return run;
}

test('appendRun daje isto što i buildRun nad svim podacima', () => {
  const rec = recording();
  const full = buildRun({ ...rec.d, events: rec.events.slice(), cols: plain(rec.d.cols) });
  assert.ok(full.steps.length >= 5 && full.lidars.length === 2 && full.excLines.length === 1);
  assert.ok(full.steps.some(s => s.target), 'GOTO cilj');
  const n = rec.frames.length, m = rec.events.length;
  assertSame(incremental(rec, [Math.floor(n / 3), Math.floor(2 * n / 3)], [Math.floor(m / 3), Math.floor(2 * m / 3)]), full);
  assertSame(incremental(rec, [100, 250], [0, m]), full);                 // događaji tek u poslednjem delu
  assertSame(incremental(rec, [n - 1, n - 1], [5, 6]), full);
  const per = rec.events.map((_, i) => i + 1).slice(0, -1);               // svaki događaj za sebe
  assertSame(incremental(rec, per.map(i => Math.floor(i * n / m)), per), full);
});

test('appendRun ne prolazi ponovo stare događaje', () => {
  const rec = recording();
  let run = buildRun({ meta: {}, result: {}, events: [], cols: {} });
  run = appendRun(run, rec.frames.slice(0, 50), rec.events.slice(0, 20));
  const before = run.steps.map(s => s);
  run = appendRun(run, rec.frames.slice(50, 60), []);
  assert.equal(run.steps.length, before.length);
  run.steps.forEach((s, i) => assert.equal(s, before[i]));               // isti objekti, bez ponovnog pravljenja
  assert.equal(run.cols.t.length, 60);
});

test('kolona koja se pojavi tek kasnije dobija null za ranije frame-ove', () => {
  let run = buildRun({ meta: {}, result: {}, events: [], cols: {} });
  run = appendRun(run, [{ t: 0, x: 1 }, { t: 10, x: 2 }], []);
  run = appendRun(run, [{ t: 20, x: 3, ox: 7 }], []);
  assert.deepEqual(run.cols.ox, [null, null, 7]);
  assert.deepEqual(run.cols.x, [1, 2, 3]);
  assert.deepEqual(run.cols.ir, [null, null, null]);
});

test('buildRun puni nedostajuće opcione kolone nulama (snimak v2)', () => {
  const run = buildRun({ meta: {}, result: {}, events: [], cols: { t: [0, 10], x: [1, 2] } });
  assert.deepEqual(run.cols.vl, [null, null]);
  assert.equal(run.duration, 10);
});

test('hasData je false za kolonu koje nema i za sve-null kolonu', () => {
  const run = buildRun({ meta: {}, result: {}, events: [], cols: { t: [0, 10, 20], x: [1, 2, 3], ir: [null, null, null] } });
  assert.equal(hasData(run, 'x'), true);
  assert.equal(hasData(run, 'ir'), false);
  assert.equal(hasData(run, 'nema_je'), false);
  assert.equal(hasData(run, 'ox'), false);                                // opciona, popunjena nulama
  const r2 = appendRun(run, [{ t: 30, x: 4, ir: 5 }], []);
  assert.equal(hasData(r2, 'ir'), true);                                  // keš se osvežava kad stignu podaci
});
