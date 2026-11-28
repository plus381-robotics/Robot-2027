// Testovi za web/shell/strip.js: snimak -> polja trake, tekstovi polja (Izvor, Veza, Meč, Poza, Korak).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildRun } from '../../web/core/run.js';
import { snapshotAt, stripView, matchView, linkView, connectView, sourceView, linkStateOf, SRC_COLOR } from '../../web/shell/strip.js';

const fixture = () => JSON.parse(readFileSync(new URL('./fixtures/run_sve_komande.json', import.meta.url), 'utf8'));
const IR = ['FLU', 'FLD', 'FRU', 'FRD', 'BLU', 'BLD', 'BRU', 'BRD'];

test('snapshotAt: poza, meč, korak, detekcija, greške u trenutku t', () => {
  const run = buildRun(fixture());
  const s = snapshotAt(run, 2000, { irNames: IR });
  assert.deepEqual(s.pose, { x: 487.26, y: 1000, th: 0 });
  assert.deepEqual(s.match, { state: 'MEC', ms: 700 });
  assert.equal(s.step.idx, 3);
  assert.equal(s.step.n, 16);
  assert.equal(s.step.name, 'GOTO 600,1000');
  assert.equal(s.step.active, true);
  assert.ok(Math.abs(s.step.frac - 650 / 3312) < 1e-9);
  assert.equal(s.det, 'ništa');                              // IR postoji, ništa ne vidi
  assert.equal(s.errors, 0);
  assert.equal(s.label, 'sve_komande');
  assert.equal(s.robot, false);
  const s0 = snapshotAt(run, 0, { irNames: IR });            // pre taktike: bez koraka, meč miruje
  assert.equal(s0.step, null);
  assert.deepEqual(s0.match, { state: 'NEMA', ms: null });
  const s2 = snapshotAt(run, 2600, { irNames: IR });         // u 2570 krenuo korak 5 (4 je trajao 0 ms)
  assert.equal(s2.step.idx, 5);
  assert.equal(s2.step.name, 'OKRET na 90');
  // završen korak bez sledećeg: neaktivan, traka puna
  const small = buildRun({ meta: {}, result: {}, cols: { t: [0, 100, 200], x: [1, 2, 3], y: [4, 5, 6], th: [0, 0, 0] },
    events: [[0, 'step', [1, 'a', 1000, null]], [50, 'step_end', [1, 'a', false, 'TIMEOUT', 50]]] });
  const s3 = snapshotAt(small, 100);
  assert.deepEqual([s3.step.idx, s3.step.active, s3.step.frac, s3.step.ok, s3.step.n], [1, false, 1, false, null]);
  assert.deepEqual(s3.match, { state: null, ms: null });
  assert.equal(s3.det, null);
});

test('snapshotAt: IR vidi, greške se broje do t, bez IR kolone nema detekcije', () => {
  const d = fixture();
  d.cols.ir = d.cols.ir.map((v, i) => (i >= 100 ? 0b1001 : 0));
  d.events.push([1500, 'log', 'GRESKA: nešto'], [3000, 'log', 'PREKID: STOP']);
  d.events.sort((a, b) => a[0] - b[0]);
  const run = buildRun(d);
  assert.equal(snapshotAt(run, 2000, { irNames: IR }).det, 'IR FLU FRD');
  assert.equal(snapshotAt(run, 2000, { irNames: IR }).errors, 1);
  assert.equal(snapshotAt(run, 7000, { irNames: IR }).errors, 2);
  const r2 = fixture();
  delete r2.cols.ir;                                         // robot koji ne šalje IR: polje se ne prikazuje (ne lažna nula)
  assert.equal(snapshotAt(buildRun(r2), 2000, { irNames: IR }).det, null);
  assert.equal(snapshotAt(null, 0), null);
  assert.equal(snapshotAt(buildRun({ meta: {}, result: {}, events: [], cols: {} }), 0), null);
});

