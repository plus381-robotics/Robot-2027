// Testovi za web/core/snimci.js: izvor S / R / H, ishod, datum, filter liste u prostoru Snimci.
import test from 'node:test';
import assert from 'node:assert/strict';
import { izvorOf, ishodOf, fmtDate, fmtDuration, fold, filterRuns, countByIzvor, sideName } from '../../web/core/snimci.js';

// Redovi kao iz GET /api/runs?detail=1 (najnoviji prvi).
const RUNS = [
  { name: 'pre_PID_fixa', date: '2026-11-27T14:05:09+01:00', engine: 'robot', lidar: 'pravi', tactic: 'kamenolomi',
    side: 'plava', mode: 'test', ok: null, duration_ms: 31200 },
  { name: '20261126-101500_primer_zuta', date: '2026-11-26T10:15:00+01:00', engine: 'sim', lidar: 'sim', tactic: 'primer',
    side: 'zuta', mode: 'mec', ok: true, duration_ms: 98000 },
  { name: 'hibrid_lidar', date: '2026-11-25T09:00:00+01:00', engine: 'sim', lidar: 'pravi', tactic: 'čučanj',
    side: 'zuta', mode: 'test', ok: false, duration_ms: 1500 },
  { name: 'stari_v1', date: '2025-01-02T03:04:05+01:00', engine: 'sim', lidar: null, tactic: 'primer', side: 'plava',
    mode: 'mec', ok: true, duration_ms: null },
  { name: 'polomljen', date: '2026-11-20T08:00:00+01:00', engine: null, lidar: null, tactic: null, side: null, mode: null,
    ok: null, duration_ms: null, error: 'Not a gzipped file' },
];

test('izvorOf: robot = R, simulacija sa pravim ili snimljenim lidarom = H, inače S; nečitljiv fajl = ?', () => {
  assert.deepEqual(RUNS.map(izvorOf), ['R', 'S', 'H', 'S', '?']);
  assert.equal(izvorOf({ engine: 'sim', lidar: 'snimak' }), 'H');
  assert.equal(izvorOf({ engine: 'robot', lidar: 'pravi' }), 'R');            // robot ostaje R
  assert.equal(izvorOf(null), 'S');
});

test('ishodOf: OK / greška / nepoznato (robot) / nečitljiv fajl', () => {
  assert.deepEqual(RUNS.map(r => ishodOf(r).text), ['–', 'OK', 'greška', 'OK', 'nečitljiv']);
  assert.equal(ishodOf(RUNS[1]).cls, 'ok');
  assert.equal(ishodOf(RUNS[2]).cls, 'err');
  assert.equal(ishodOf(RUNS[4]).title, 'Not a gzipped file');
});

test('fmtDate i fmtDuration: vreme kako ga je zapisao server, bez zone', () => {
  assert.equal(fmtDate('2026-11-27T14:05:09+01:00'), '27.11. 14:05');
  assert.equal(fmtDate('2026-03-01T00:30:00-05:00'), '01.03. 00:30');
  assert.equal(fmtDate(''), '');
  assert.equal(fmtDate(undefined), '');
  assert.equal(fmtDuration(98000), '98.0 s');
  assert.equal(fmtDuration(null), '');
  assert.equal(sideName('zuta'), 'Žuta');
  assert.equal(sideName(null), '');
});

test('fold: mala slova bez kvačica', () => {
  assert.equal(fold('Čučanj ŽUTA Đak'), 'cucanj zuta dak');
  assert.equal(fold(null), '');
});

test('filterRuns: po izvoru, po tekstu (sve reči, bez kvačica), oba zajedno', () => {
  const names = l => l.map(r => r.name);
  assert.deepEqual(names(filterRuns(RUNS)), names(RUNS));                      // bez filtera: sve, isti red
  assert.deepEqual(names(filterRuns(RUNS, { izvor: 'R' })), ['pre_PID_fixa']);
  assert.deepEqual(names(filterRuns(RUNS, { izvor: 'H' })), ['hibrid_lidar']);
  assert.deepEqual(names(filterRuns(RUNS, { izvor: 'S' })), ['20261126-101500_primer_zuta', 'stari_v1']);
  assert.deepEqual(names(filterRuns(RUNS, { text: 'primer' })), ['20261126-101500_primer_zuta', 'stari_v1']);
  assert.deepEqual(names(filterRuns(RUNS, { text: 'PRIMER  plava' })), ['stari_v1']);    // sve reči; „plava“ = strana
  assert.deepEqual(names(filterRuns(RUNS, { text: 'zuta' })), ['20261126-101500_primer_zuta', 'hibrid_lidar']);
  assert.deepEqual(names(filterRuns(RUNS, { text: 'žuta' })), names(filterRuns(RUNS, { text: 'zuta' })));
  assert.deepEqual(names(filterRuns(RUNS, { text: 'cucanj' })), ['hibrid_lidar']);       // taktika „čučanj“
  assert.deepEqual(names(filterRuns(RUNS, { text: 'pid' })), ['pre_PID_fixa']);         // ime fajla
  assert.deepEqual(names(filterRuns(RUNS, { text: 'greška' })), ['hibrid_lidar']);      // ishod
  assert.deepEqual(names(filterRuns(RUNS, { text: '27.11.' })), ['pre_PID_fixa']);      // datum kako se prikazuje
  assert.deepEqual(names(filterRuns(RUNS, { izvor: 'S', text: 'mec' })), ['20261126-101500_primer_zuta', 'stari_v1']);
  assert.deepEqual(filterRuns(RUNS, { izvor: 'R', text: 'primer' }), []);
  assert.deepEqual(filterRuns(null, { text: 'x' }), []);
});

test('countByIzvor', () => {
  assert.deepEqual(countByIzvor(RUNS), { S: 2, R: 1, H: 1 });               // nečitljiv se ne broji
  assert.deepEqual(countByIzvor([]), { S: 0, R: 0, H: 0 });
});
