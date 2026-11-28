// Testovi za web/senzori/izvor.js: viewMode i blockSource (oznaka izvora i razlozi).
import test from 'node:test';
import assert from 'node:assert/strict';
import { viewMode, blockSource, REASONS } from '../../web/senzori/izvor.js';

const B = { id: 'brzine', part: 'pogon', fields: ['v', 'w'], notes: { robot: { w: 'ω: ESP je još ne šalje laptopu' } } };
const emptyRun = { cols: { t: [] } };
const someRun = { cols: { t: [0, 20] } };
const robotSt = { session: { kind: 'robot', host: '192.168.4.1' }, sens: { run: someRun }, lidarScan: null };

test('ništa', () => assert.deepEqual(blockSource(B, { session: null, sens: null }, () => false),
  { src: null, reason: 'nije povezano', note: null }));
test('robot bez Nucleo-a: pogon nepovezano', () => {
  const r = blockSource(B, { session: { kind: 'robot' }, sens: { run: emptyRun } }, () => false);
  assert.equal(r.src, null); assert.equal(r.reason, 'Nucleo ne javlja (nema poze)');
});
test('robot sa v bez w: pravo + napomena', () => {
  const r = blockSource(B, robotSt, k => k === 'v');
  assert.equal(r.src, 'pravo'); assert.equal(r.note, 'ω: ESP je još ne šalje laptopu');
});
test('robot sa v i w: bez napomene', () => {
  const r = blockSource(B, robotSt, () => true);
  assert.deepEqual(r, { src: 'pravo', reason: null, note: null });
});
test('robot: polje bez podataka sa REASONS unosom', () => {
  const pid = { id: 'pid', part: 'pogon', fields: ['v_ref'] };
  assert.equal(blockSource(pid, robotSt, () => false).reason, 'Nucleo ga ne šalje (firmver)');
  const bat = { id: 'napajanje', part: null, fields: ['bat'] };
  assert.equal(blockSource(bat, robotSt, () => false).reason, 'INA3221 nije podešen');
  const ul = { id: 'ulazi', part: null, fields: ['btn'], simFields: ['mec'] };
  assert.equal(blockSource(ul, robotSt, () => false).reason, 'ESP ih još ne šalje laptopu');
  assert.equal(blockSource({ id: 'robot', part: 'ir', fields: ['irm'] }, robotSt, () => false).reason,
    'ESP ga još ne šalje laptopu (1 polje u telemetriji)');
  assert.equal(REASONS.enkoderi, 'Nucleo ga ne šalje (firmver)');
});
test('robot: polje bez REASONS unosa: opšti razlog', () => {
  const x = { id: 'nepoznat', part: 'mehanizmi', fields: ['zzz'] };
  assert.equal(blockSource(x, robotSt, () => false).reason, 'robot ga još ne šalje');
});
test('robot: lidar bez kruga i sa krugom', () => {
  const L = { id: 'lidar', part: 'lidar', fields: ['@lidar'] };
  const r = blockSource(L, robotSt, () => false);
  assert.equal(r.src, null); assert.equal(r.reason, 'lidar ugašen: Upali lidar');
  assert.equal(blockSource(L, { ...robotSt, lidarScan: { pts: [] } }, () => true).src, 'pravo');
});
test('veza (fields: []): izvor režima kad god ima sesije ili puštanja', () => {
  const V = { id: 'veza', part: null, fields: [] };
  assert.equal(blockSource(V, robotSt, () => false).src, 'pravo');
  assert.equal(blockSource(V, { session: { kind: 'sim' } }, () => false).src, 'sim');
  assert.equal(blockSource(V, { session: null, sens: { replay: true, name: 'x', t: 1 } }, () => false).src, 'snimak');
  assert.deepEqual(blockSource(V, { session: null, sens: null }, () => false), { src: null, reason: 'nije povezano', note: null });
});
test('hibrid: lidar pravo, ostalo sim; lidar iz snimka = snimak', () => {
  const L = { id: 'lidar', part: 'lidar', fields: ['@lidar'] };
  assert.equal(blockSource(L, { session: { kind: 'sim', lidar: 'robot' } }, () => true).src, 'pravo');
  assert.equal(blockSource(L, { session: { kind: 'sim', lidar: 'file' } }, () => true).src, 'snimak');
  assert.equal(blockSource(B, { session: { kind: 'sim', lidar: 'robot' } }, () => true).src, 'sim');
});
test('SIM napajanje', () => assert.equal(blockSource({ id: 'napajanje', part: null, fields: ['bat'] },
  { session: { kind: 'sim' } }, () => false).reason, 'nema simulacije (samo pravi robot)'));
