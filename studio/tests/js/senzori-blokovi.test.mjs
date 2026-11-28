// Testovi za web/senzori/blokovi/: spisak blokova (redosled, mesto u rasporedu B), oblik modula bloka, `has` (da li
// polje stvarno stiže) i procena svih blokova za zaglavlje Senzora (brojač radi / upozorenje / bez podataka).
import test from 'node:test';
import assert from 'node:assert/strict';
import { BLOCKS, SLOTS, makeHas, evalBlocks, counts, warnWord } from '../../web/senzori/blokovi/index.js';
import { buildRun } from '../../web/core/run.js';
import { scanXY } from '../../web/senzori/blokovi/lidar.js';
import { wheelsAt } from '../../web/senzori/blokovi/robot.js';

const IDS = ['lidar', 'robot', 'brzine', 'pid', 'napajanje', 'aktuatori', 'enkoderi', 'ulazi', 'mec', 'veza'];
const byId = id => BLOCKS.find(b => b.id === id);

test('BLOCKS: tačan redosled', () => {
  assert.deepEqual(BLOCKS.map(b => b.id), IDS);
});

test('BLOCKS: ime, „Kako proveriti“, mesto u rasporedu B', () => {
  const want = { lidar: 'top', robot: 'sketch', brzine: 'right', pid: 'right', napajanje: 'right', aktuatori: 'bottom',
    enkoderi: 'bottom', ulazi: 'bottom', mec: 'bottom', veza: 'bottom' };
  for (const b of BLOCKS) {
    assert.ok(typeof b.name === 'string' && b.name.length > 0, b.id);
    assert.ok(Array.isArray(b.hints) && b.hints.length > 0, b.id);
    assert.ok(SLOTS.includes(b.slot), b.id);
    assert.equal(b.slot, want[b.id], b.id);
    assert.equal(typeof b.view, 'function', b.id);
  }
  assert.deepEqual(SLOTS, ['top', 'sketch', 'right', 'bottom']);
});

test('BLOCKS: polja za oznaku izvora (blockSource)', () => {
  const f = id => { const b = byId(id); return { part: b.part, fields: b.fields, simFields: b.simFields, notes: b.notes }; };
  assert.deepEqual(f('lidar'), { part: 'lidar', fields: ['@lidar'], simFields: undefined, notes: undefined });
  assert.deepEqual(f('robot'), { part: 'ir', fields: ['ir'], simFields: undefined, notes: undefined });
  assert.deepEqual(f('brzine'), { part: 'pogon', fields: ['v', 'w'], simFields: undefined,
    notes: { robot: { w: 'ω: ESP je još ne šalje laptopu' } } });
  assert.deepEqual(f('pid'), { part: 'pogon', fields: ['v_ref', 'w_ref'], simFields: undefined, notes: undefined });
  assert.deepEqual(f('napajanje'), { part: null, fields: ['bat'], simFields: undefined, notes: undefined });
  assert.deepEqual(f('aktuatori'), { part: 'mehanizmi', fields: ['act'], simFields: undefined, notes: undefined });
  assert.deepEqual(f('enkoderi'), { part: 'pogon', fields: ['ox', 'oy', 'oth'], simFields: undefined, notes: undefined });
  assert.deepEqual(f('ulazi'), { part: null, fields: ['btn'], simFields: ['mec'], notes: undefined });
  assert.deepEqual(f('mec'), { part: null, fields: ['mec'], simFields: undefined, notes: undefined });
  assert.deepEqual(f('veza'), { part: null, fields: [], simFields: undefined, notes: undefined });
});

test('view bez izvora: status none', () => {
  for (const b of BLOCKS) {
    const v = b.view({ src: null });
    assert.equal(v.status, 'none', b.id);
    assert.equal(typeof v.text, 'string', b.id);
    assert.ok(Array.isArray(v.vals), b.id);
    const full = b.view({ st: { session: null, sens: null }, run: null, t: 0, src: null, profile: null });
    assert.equal(full.status, 'none', b.id);
  }
});

