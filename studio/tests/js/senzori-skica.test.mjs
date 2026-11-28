// Testovi za web/senzori/skica.js: skica robota spreda / pozadi (strane na ekranu, IR po imenu, mere iz Profila,
// raspored jedne skice: telo, lidar na vrhu, točkovi, IR lampice).
import test from 'node:test';
import assert from 'node:assert/strict';
import { screenSide, irAt, sketchGeometry, irSensors, cornerOn, elevation, IR_NAMES } from '../../web/senzori/skica.js';

const PROFILE = { body: { width: 300, length: 165, height: 350 }, ir: { low_z: 40, high_z: 340 },
  drive: { wheel_track: 166, wheel_diameter: 65 }, odometry: { encoder_track: 286 } };

test('spreda je levo robota desno na ekranu, pozadi levo', () => {
  assert.equal(screenSide(true, 'spreda'), 1); assert.equal(screenSide(true, 'pozadi'), -1);
  assert.equal(screenSide(false, 'spreda'), -1);
  assert.equal(screenSide(false, 'pozadi'), 1);
});

test('irAt', () => assert.deepEqual(irAt('BRU'), { front: false, left: false, upper: true }));

test('irAt: svi uglovi i visine', () => {
  assert.deepEqual(irAt('FLD'), { front: true, left: true, upper: false });
  assert.deepEqual(irAt('FRU'), { front: true, left: false, upper: true });
  assert.deepEqual(irAt('BLD'), { front: false, left: true, upper: false });
});

test('geometrija iz Profila', () => {
  const g = sketchGeometry(PROFILE);
  assert.deepEqual([g.w, g.h, g.irLow, g.irHigh, g.odoTrack, g.driveTrack], [300, 350, 40, 340, 286, 166]);
  assert.equal(g.len, 165); assert.equal(g.wheelD, 65);
});

test('geometrija bez Profila: mere robota 2027', () => {
  const g = sketchGeometry(null);
  assert.deepEqual([g.w, g.len, g.h, g.irLow, g.irHigh, g.driveTrack, g.odoTrack, g.wheelD], [300, 165, 350, 40, 340, 166, 286, 65]);
  assert.equal(sketchGeometry({ body: { width: 280 } }).w, 280);
});

test('irSensors: bitovi redom imena iz Profila, bez Profila FLD FLU FRD FRU BLD BLU BRD BRU', () => {
  const s = irSensors(null);
  assert.deepEqual(s.map(x => x.name), IR_NAMES);
  assert.deepEqual(s.map(x => x.bit), [0, 1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(s[7], { name: 'BRU', bit: 7, front: false, left: false, upper: true });
  const p = irSensors({ ir_sensors: [{ name: 'BRU' }, { name: 'FLD' }] });
  assert.deepEqual(p.map(x => [x.name, x.bit, x.front]), [['BRU', 0, false], ['FLD', 1, true]]);
});

test('cornerOn: ugao svetli kad vidi D ili U; bez podataka null', () => {
  const s = irSensors(null);
  assert.equal(cornerOn(s, 0b10, true, true), true);          // FLU
  assert.equal(cornerOn(s, 0b10, true, false), false);
  assert.equal(cornerOn(s, 1 << 6, false, false), true);      // BRD
  assert.equal(cornerOn(s, null, true, true), null);
});

const box = { x: 0, y: 0, w: 290, h: 160 };

test('elevation spreda: levo robota (FL*) desno na ekranu, U iznad D, lidar na vrhu tela', () => {
  const L = elevation(sketchGeometry(PROFILE), irSensors(PROFILE), box, 'spreda');
  assert.deepEqual(L.lamps.map(l => l.name).sort(), ['FLD', 'FLU', 'FRD', 'FRU']);
  const at = n => L.lamps.find(l => l.name === n);
  assert.ok(at('FLD').x > L.cx && at('FRD').x < L.cx);
  assert.ok(at('FLU').y < at('FLD').y);                       // gornji je više na ekranu
  assert.ok(at('FLD').x > L.body[2]);                         // lampica je van tela, uz ivicu
  assert.ok(L.lidar.box[3] <= L.body[1] + 1e-9);              // lidar sedi na vrhu tela
  assert.ok(L.lidar.scanY < L.body[1]);                       // ravan skeniranja iznad tela
  assert.deepEqual(L.title, ['SPREDA', '(stojiš ispred robota)']);
  assert.deepEqual(L.sides, { left: 'desno r.', right: 'levo r.' });
  const odoL = L.odo.find(o => o.name === 'L'), odoD = L.odo.find(o => o.name === 'D');
  assert.ok(odoL.x > L.cx && odoD.x < L.cx);                  // pasivni točak levo robota je desno na ekranu
  assert.ok(Math.abs(Math.abs(odoL.x - L.cx) - 143 * L.k) < 1e-9);   // ±encoder_track/2
  for (const dw of L.drive) assert.ok(Math.abs(Math.abs(dw.x - L.cx) - 83 * L.k) < 1e-9);   // ±wheel_track/2
});

test('elevation pozadi: levo robota (BL*) levo na ekranu', () => {
  const L = elevation(sketchGeometry(PROFILE), irSensors(PROFILE), box, 'pozadi');
  assert.deepEqual(L.lamps.map(l => l.name).sort(), ['BLD', 'BLU', 'BRD', 'BRU']);
  const at = n => L.lamps.find(l => l.name === n);
  assert.ok(at('BLD').x < L.cx && at('BRU').x > L.cx);
  assert.ok(L.odo.find(o => o.name === 'L').x < L.cx);
  assert.deepEqual(L.title, ['POZADI', '(stojiš iza robota)']);
  assert.deepEqual(L.sides, { left: 'levo r.', right: 'desno r.' });
});

test('elevation: telo staje u okvir i na D i U visinama iz Profila', () => {
  const g = sketchGeometry(PROFILE), L = elevation(g, irSensors(PROFILE), box, 'spreda');
  assert.ok(L.lidar.labelY > box.y && L.gy < box.y + box.h);
  assert.ok(Math.abs(L.lamps.find(l => l.name === 'FLD').y - (L.gy - 40 * L.k)) < 1e-9);
  assert.ok(Math.abs(L.lamps.find(l => l.name === 'FLU').y - (L.gy - 340 * L.k)) < 1e-9);
  assert.ok(Math.abs((L.body[2] - L.body[0]) - 300 * L.k) < 1e-9);
});