test('SIM lidar bez krugova', () => assert.equal(blockSource({ id: 'lidar', part: 'lidar', fields: ['@lidar'] },
  { session: { kind: 'sim', lidar: 'sim' } }, () => false).reason, 'na ESP-u: Meni → Lidar test'));
test('simFields: SIM i robot', () => {
  const U = { id: 'ulazi', part: null, fields: ['btn'], simFields: ['mec'] };
  assert.equal(blockSource(U, { session: { kind: 'sim' } }, k => k === 'mec').src, 'sim');
  const r = blockSource(U, robotSt, k => k === 'mec');
  assert.equal(r.src, null); assert.equal(r.reason, 'ESP ih još ne šalje laptopu');
  assert.equal(blockSource(U, robotSt, k => k === 'btn').src, 'pravo');
});
test('snimak pušten: snimak ili nije snimljeno', () => {
  const st = { session: null, sens: { replay: true, name: 'x', t: 3 } };
  assert.equal(blockSource(B, st, () => true).src, 'snimak');
  const r = blockSource(B, st, () => false);
  assert.equal(r.src, null); assert.equal(r.reason, 'nije snimljeno');
});
test('snimak: simFields samo za snimak simulacije', () => {
  const U = { id: 'ulazi', part: null, fields: ['btn'], simFields: ['mec'] };
  const only = k => k === 'mec';
  const simRun = { meta: { origin: { engine: 'sim' } }, cols: { t: [0] } };
  const robRun = { meta: { origin: { engine: 'robot' } }, cols: { t: [0] } };
  assert.equal(blockSource(U, { session: null, sens: { replay: true, run: simRun } }, only).src, 'snimak');
  assert.equal(blockSource(U, { session: null, sens: { replay: true, run: robRun } }, only).src, null);
});
test('snimak: lidar pita has("@lidar")', () => {
  const L = { id: 'lidar', part: 'lidar', fields: ['@lidar'] };
  const st = { session: null, sens: { replay: true } };
  assert.equal(blockSource(L, st, k => k === '@lidar').src, 'snimak');
  assert.equal(blockSource(L, st, () => false).reason, 'nije snimljeno');
});
test('napomena samo kad je src postavljen', () => {
  assert.equal(blockSource(B, { session: { kind: 'robot' }, sens: { run: emptyRun } }, () => false).note, null);
  assert.equal(blockSource(B, { session: { kind: 'sim' } }, k => k === 'v').note, null);
});

test('viewMode: tekstovi', () => {
  assert.deepEqual(viewMode({ session: null, sens: null },),
    { mode: 'nista', text: 'Ništa nije povezano: Poveži robota ili pokreni simulaciju u Vožnji' });
  assert.deepEqual(viewMode({ session: { kind: 'robot', host: '10.0.0.5' } }),
    { mode: 'robot', text: 'Prikazuje: pravi robot · 10.0.0.5' });
  assert.equal(viewMode({ session: { kind: 'robot', host: 'x', virtual: true } }).text, 'Prikazuje: virtuelni robot');
  assert.deepEqual(viewMode({ session: { kind: 'sim' } }),
    { mode: 'sim', text: 'Prikazuje: simulacija (Vožnja SIM) · ovo nije pravi robot' });
  assert.deepEqual(viewMode({ session: { kind: 'sim', lidar: 'robot' } }),
    { mode: 'hibrid', text: 'Prikazuje: hibrid · lidar sa pravog robota, ostalo simulirano' });
  assert.equal(viewMode({ session: { kind: 'sim', lidar: 'file' } }).text,
    'Prikazuje: hibrid · lidar iz snimka, ostalo simulirano');
});
test('viewMode: snimak', () => {
  assert.deepEqual(viewMode({ session: null, sens: { replay: true, name: 'abc', t: 42.3 } }),
    { mode: 'snimak', text: 'Prikazuje: snimak abc · 42,3 s' });
  assert.equal(viewMode({ session: null, sens: { replay: false, name: 'x' } }).mode, 'nista');
  assert.equal(viewMode({ session: { kind: 'sim' }, sens: { replay: true, name: 'x', t: 1 } }).mode, 'sim');
});
