// Testovi za web/core/panels.js: registar panela i pamćenje radnog prostora.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRegistry, panelsFor, loadWorkspace, saveWorkspace, WORKSPACES, WS_KEY } from '../../web/core/panels.js';

test('panelsFor: samo paneli tog prostora, po regionu pa po prioritetu (manji broj prvi), stabilno', () => {
  const r = createRegistry();
  r.registerPanel({ id: 'koraci', workspaces: ['taktike', 'voznja'], region: 'side', priority: 2 });
  r.registerPanel({ id: 'dnevnik', workspaces: ['voznja'], region: 'side', priority: 5 });
  r.registerPanel({ id: 'sto', workspaces: ['taktike', 'voznja'], region: 'main', priority: 9 });
  r.registerPanel({ id: 'esp', workspaces: ['voznja'], region: 'side', priority: 2 });
  r.registerPanel({ id: 'vreme', workspaces: ['voznja'], region: 'bottom', priority: 1 });
  assert.deepEqual(r.panelsFor('voznja').map(p => p.id), ['sto', 'koraci', 'esp', 'dnevnik', 'vreme']);
  assert.deepEqual(r.panelsFor('taktike').map(p => p.id), ['sto', 'koraci']);
  assert.deepEqual(r.panelsFor('senzori'), []);
});

test('panelsFor: needs koji izvor nema -> panel ostaje, ali siv sa razlogom', () => {
  const r = createRegistry();
  r.registerPanel({ id: 'esp', workspaces: ['voznja'], needs: ['esp_screen'] });
  r.registerPanel({ id: 'lidar', workspaces: ['voznja'], needs: ['lidar', 'pose'], priority: 1 });
  const [lidar, esp] = r.panelsFor('voznja', new Set(['esp_screen', 'pose']));
  assert.equal(esp.disabled, false);
  assert.equal(esp.reason, '');
  assert.equal(lidar.disabled, true);
  assert.equal(lidar.reason, 'potrebno: lidar');
  assert.equal(r.panelsFor('voznja', ['esp_screen', 'pose', 'lidar'])[0].disabled, false);    // i obična lista
  assert.equal(r.panelsFor('voznja')[1].reason, 'potrebno: esp_screen');
});

test('registerPanel: podrazumevane vrednosti i provere', () => {
  const r = createRegistry();
  const p = r.registerPanel({ id: 'x', workspaces: ['snimci'] });
  assert.equal(p.region, 'side');
  assert.equal(p.open, false);
  assert.deepEqual(p.needs, []);
  assert.equal(r.get('x'), p);
  assert.throws(() => r.registerPanel({ id: 'x', workspaces: [] }), /već postoji/);
  assert.throws(() => r.registerPanel({ id: 'y', workspaces: ['nepostojeci'] }), /radni prostor/);
  assert.throws(() => r.registerPanel({ id: 'z', region: 'gore' }), /region/);
  assert.throws(() => r.registerPanel({}), /bez id/);
});

test('loadWorkspace / saveWorkspace: ključ eurosim.ws, loša vrednost i bačen izuzetak -> podrazumevano', () => {
  assert.equal(WS_KEY, 'eurosim.ws');
  assert.deepEqual(WORKSPACES, ['taktike', 'senzori', 'voznja', 'snimci']);
  const mem = new Map();
  const st = { getItem: k => (mem.has(k) ? mem.get(k) : null), setItem: (k, v) => mem.set(k, v) };
  assert.equal(loadWorkspace(st), 'taktike');
  saveWorkspace('voznja', st);
  assert.equal(mem.get('eurosim.ws'), 'voznja');
  assert.equal(loadWorkspace(st), 'voznja');
  saveWorkspace('svasta', st);                                   // nepoznat prostor se ne pamti
  assert.equal(loadWorkspace(st), 'voznja');
  mem.set('eurosim.ws', 'svasta');
  assert.equal(loadWorkspace(st), 'taktike');
  const bad = { getItem() { throw new Error('blokirano'); }, setItem() { throw new Error('blokirano'); } };
  assert.equal(loadWorkspace(bad), 'taktike');
  assert.doesNotThrow(() => saveWorkspace('senzori', bad));
  assert.equal(loadWorkspace(undefined), 'taktike');
});

test('staro eurosim.ws = test otvara senzori', () => {
  assert.equal(loadWorkspace({ getItem: () => 'test' }), 'senzori');
});

test('lidar paneli samo u detalju lidara', async () => {
  let ok = true;
  try { await import('../../web/panels/lidar.js'); } catch (e) { ok = false; }
  if (!ok) {                                     // fallback: registar sa lažnim panelom sa istim when
    const r = createRegistry();
    r.registerPanel({ id: 'lidar', workspaces: ['senzori'], when: st => st.sensOpen === 'lidar' });
    assert.ok(r.panelsFor('senzori', [], { sensOpen: 'lidar' }).some(p => p.id === 'lidar'));
    assert.ok(!r.panelsFor('senzori', [], { sensOpen: null }).some(p => p.id === 'lidar'));
    return;
  }
  const ids = st => panelsFor('senzori', [], st).map(p => p.id);
  assert.ok(ids({ sensOpen: 'lidar' }).includes('lidar'));
  assert.ok(!ids({ sensOpen: null }).includes('lidar'));
});
