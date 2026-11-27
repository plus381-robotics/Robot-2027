// Testovi za web/core/voznja.js: red komandi Vožnja po stanju sesije i njenim mogućnostima (hello), kartice ESP i
// Postavka stola. Mogućnosti su iste kao u eurosim/session.py (SimSource, RobotSource).
import test from 'node:test';
import assert from 'node:assert/strict';
import { voznjaTools, espShown, stoShown, hasCap, TOOL_IDS } from '../../web/core/voznja.js';
import { createRegistry } from '../../web/core/panels.js';

const SIM_CAPS = ['arm', 'cord', 'esp_buttons', 'esp_screen', 'lidar', 'opponents', 'pause', 'speed', 'stop', 'test'];
const SIM_REAL_LIDAR = SIM_CAPS.filter(c => c !== 'pause' && c !== 'speed');      // pravi lidar: ×1, bez pauze
const ROBOT_CAPS = ['lidar', 'push', 'run', 'stop'];
const SESSION_KEYS = ['arm', 'cord', 'test', 'speed', 'pause', 'push', 'run'];

const shown = v => Object.keys(TOOL_IDS).filter(k => v[k]);

test('bez sesije: Izvori ▾ i Pokreni sesiju (SIM i ROBOT); nijedna komanda sesije', () => {
  const sim = voznjaTools({ drive: 'sim', session: null, caps: null });
  assert.deepEqual(shown(sim), ['izvori', 'start']);
  assert.equal(sim.kind, 'sim');
  const rob = voznjaTools({ drive: 'robot', session: null, caps: null });
  assert.deepEqual(shown(rob), ['izvori', 'start']);
  assert.equal(rob.kind, 'robot');
  assert.deepEqual(shown(voznjaTools({})), ['izvori', 'start']);                   // podrazumevano SIM
});

test('SIM sesija: komande po mogućnostima; pre poruke hello samo Prati i Završi', () => {
  const s = { kind: 'sim' };
  assert.deepEqual(shown(voznjaTools({ drive: 'sim', session: s, caps: null })), ['follow', 'end']);
  const v = voznjaTools({ drive: 'sim', session: s, caps: SIM_CAPS });
  assert.deepEqual(shown(v), ['arm', 'cord', 'test', 'speed', 'pause', 'follow', 'end']);
  assert.equal(v.endLabel, 'Završi');
  const real = voznjaTools({ drive: 'sim', session: s, caps: new Set(SIM_REAL_LIDAR) });     // i Set
  assert.deepEqual(shown(real), ['arm', 'cord', 'test', 'follow', 'end']);
});

test('ROBOT sesija: Pošalji, Pošalji i pokreni, Prati, Prekini vezu; vrsta sesije pobeđuje izbor', () => {
  const v = voznjaTools({ drive: 'robot', session: { kind: 'robot' }, caps: ROBOT_CAPS });
  assert.deepEqual(shown(v), ['push', 'run', 'follow', 'end']);
  assert.equal(v.endLabel, 'Prekini vezu');
  const odd = voznjaTools({ drive: 'sim', session: { kind: 'robot' }, caps: ROBOT_CAPS });
  assert.equal(odd.kind, 'robot');
  assert.equal(odd.izvori, false);                                        // u sesiji: Izvori samo iz bočne trake
  for (const k of SESSION_KEYS) {                                        // mogućnost koje nema -> nema ni dugmeta
    const caps = ROBOT_CAPS.concat(SIM_CAPS).filter(c => c !== k);
    assert.equal(voznjaTools({ session: { kind: 'robot' }, caps })[k], false, k);
  }
});