test('matchView: miruje / NAORUŽAN / MEČ odbrojava / KRAJ', () => {
  assert.deepEqual(matchView(null), { text: 'miruje', cls: 'idle' });
  assert.deepEqual(matchView({ state: 'NEMA', ms: null }), { text: 'miruje', cls: 'idle' });
  assert.deepEqual(matchView({ state: 'NAORUZAN', ms: null }), { text: 'NAORUŽAN', cls: 'armed' });
  assert.deepEqual(matchView({ state: 'MEC', ms: 37200 }), { text: 'MEČ 62.8 s', cls: 'run' });
  assert.deepEqual(matchView({ state: 'MEC', ms: 100000 }), { text: 'KRAJ', cls: 'end' });
  assert.deepEqual(matchView({ state: 'KRAJ', ms: null }), { text: 'KRAJ', cls: 'end' });
  assert.deepEqual(matchView({ state: null, ms: 1000 }), { text: 'MEČ 99.0 s', cls: 'run' });
});

test('linkView: sim, robot povezivanje / nema telemetrije / povezan / podaci stari / veza izgubljena', () => {
  assert.deepEqual(linkView({ session: null }), { cls: 'idle', text: 'nije povezano', connect: true, disconnect: false });
  const sim = { session: { kind: 'sim' } };
  assert.equal(linkView({ ...sim, speed: null }).text, 'pokretanje…');
  assert.deepEqual(linkView({ ...sim, speed: 2, paused: false }), { cls: 'ok', text: 'simulacija radi · ×2', connect: true, disconnect: false });
  assert.deepEqual(linkView({ ...sim, speed: 1, paused: true }), { cls: 'warn', text: 'simulacija na pauzi', connect: true, disconnect: false });
  const rob = { session: { kind: 'robot', host: 'eurokik.local' } };
  assert.deepEqual(linkView({ ...rob, telemetry: null }), { cls: 'idle', text: 'povezivanje…', connect: false, disconnect: true });
  assert.deepEqual(linkView({ ...rob, telemetry: false, linkState: 'stale' }), { cls: 'warn', text: 'nema telemetrije', connect: false, disconnect: true });
  assert.deepEqual(linkView({ ...rob, telemetry: false, linkState: 'lost' }), { cls: 'bad', text: 'nema telemetrije', connect: false, disconnect: true });
  assert.deepEqual(linkView({ ...rob, telemetry: true, linkAge: 120 }), { cls: 'ok', text: 'povezan', connect: false, disconnect: true });
  assert.deepEqual(linkView({ ...rob, telemetry: true, linkAge: 2300 }), { cls: 'warn', text: 'podaci stari 2.3 s', connect: false, disconnect: true });
  assert.deepEqual(linkView({ ...rob, telemetry: true, linkAge: 7400 }), { cls: 'bad', text: 'veza izgubljena 7 s', connect: false, disconnect: true });
  assert.equal(linkStateOf(1500), 'ok');
  assert.equal(linkStateOf(1501), 'stale');
  assert.equal(linkStateOf(5001), 'lost');
});

test('sourceView: SIM / HIBRID / ROBOT / SNIMAK sa bojama', () => {
  assert.deepEqual(sourceView({ session: null, snap: null }), { kind: 'SIM', sub: 'spremno', color: SRC_COLOR.SIM });
  assert.equal(sourceView({ session: { kind: 'sim', lidar: 'sim' } }).sub, 'Live');
  assert.deepEqual(sourceView({ session: { kind: 'sim', lidar: 'robot' } }),
    { kind: 'HIBRID', sub: 'lidar sa robota', color: '#8a5a00' });
  assert.equal(sourceView({ session: { kind: 'sim', lidar: 'file:x.jsonl.gz' } }).sub, 'lidar iz snimka');
  assert.deepEqual(sourceView({ session: { kind: 'robot', host: 'eurokik.local' } }),
    { kind: 'ROBOT', sub: 'eurokik.local', color: '#c62828' });
  assert.equal(sourceView({ session: { kind: 'robot', host: '127.0.0.1', virtual: true } }).sub, 'virtuelni');
  assert.deepEqual(sourceView({ session: null, snap: { label: 'primer' } }), { kind: 'SNIMAK', sub: 'primer', color: '#3a4250' });
});

