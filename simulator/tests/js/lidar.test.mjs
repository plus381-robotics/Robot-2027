// Testovi za web/core/lidar.js (Test dela → Lidar): projekcije radar / sto, slojevi, puštanje snimka, brojke, prefs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { scanPose, radarView, radarXY, tableView, tableXY, layerItems, playIndex, fmtAge, fmtGroup, statsRows,
  loadPrefs, savePrefs, PREFS_KEY, DEFAULT_PREFS } from '../../web/core/lidar.js';

// Međukoraci kao iz POST /api/lidar/stages (eurosim/lidarview.py).
const STAGES = {
  in: [[1920, 1000], [1930, 1050]], out: [[3200, 1400]],
  raw: [[420, 0, 1], [430, 50, 1], [1700, 400, 0]],
  groups: [{ x: 1925, y: 1025, rx: 425, ry: 25, n: 3, dist: 420, angle: 3.4 }, { x: 600, y: 300, rx: -900, ry: -700, n: 4, dist: 1100, angle: -142 }],
  nearest: { x: 1925, y: 1025, rx: 425, ry: 25, n: 3, dist: 420, angle: 3.4 }, frame: 'sto', by: 'laptop', esp_near: null,
};

test('scanPose: poza samo kad je ima (nopose / null / neispravna -> null)', () => {
  assert.deepEqual(scanPose({ pose: [1, 2, 3] }), [1, 2, 3]);
  assert.equal(scanPose({ pose: [1, 2, 3], nopose: true }), null);          // robot bez STM32: lažna poza starta
  assert.equal(scanPose({ pose: null }), null);
  assert.equal(scanPose({ pose: [1, 2] }), null);
  assert.equal(scanPose({ pose: [1, NaN, 0] }), null);
  assert.equal(scanPose(null), null);
});

test('radar: robot u centru, napred gore, levo levo; domet do ivice kruga', () => {
  const v = radarView(400, 300, 2000, 10);                   // manja stranica 300: poluprečnik 140 px = 2000 mm
  assert.equal(v.cx, 200); assert.equal(v.cy, 150);
  assert.ok(Math.abs(v.k * 2000 - 140) < 1e-9);
  assert.deepEqual(radarXY(0, 0, v), [200, 150]);
  const [fx, fy] = radarXY(1000, 0, v);                       // 1 m napred -> gore
  assert.equal(fx, 200); assert.ok(Math.abs(fy - 80) < 1e-9);
  const [lx, ly] = radarXY(0, 1000, v);                       // 1 m levo -> levo
  assert.ok(Math.abs(lx - 130) < 1e-9); assert.equal(ly, 150);
  assert.ok(radarView(10, 10, 4000).k > 0);                   // sitno platno: bez deljenja nulom / negativnog
});

test('sto: ceo sto u platnu, y gore, razmera ista po obe ose', () => {
  const v = tableView(624, 424, { w: 3000, h: 2000 }, 12);   // 600 × 400 px: 0.2 px/mm
  assert.ok(Math.abs(v.k - 0.2) < 1e-12);
  assert.deepEqual(tableXY(0, 0, v), [12, 412]);              // donji levi ugao
  assert.deepEqual(tableXY(3000, 2000, v), [612, 12]);        // gornji desni
  const w = tableView(1000, 300);                             // široko platno: sto centriran po x
  const [a] = tableXY(0, 0, w), [b] = tableXY(3000, 0, w);
  assert.ok(Math.abs((a + b) / 2 - 500) < 1e-9);
  const m = tableView(624, 424, { w: 3000, h: 2000 }, 12, 500);   // 500 mm oko stola: 4000 × 3000 mm u 600 × 400 px
  assert.ok(Math.abs(m.k - 0.1333333333) < 1e-6);
  const [mx, my] = tableXY(-500, -500, m);                      // ugao okvira van stola je na ivici platna
  assert.ok(Math.abs(mx - 45.33) < 0.01 && Math.abs(my - 412) < 0.01);
  assert.deepEqual(tableXY(1500, 1000, m), [312, 212]);          // sredina stola u sredini platna
});

test('layerItems: slojevi sirovo / van stola / grupe se gase nezavisno', () => {
  const all = layerItems(STAGES);
  assert.equal(all.tableIn.length, 2); assert.equal(all.tableOut.length, 1);
  assert.deepEqual(all.radarIn.map(p => p[2]), [1, 1]); assert.deepEqual(all.radarOut.map(p => p[2]), [0]);
  assert.equal(all.groups.length, 2); assert.equal(all.nearest.dist, 420);
  const noRaw = layerItems(STAGES, { sirovo: false, van: true, grupe: true });
  assert.deepEqual([noRaw.tableIn, noRaw.radarIn], [[], []]); assert.equal(noRaw.tableOut.length, 1);
  const noOut = layerItems(STAGES, { sirovo: true, van: false, grupe: true });
  assert.deepEqual([noOut.tableOut, noOut.radarOut], [[], []]); assert.equal(noOut.radarIn.length, 2);
  const noGr = layerItems(STAGES, { grupe: false });          // ostali slojevi podrazumevano upaljeni
  assert.deepEqual(noGr.groups, []); assert.equal(noGr.nearest, null); assert.equal(noGr.tableIn.length, 2);
  // bez poze: sve tačke su k = -1 (nepoznato) i idu u sloj „sirovo“; van stola nema
  const np = layerItems({ in: [], out: [], raw: [[100, 0, -1], [0, 200, -1]], groups: [] });
  assert.equal(np.radarIn.length, 2); assert.deepEqual(np.radarOut, []); assert.deepEqual(np.tableIn, []);
  assert.deepEqual(layerItems(null).groups, []);
});