test('Kako proveriti: IR samo da/ne (domet točkićem), enkoderi Nuliraj / 50 cm / < 5 mm', () => {
  const ir = byId('robot').hints.join(' ');
  assert.match(ir, /da\/ne/); assert.match(ir, /točkić/);
  const enk = byId('enkoderi').hints.join(' ');
  assert.match(enk, /Nuliraj/); assert.match(enk, /50 cm/); assert.match(enk, /5 mm/);
});

const simRun = () => buildRun({ meta: {}, result: {}, events: [[10, 'lidar', { pts: [[0, 500]], hz: 9.5 }]],
  cols: { t: [0, 100], v: [0.1, 0.25], w: [0, 0.5], mec: ['MIROVANJE', 'MIROVANJE'] } });

test('makeHas: lidar iz kruga sesije ili snimka, ostalo iz kolona; bez snimka nema ničega', () => {
  assert.equal(makeHas({ lidarScan: { pts: [] }, sens: null })('@lidar'), true);
  assert.equal(makeHas({ lidarScan: null, sens: null })('@lidar'), false);
  assert.equal(makeHas({ lidarScan: null, sens: null })('v'), false);
  const run = simRun();
  const has = makeHas({ lidarScan: null, sens: { run, t: 100 } });
  assert.equal(has('@lidar'), true);
  assert.equal(has('v'), true);
  assert.equal(has('w_ref'), false);                // kolona postoji, sve null
  assert.equal(has('bat'), false);                  // kolone nema
  const noLidar = buildRun({ meta: {}, result: {}, events: [], cols: { t: [0], v: [0] } });
  assert.equal(makeHas({ lidarScan: null, sens: { run: noLidar, t: 0 } })('@lidar'), false);
});

test('evalBlocks: ništa povezano -> svi bez podataka, razlog „nije povezano“', () => {
  const list = evalBlocks({ session: null, sens: null, lidarScan: null, profile: null });
  assert.deepEqual(list.map(x => x.b.id), IDS);
  for (const x of list) {
    assert.equal(x.s.src, null, x.b.id);
    assert.equal(x.s.reason, 'nije povezano', x.b.id);
    assert.equal(x.v.status, 'none', x.b.id);
  }
  assert.deepEqual(counts(list), { ok: 0, warn: 0, none: 10 });
});

test('evalBlocks: SIM sesija sa brzinama i krugom lidara', () => {
  const run = simRun();
  const st = { session: { kind: 'sim', lidar: 'sim' }, sens: { run, t: run.duration, replay: false, name: '' },
    lidarScan: null, profile: null };
  const list = evalBlocks(st), get = id => list.find(x => x.b.id === id);
  assert.equal(get('brzine').s.src, 'sim');
  assert.equal(get('brzine').v.status, 'ok');
  assert.ok(get('brzine').v.vals.length > 0);
  assert.equal(get('lidar').s.src, 'sim');
  assert.equal(get('napajanje').s.src, null);
  assert.equal(get('napajanje').v.status, 'none');
  assert.equal(get('veza').s.src, 'sim');
  assert.equal(get('ulazi').s.src, 'sim');            // simFields: činč iz stanja meča
  for (const x of list) {
    assert.ok(['ok', 'warn', 'none'].includes(x.v.status), x.b.id);
    for (const p of x.v.vals) assert.ok(Array.isArray(p) && p.length === 2 && p.every(s => typeof s === 'string'), x.b.id);
  }
  const c = counts(list);
  assert.equal(c.ok + c.warn + c.none, 10);
  assert.ok(c.ok >= 4);
});

test('evalBlocks: blok koji baci izuzetak ne ruši ostale', () => {
  const bad = { id: 'x', name: 'X', part: null, fields: [], hints: ['h'], slot: 'bottom', view() { throw new Error('bum'); } };
  const [x] = evalBlocks({ session: { kind: 'sim', lidar: 'sim' }, sens: null }, [bad]);
  assert.equal(x.v.status, 'none');
  assert.match(x.v.text, /bum/);
});