test('snapshotAt.tactic: taktika koja je poslednja krenula do t (i druga, npr. sa ESP menija)', () => {
  const run = buildRun(fixture());                           // događaj "tactic" u 1330 ms
  assert.equal(snapshotAt(run, 1000).tactic, null);
  assert.equal(snapshotAt(run, 1330).tactic, 'sve_komande');
  assert.equal(snapshotAt(run, 5000).tactic, 'sve_komande');
  const two = buildRun({ meta: { tactic: 'primer' }, result: {}, cols: { t: [0, 100, 200, 300], x: [1, 1, 1, 1], y: [1, 1, 1, 1], th: [0, 0, 0, 0] },
    events: [[50, 'tactic', ['primer', 'zuta']], [210, 'tactic', ['kamenolomi', 'zuta']]] });
  assert.equal(snapshotAt(two, 100).tactic, 'primer');
  assert.equal(snapshotAt(two, 300).tactic, 'kamenolomi');    // meta.tactic (prva) je zastareo, ovo nije
  assert.equal(snapshotAt(two, 300).label, 'primer');
});

test('sourceView: u sesiji podnaslov nosi taktiku koja radi (ROBOT: running, SIM: snimak sesije)', () => {
  const rob = { kind: 'robot', host: '127.0.0.1', virtual: true };
  assert.equal(sourceView({ session: rob, running: 'primer', snap: { tactic: 'stara' } }).sub, 'virtuelni · primer');
  assert.equal(sourceView({ session: rob, running: null, snap: { tactic: 'stara' } }).sub, 'virtuelni');   // ne radi nijedna
  assert.equal(sourceView({ session: { kind: 'robot', host: 'eurokik.local' }, running: 'x' }).sub, 'eurokik.local · x');
  assert.equal(sourceView({ session: { kind: 'sim', lidar: 'sim' }, snap: { tactic: 'kamenolomi' } }).sub, 'Live · kamenolomi');
  assert.equal(sourceView({ session: { kind: 'sim', lidar: 'sim' }, snap: { tactic: null } }).sub, 'Live');
  assert.equal(sourceView({ session: { kind: 'sim', lidar: 'robot' }, snap: { tactic: 'a' } }).sub, 'lidar sa robota · a');
  assert.equal(sourceView({ session: null, running: 'x', snap: { label: 'primer', tactic: 'primer' } }).sub, 'primer');   // snimak: kao pre
});

test('stripView: poza, korak, polja bez podatka se ne prikazuju, STOP neaktivan bez sesije', () => {
  const snap = { pose: { x: 1240.4, y: 829.6, th: 91.7 }, match: { state: 'MEC', ms: 37200 },
    step: { idx: 7, n: 15, name: 'ka_kamenolomu_2', active: true, frac: 0.4, ok: null }, det: null, errors: 2, label: 'x' };
  const v = stripView({ session: { kind: 'sim' }, speed: 1, snap });
  assert.equal(v.pose.text, '1240, 830 · 92°');
  assert.equal(v.match.text, 'MEČ 62.8 s');
  assert.deepEqual(v.step, { text: '7/15 ka_kamenolomu_2', frac: 0.4, over: false, fail: false });
  assert.equal(v.det, null);
  assert.equal(v.errors, 2);
  assert.equal(v.stopIdle, false);
  const over = stripView({ session: { kind: 'sim' }, snap: { ...snap, step: { ...snap.step, n: null, frac: 1.5 } } });
  assert.deepEqual(over.step, { text: '#7 ka_kamenolomu_2', frac: 1, over: true, fail: false });
  const idle = stripView({ session: null, snap: null });
  assert.equal(idle.pose, null);
  assert.equal(idle.step, null);
  assert.equal(idle.match.text, 'miruje');
  assert.equal(idle.errors, 0);
  assert.equal(idle.stopIdle, true);
  const noPose = stripView({ session: { kind: 'robot' }, telemetry: true, linkAge: 100, snap: null });
  assert.deepEqual(noPose.pose, { text: 'nema poze (STM32)', cls: 'warn' });
});