test('napomena „tekst iz editora (nesačuvan)“', () => {
  assert.equal(voznjaTools({ drive: 'sim', edUnsaved: false }).note, false);
  assert.equal(voznjaTools({ drive: 'sim', edUnsaved: true }).note, true);           // Live bi uzeo tekst editora
  assert.equal(voznjaTools({ drive: 'robot', edUnsaved: true }).note, true);         // Pošalji posle povezivanja
  const sim = { kind: 'sim', edText: true };
  assert.equal(voznjaTools({ session: sim, caps: SIM_CAPS, edUnsaved: false }).note, true);   // Live pokrenut sa tim tekstom
  assert.equal(voznjaTools({ session: { kind: 'sim' }, caps: SIM_CAPS, edUnsaved: true }).note, false);
  assert.equal(voznjaTools({ session: { kind: 'robot' }, caps: ROBOT_CAPS, edUnsaved: true }).note, true);
  assert.equal(voznjaTools({ session: { kind: 'robot' }, caps: null, edUnsaved: true }).note, false);   // još nema Pošalji
});

test('espShown: sesija sa esp_screen (pre hello po vrsti); bez sesije samo uz SIM', () => {
  assert.equal(espShown({ drive: 'sim', session: null }), true);
  assert.equal(espShown({ drive: 'robot', session: null }), false);
  assert.equal(espShown({ drive: 'sim', session: { kind: 'sim' }, caps: SIM_CAPS }), true);
  assert.equal(espShown({ drive: 'sim', session: { kind: 'sim' }, caps: null }), true);      // pre hello: po vrsti sesije
  assert.equal(espShown({ drive: 'robot', session: { kind: 'robot' }, caps: null }), false);
  assert.equal(espShown({ drive: 'sim', session: { kind: 'sim' }, caps: ['arm', 'stop'] }), false);   // sesija bez ekrana
  assert.equal(espShown({ drive: 'robot', session: { kind: 'robot' }, caps: ROBOT_CAPS }), false);
});

test('stoShown: Taktike uvek, Vožnja samo SIM', () => {
  assert.equal(stoShown({ drive: 'robot' }, 'taktike'), true);
  assert.equal(stoShown({ drive: 'sim' }, 'voznja'), true);
  assert.equal(stoShown({ drive: 'robot' }, 'voznja'), false);
  assert.equal(stoShown({ drive: 'sim', session: { kind: 'robot' } }, 'voznja'), false);
  assert.equal(stoShown({ drive: 'robot', session: { kind: 'sim' } }, 'voznja'), true);
  assert.equal(stoShown({ ws: 'voznja', drive: 'robot' }), false);
});

test('hasCap: Set, lista, null', () => {
  assert.equal(hasCap(new Set(['a']), 'a'), true);
  assert.equal(hasCap(['a'], 'a'), true);
  assert.equal(hasCap(null, 'a'), false);
  assert.equal(hasCap(['b'], 'a'), false);
});

test('panelsFor: when(state, ws) sakriva panel (ESP uz robota, Postavka stola u Vožnji ROBOT)', () => {
  const r = createRegistry();
  r.registerPanel({ id: 'esp', workspaces: ['voznja'], priority: 5, when: espShown });
  r.registerPanel({ id: 'sto', workspaces: ['taktike', 'voznja'], priority: 25, when: stoShown });
  r.registerPanel({ id: 'koraci', workspaces: ['taktike', 'voznja'], priority: 20 });
  assert.deepEqual(r.panelsFor('voznja', [], { drive: 'sim' }).map(p => p.id), ['esp', 'koraci', 'sto']);
  assert.deepEqual(r.panelsFor('voznja', [], { drive: 'robot' }).map(p => p.id), ['koraci']);
  assert.deepEqual(r.panelsFor('taktike', [], { drive: 'robot' }).map(p => p.id), ['koraci', 'sto']);
  const st = { drive: 'robot', session: { kind: 'robot' }, caps: ROBOT_CAPS };
  assert.deepEqual(r.panelsFor('voznja', ROBOT_CAPS, st).map(p => p.id), ['koraci']);
  assert.deepEqual(r.panelsFor('voznja').map(p => p.id), ['esp', 'koraci', 'sto']);   // bez stanja: SIM
});
