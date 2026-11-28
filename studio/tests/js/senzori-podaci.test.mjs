// Testovi za web/senzori/podaci.js: vrednosti iz snimka (lastAt, history) i enkoderi iz odometrije (odoWheels).
// Kolona t je u milisekundama (kao u run.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRun } from '../../web/core/run.js';
import { lastAt, history, odoWheels } from '../../web/senzori/podaci.js';

const runOf = rows => buildRun({ meta: {}, result: {}, events: [], cols: {
  t: rows.map(r => r[0]), ox: rows.map(r => r[1]), oy: rows.map(r => r[2]), oth: rows.map(r => r[3]) } });
const vRun = (ts, vs) => buildRun({ meta: {}, result: {}, events: [], cols: { t: ts, v: vs } });

test('odoWheels: pravo 500 mm', () => {
  const r = odoWheels(runOf([[0, 0, 0, 0], [1, 500, 0, 0]]), 0, 1, 286);
  assert.ok(Math.abs(r.L - 500) < 1e-6 && Math.abs(r.R - 500) < 1e-6 && Math.abs(r.diff) < 1e-6);
});
test('odoWheels: okret u mestu +90°', () => {
  const r = odoWheels(runOf([[0, 0, 0, 0], [1, 0, 0, 90]]), 0, 1, 286);
  assert.ok(Math.abs(r.L + 224.62) < 0.05 && Math.abs(r.R - 224.62) < 0.05);
});
test('odoWheels: okret preko ±180° ide kraćim putem', () => {
  const r = odoWheels(runOf([[0, 0, 0, 170], [1, 0, 0, -170]]), 0, 1, 286);
  assert.ok(r.R > 0 && r.R < 60);
});
test('odoWheels: prozor (t0, t1] i bez podataka', () => {
  const run = runOf([[0, 0, 0, 0], [1, 100, 0, 0], [2, 300, 0, 0]]);
  assert.ok(Math.abs(odoWheels(run, 1, 2, 286).L - 200) < 1e-6);
  const nul = buildRun({ meta: {}, result: {}, events: [], cols: { t: [0, 1] } });
  assert.equal(odoWheels(nul, 0, 1, 286), null);
});

test('lastAt: vrednost u poslednjem frame-u do t, ili null', () => {
  const run = vRun([0, 20, 40], [1, null, 3]);
  assert.equal(lastAt(run, 'v', 25), null);
  assert.equal(lastAt(run, 'v', 45), 3);
  assert.equal(lastAt(run, 'v', 0), 1);
  assert.equal(lastAt(run, 'nema', 0), null);
});
test('history: poslednjih sec sekundi, null izostavljen', () => {
  const run = vRun([0, 1000, 2000, 3000], [1, null, 3, 4]);
  assert.deepEqual(history(run, 'v', 3000, 2), [3, 4]);          // 1000 < t <= 3000, 1000 je null
  assert.deepEqual(history(run, 'v', 3000), [1, 3, 4]);
  assert.deepEqual(history(run, 'v', 1500, 1), []);
  assert.deepEqual(history(run, 'nema', 3000), []);
});