test('bez sesije: dugme Poveži robota', () => {
  const v = linkView({ session: null });
  assert.equal(v.connect, true); assert.equal(v.disconnect, false); assert.equal(v.text, 'nije povezano');
});
test('ROBOT: Prekini, tekst kao pre', () => {
  const v = linkView({ session: { kind: 'robot', host: 'eurokik.local' }, telemetry: true, linkAge: 100 });
  assert.equal(v.disconnect, true); assert.equal(v.connect, false); assert.equal(v.text, 'povezan');
});
test('hibrid sa pravim lidarom: lidar: host, bez Prekini', () => {
  const v = linkView({ session: { kind: 'sim', lidar: 'robot', host: 'eurokik.local' }, speed: 1,
    lidarScan: { wall: 1000 } }, 1500);
  assert.equal(v.text, 'lidar: eurokik.local'); assert.equal(v.cls, 'ok'); assert.equal(v.disconnect, false);
  assert.equal(v.connect, false);
});
test('hibrid: lidar stao duže od 1,5 s je warn', () => {
  assert.equal(linkView({ session: { kind: 'sim', lidar: 'robot', host: 'h' }, speed: 1, lidarScan: { wall: 0 } }, 2000).cls, 'warn');
  assert.equal(linkView({ session: { kind: 'sim', lidar: 'robot', host: 'h' }, speed: 1, lidarScan: { wall: 0 } }, 1500).cls, 'ok');
});
test('hibrid: još nema skena je warn, tekst ostaje; bez hosta lidar: robot', () => {
  const v = linkView({ session: { kind: 'sim', lidar: 'robot', host: 'h' }, speed: 1 }, 5000);
  assert.deepEqual(v, { cls: 'warn', text: 'lidar: h', connect: false, disconnect: false });
  assert.equal(linkView({ session: { kind: 'sim', lidar: 'robot' }, speed: 1 }, 0).text, 'lidar: robot');
});
test('hibrid iz snimka: lidar iz snimka', () => {
  const v = linkView({ session: { kind: 'sim', lidar: 'file' }, speed: 1 });
  assert.equal(v.text, 'lidar iz snimka'); assert.equal(v.cls, 'ok');
  assert.equal(linkView({ session: { kind: 'sim', lidar: 'file' }, speed: 1, paused: true }).cls, 'warn');
  assert.equal(v.connect, false); assert.equal(v.disconnect, false);
});
test('SIM sesija (bez hibrida): tekst simulacije i dugme Poveži robota (klik daje razlog); hibrid bez dugmeta', () => {
  for (const lidar of [undefined, 'sim']) {
    for (const extra of [{ speed: null }, { speed: 1 }, { speed: 1, paused: true }]) {
      const v = linkView({ session: { kind: 'sim', lidar }, ...extra });
      assert.equal(v.connect, true, JSON.stringify([lidar, extra])); assert.equal(v.disconnect, false);
    }
  }
  assert.equal(linkView({ session: { kind: 'sim', lidar: 'sim' }, speed: 1 }).text, 'simulacija radi · ×1');
  assert.equal(stripView({ session: { kind: 'sim', lidar: 'sim' }, speed: 1, snap: null }).link.connect, true);
  for (const lidar of ['robot', 'file']) {
    assert.equal(linkView({ session: { kind: 'sim', lidar, host: 'h' }, speed: 1 }, 0).connect, false, lidar);
    assert.equal(linkView({ session: { kind: 'sim', lidar, host: 'h' }, speed: null }, 0).connect, false, lidar);
  }
});
test('SIM sesija: Poveži se odbija sa razlogom', () => {
  assert.deepEqual(connectView({ session: { kind: 'sim' } }), { ok: false, reason: 'Sesija radi: prvo Završi u Vožnji' });
  assert.deepEqual(connectView({ session: null }), { ok: true, reason: null });
  assert.deepEqual(connectView({ session: { kind: 'robot' } }), { ok: false, reason: 'Već je povezan: Prekini pa poveži ponovo' });
});