test('warnWord: 1 upozorenje, 2/5/11 upozorenja, 21 upozorenje', () => {
  assert.equal(warnWord(0), 'upozorenja');
  assert.equal(warnWord(1), 'upozorenje');
  assert.equal(warnWord(2), 'upozorenja');
  assert.equal(warnWord(5), 'upozorenja');
  assert.equal(warnWord(11), 'upozorenja');
  assert.equal(warnWord(21), 'upozorenje');
});

// ---------------- Zadatak 8: Odozgo · lidar i Robot · IR ----------------

const lidarBlock = byId('lidar'), robotBlock = byId('robot');
const ROBOT_SES = { kind: 'robot', host: 'eurokik.local', virtual: false, lidar: 'sim' };
const scanOf = (hz, wall = performance.now()) => ({ t: 0, pts: [0, 500, 10, 600], o: [0, 0, 300], near: [500, 0], hz, wall,
  kind: 'robot' });
const dWithHz = (hz, st = {}) => ({ st: { session: ROBOT_SES, lidarScan: scanOf(hz), ...st }, run: null, t: 0, src: 'pravo',
  reason: null, note: null, profile: null });

test('lidar upozorenje ispod 5 Hz', () => assert.equal(lidarBlock.view(dWithHz(4)).status, 'warn'));

test('lidar: svež krug i 10 Hz radi; Hz, tačaka, najbliža grupa i „grupe računa laptop“', () => {
  const v = lidarBlock.view(dWithHz(10));
  assert.equal(v.status, 'ok');
  assert.deepEqual(v.vals.map(p => p[0]), ['Hz', 'tačaka', 'najbliža grupa']);
  assert.equal(v.vals[0][1], '10,0');
  assert.equal(v.vals[1][1], '2');                         // pts = [ugao, mm, ugao, mm]
  assert.equal(v.foot, 'grupe računa laptop');
});

test('lidar: krug stariji od 1,5 s -> upozorenje (i bez Hz)', () => {
  const d = dWithHz(10);
  d.st.lidarScan.wall = performance.now() - 2000;
  assert.equal(lidarBlock.view(d).status, 'warn');
  const noHz = dWithHz(null);
  assert.equal(lidarBlock.view(noHz).status, 'ok');           // nema Hz: ne upozorava na Hz
  noHz.st.lidarScan.wall = performance.now() - 1600;
  assert.equal(lidarBlock.view(noHz).status, 'warn');
});

test('lidar: krug snimka u trenutku d.t (bez sesije), bez kruga nema podataka', () => {
  const run = buildRun({ meta: {}, result: {}, events: [[100, 'lidar', { pts: [0, 800], hz: 9.8, pose: [0, 0, 0] }]],
    cols: { t: [0, 100, 200] } });
  const v = lidarBlock.view({ st: { session: null }, run, t: 150, src: 'snimak', profile: null });
  assert.equal(v.status, 'ok');
  assert.equal(v.vals[0][1], '9,8');
  assert.equal(lidarBlock.view({ st: { session: null }, run, t: 50, src: 'snimak', profile: null }).status, 'none');
});

test('lidar: tačke kruga u koordinatama robota (ugao + levo, od položaja lidara)', () => {
  const p = scanXY({ pts: [0, 500, 90, 1000], o: [10, -5, 300] });
  assert.equal(p.length, 2);
  assert.ok(Math.abs(p[0][0] - 510) < 1e-9 && Math.abs(p[0][1] + 5) < 1e-9);
  assert.ok(Math.abs(p[1][0] - 10) < 1e-9 && Math.abs(p[1][1] - 995) < 1e-9);
  assert.equal(scanXY({ pts: [0, 0, 5, 300] }).length, 1);       // 0 mm = nema tačke
  assert.deepEqual(scanXY(null), []);
});