test('playIndex: krug po vremenu snimka, u krug ili do kraja', () => {
  const scans = [{ t: 0 }, { t: 100 }, { t: 200 }];           // period 300 ms (kao lidarsrc.FileLidar)
  assert.deepEqual(playIndex(scans, 0), { i: 0, done: false });
  assert.deepEqual(playIndex(scans, 150), { i: 1, done: false });
  assert.deepEqual(playIndex(scans, 299), { i: 2, done: false });
  assert.deepEqual(playIndex(scans, 310, true), { i: 0, done: false });
  assert.deepEqual(playIndex(scans, 520, true), { i: 2, done: false });
  assert.deepEqual(playIndex(scans, 310, false), { i: 2, done: true });
  assert.deepEqual(playIndex([], 10), { i: -1, done: true });
  assert.deepEqual(playIndex(scans, -5), { i: 0, done: false });
});

test('fmtAge, fmtGroup', () => {
  assert.equal(fmtAge(null), '–'); assert.equal(fmtAge(85.4), '85 ms'); assert.equal(fmtAge(2340), '2.3 s');
  assert.equal(fmtGroup(null), 'nema'); assert.equal(fmtGroup({ dist: 420, angle: 29.6 }), '420 mm, 30°');
});

test('statsRows: Hz, tačke, starost, poza, najbliža grupa (laptop) i tačka (ESP); bez podatka nema lažne nule', () => {
  const scan = { pts: [0, 420, 1, 430, 20, 1700], pose: [1500, 1000, 0], near: [420, 0], hz: 9.94, wall: 1000 };
  const rows = Object.fromEntries(statsRows(scan, STAGES, 1250).map(r => [r[0], r]));
  assert.equal(rows.Hz[1], '9.9');
  assert.equal(rows['tačaka'][1], '3 · u stolu 2 · van 1');
  assert.equal(rows['starost kruga'][1], '250 ms'); assert.equal(rows['starost kruga'][2], '');
  assert.equal(rows.poza[1], '1500, 1000 · 0°');
  assert.equal(rows['najbliža grupa'][1], '420 mm, 3° · 3 t.'); assert.equal(rows['najbliža grupa'][2], 'hl');
  assert.equal(rows['najbliža tačka (ESP)'][1], '420 mm, 0°');
  const bare = Object.fromEntries(statsRows({ pts: [0, 500], hz: null, near: null, nopose: true, pose: [250, 1000, 0], wall: 0 },
    { ...STAGES, nearest: null }, 5000).map(r => [r[0], r]));
  assert.equal(bare.Hz[1], 'nema sa robota');
  assert.equal(bare.poza[1], 'nema poze'); assert.equal(bare.poza[2], 'warn');
  assert.equal(bare['tačaka'][1], '1');                       // bez poze nema „u stolu / van“
  assert.equal(bare['starost kruga'][2], 'warn');             // > 1.5 s
  assert.equal(bare['najbliža grupa'][1], 'nema');
  assert.equal(statsRows(null, null, 0).length, 0);
});

test('prefs: localStorage eurosim.lidar, pokvaren ili nedostupan -> podrazumevano', () => {
  const mem = { d: {}, getItem(k) { return this.d[k] ?? null; }, setItem(k, v) { this.d[k] = v; } };
  assert.deepEqual(loadPrefs(mem), DEFAULT_PREFS);
  savePrefs({ src: 'snimak', file: 'a.jsonl.gz', layers: { van: false }, range: 4000, loop: false }, mem);
  assert.deepEqual(loadPrefs(mem), { src: 'snimak', file: 'a.jsonl.gz', layers: { sirovo: true, van: false, grupe: true }, range: 4000, loop: false });
  mem.d[PREFS_KEY] = '{pokvaren';
  assert.deepEqual(loadPrefs(mem), DEFAULT_PREFS);
  mem.d[PREFS_KEY] = JSON.stringify({ src: 'x', range: 123 });
  assert.deepEqual(loadPrefs(mem), DEFAULT_PREFS);
  const bad = { getItem() { throw new Error('blokirano'); }, setItem() { throw new Error('blokirano'); } };
  assert.deepEqual(loadPrefs(bad), DEFAULT_PREFS);
  savePrefs(DEFAULT_PREFS, bad);                              // ne baca
  assert.deepEqual(loadPrefs(undefined), DEFAULT_PREFS);
});
