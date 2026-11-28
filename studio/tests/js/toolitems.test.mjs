// Testovi za web/core/toolitems.js: zajedničke stavke reda komandi (Taktika, Strana) — gde koja ide po prostoru.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRegistry } from '../../web/core/panels.js';
import { createToolItems, sharedHomes, sharedMoves } from '../../web/core/toolitems.js';

// Registar kao posle Zadatka 4.6 (voznja-alati se dodaje u testu, da se vidi deljenje između prostora).
function registry() {
  const r = createRegistry();
  r.registerPanel({ id: 'poruka', workspaces: ['taktike', 'senzori', 'voznja', 'snimci'], region: 'tool', priority: 95 });
  r.registerPanel({ id: 'taktike-alati', workspaces: ['taktike'], region: 'tool', priority: 10, shared: ['taktika', 'strana'] });
  r.registerPanel({ id: 'snimci-alati', workspaces: ['snimci'], region: 'tool', priority: 10, shared: ['taktika', 'strana'] });
  r.registerPanel({ id: 'teren', workspaces: ['taktike', 'voznja', 'snimci'], region: 'main', priority: 20 });
  return r;
}

test('sharedHomes: u prostoru stavka ide u najvažniji panel koji je navodi', () => {
  const r = registry();
  assert.deepEqual(sharedHomes(r.panelsFor('taktike')), { taktika: 'taktike-alati', strana: 'taktike-alati' });
  assert.deepEqual(sharedHomes(r.panelsFor('voznja')), {});                     // još bez voznja-alati
  assert.deepEqual(sharedHomes(r.panelsFor('senzori')), {});
  r.registerPanel({ id: 'voznja-alati', workspaces: ['voznja'], region: 'tool', priority: 10, shared: ['strana', 'taktika'] });
  assert.deepEqual(sharedHomes(r.panelsFor('voznja')), { strana: 'voznja-alati', taktika: 'voznja-alati' });
  assert.deepEqual(sharedHomes(r.panelsFor('snimci')), { taktika: 'snimci-alati', strana: 'snimci-alati' });
});

test('sharedHomes: panel bez shared i prazna lista', () => {
  assert.deepEqual(sharedHomes([{ id: 'a' }, { id: 'b', shared: [] }]), {});
  assert.deepEqual(sharedHomes(undefined), {});
  assert.deepEqual(sharedHomes([{ id: 'a', shared: ['x'] }, { id: 'b', shared: ['x', 'y'] }]), { x: 'a', y: 'b' });
});

test('sharedMoves: seli samo ono što menja dom; bez doma u prostoru stavka ostaje gde je', () => {
  const r = registry();
  r.registerPanel({ id: 'voznja-alati', workspaces: ['voznja'], region: 'tool', priority: 10, shared: ['taktika', 'strana'] });
  let where = {};                                            // početak: stavke još nigde
  const first = sharedMoves(where, sharedHomes(r.panelsFor('taktike')));
  assert.deepEqual(first, [{ id: 'taktika', from: null, to: 'taktike-alati' }, { id: 'strana', from: null, to: 'taktike-alati' }]);
  for (const m of first) where[m.id] = m.to;
  assert.deepEqual(sharedMoves(where, sharedHomes(r.panelsFor('taktike'))), []);         // isti prostor: ništa
  const toV = sharedMoves(where, sharedHomes(r.panelsFor('voznja')));
  assert.deepEqual(toV.map(m => [m.id, m.from, m.to]), [['taktika', 'taktike-alati', 'voznja-alati'], ['strana', 'taktike-alati', 'voznja-alati']]);
  for (const m of toV) where[m.id] = m.to;
  assert.deepEqual(sharedMoves(where, sharedHomes(r.panelsFor('senzori'))), []);            // Senzori: ostaju u Vožnji
  const toS = sharedMoves(where, sharedHomes(r.panelsFor('snimci')));
  assert.deepEqual(toS.map(m => m.to), ['snimci-alati', 'snimci-alati']);
});

test('registerToolItem: provere', () => {
  const t = createToolItems();
  const it = t.registerToolItem({ id: 'taktika', mount: () => {} });
  assert.equal(it.title, 'taktika');
  assert.equal(t.get('taktika'), it);
  assert.equal(t.get('nema'), null);
  assert.deepEqual(t.all().map(x => x.id), ['taktika']);
  assert.throws(() => t.registerToolItem({ id: 'taktika', mount: () => {} }), /već postoji/);
  assert.throws(() => t.registerToolItem({ mount: () => {} }), /bez id/);
  assert.throws(() => t.registerToolItem({ id: 'x' }), /mount/);
});