test('lidar dugmad: ROBOT Upali/Ugasi lidar (sivo dok taktika radi), hibrid i SIM bez dugmeta', () => {
  const sent = [];
  const ctx = { command: c => { sent.push(c); return true; } };
  const a = lidarBlock.actions({ ...dWithHz(10), ctx });
  assert.equal(a.length, 1);
  assert.equal(a[0].label, 'Upali lidar');
  assert.ok(!a[0].disabled);
  a[0].run();
  assert.deepEqual(sent, [['lidar', 'on']]);
  const on = lidarBlock.actions({ ...dWithHz(10, { robotLidarSeen: true, robotLidar: 'scan' }), ctx });
  assert.equal(on[0].label, 'Ugasi lidar');
  on[0].run();
  assert.deepEqual(sent[1], ['lidar', 'off']);
  const replied = lidarBlock.actions({ st: { session: ROBOT_SES, lidarReply: { cmd: 'lidar', ok: true, lidar: { on: true } } },
    src: null });
  assert.equal(replied[0].label, 'Ugasi lidar');                // telemetrija ne javlja stanje: ono što je poslato
  const busy = lidarBlock.actions(dWithHz(10, { running: 'primer' }));
  assert.equal(busy[0].disabled, true);
  assert.match(busy[0].title, /taktika primer radi/);
  const off = lidarBlock.actions({ st: { session: ROBOT_SES, lidarScan: null }, src: null });
  assert.equal(off.length, 1);                                  // ugašen lidar: dugme je tu (blok je nepovezan)
  const hib = { st: { session: { kind: 'sim', lidar: 'robot' }, lidarScan: scanOf(10) }, src: 'pravo' };
  assert.deepEqual(lidarBlock.actions(hib), []);
  assert.deepEqual(lidarBlock.actions({ st: { session: { kind: 'sim', lidar: 'sim' } }, src: 'sim' }), []);
  assert.deepEqual(lidarBlock.actions({ st: { session: null }, src: null }), []);
});

test('evalBlocks: ctx i redraw panela stižu u d (dugmad i crtanje)', () => {
  const ctx = { command: () => true }, redraw = () => {};
  const list = evalBlocks({ session: null, sens: null }, BLOCKS, { ctx, redraw });
  assert.equal(list[0].d.ctx, ctx);
  assert.equal(list[0].d.redraw, redraw);
  assert.equal(evalBlocks({ session: null, sens: null })[0].d.ctx, null);
});

const irRun = () => buildRun({ meta: {}, result: {}, events: [],
  cols: { t: [0, 100], ir: [0, 0b10000001], irm: [255, 255], ox: [0, 100], oy: [0, 0], oth: [0, 0] } });

test('Robot · IR: aktivni i maska; status ok kad ima IR', () => {
  const v = robotBlock.view({ st: {}, run: irRun(), t: 100, src: 'sim', profile: null });
  assert.equal(v.status, 'ok');
  assert.deepEqual(v.vals, [['aktivni', 'FLD BRU'], ['maska', 'svi']]);
  const before = robotBlock.view({ st: {}, run: irRun(), t: 0, src: 'sim', profile: null });
  assert.deepEqual(before.vals, [['aktivni', 'nijedan'], ['maska', 'svi']]);
});

test('Robot · IR detalj: 8 senzora sa mestom i stanjem', () => {
  const html = robotBlock.html({ st: {}, run: irRun(), t: 100, src: 'sim', profile: null }, true);
  for (const n of ['FLD', 'FLU', 'FRD', 'FRU', 'BLD', 'BLU', 'BRD', 'BRU']) assert.match(html, new RegExp(n));
  assert.equal((html.match(/<tr class="on/g) || []).length, 2);  // FLD i BRU vide
  assert.match(html, /spreda levo/);
  assert.match(html, /pozadi desno/);
});

test('Robot · IR: mm pasivnih točkova od „Nuliraj“ (sensZero) ili od početka snimka', () => {
  const run = irRun();
  const w = wheelsAt({ st: {}, run, t: 100 }, 286);
  assert.ok(Math.abs(w.L - 100) < 1e-9 && Math.abs(w.R - 100) < 1e-9);
  assert.ok(Math.abs(wheelsAt({ st: { sensZero: 100 }, run, t: 100 }, 286).L) < 1e-9);
  assert.equal(wheelsAt({ st: {}, run: null, t: 0 }, 286), null);
});
