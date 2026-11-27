// Testovi za web/charts.js (bez DOM-a): koji grafici se crtaju za date kolone.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFS, chartDefs } from '../../web/charts.js';

test('DEFS: grafik ugla „Ugao θ [°]“ iz kolone th; naslovi na srpskom', () => {
  const ugao = DEFS.find(d => d.title === 'Ugao θ [°]');
  assert.ok(ugao);
  assert.deepEqual(ugao.series.map(s => s[0]), ['th']);
  assert.deepEqual(DEFS.map(d => d.title), ['Brzina [m/s]', 'Ugaona brzina [rad/s]', 'Točkovi [m/s]', 'Ugao θ [°]']);
});

test('chartDefs: grafik bez podataka se ne crta (kolona fali ili je sva null)', () => {
  const sim = { t: [0, 10], v: [0, 0.1], v_ref: [0, 0.2], w: [0, 0], w_ref: [0, 0], vl: [0, 1], vr: [0, 1], th: [0, 90] };
  assert.equal(chartDefs(sim).length, 4);
  const robot = { t: [0, 10], v: [0, 0.1], w: [null, null], vl: [null, null], th: [12.5, 13] };   // robot: bez w/točkova
  assert.deepEqual(chartDefs(robot).map(d => d.title), ['Brzina [m/s]', 'Ugao θ [°]']);
  assert.deepEqual(chartDefs({ t: [] }), []);
});
