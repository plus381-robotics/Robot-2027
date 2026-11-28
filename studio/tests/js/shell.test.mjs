// Testovi za web/shell/layout.js: Esc = STOP (hvatanje na window-u, ne smeta editoru).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { installEscStop } from '../../web/shell/layout.js';
import { RAIL_LOGO } from '../../web/shell/rail.js';
import { migratedNotice } from '../../web/core/migrated.js';

const key = (k, extra = {}) => {
  const e = new Event('keydown', { bubbles: true, cancelable: true });
  Object.assign(e, { key: k, repeat: false, ...extra });
  return e;
};

test('Esc šalje STOP samo dok sesija radi; ponavljanje i drugi tasteri ne', () => {
  const win = new EventTarget();
  let running = false, stops = 0;
  const off = installEscStop(win, () => running, () => stops++);
  win.dispatchEvent(key('Escape'));
  assert.equal(stops, 0);                         // nema sesije
  running = true;
  win.dispatchEvent(key('Escape'));
  assert.equal(stops, 1);
  win.dispatchEvent(key('Escape', { repeat: true }));
  win.dispatchEvent(key('a'));
  win.dispatchEvent(key('Enter'));
  assert.equal(stops, 1);
  off();
  win.dispatchEvent(key('Escape'));
  assert.equal(stops, 1);                         // odjavljen
});

test('Esc: slušalac ne blokira događaj (editor i dalje zatvara popup dopune)', () => {
  const win = new EventTarget();
  let stops = 0, editorSaw = 0;
  installEscStop(win, () => true, () => stops++);
  win.addEventListener('keydown', e => { if (e.key === 'Escape') editorSaw++; });   // npr. keymap CodeMirror-a
  const e = key('Escape');
  win.dispatchEvent(e);
  assert.equal(stops, 1);
  assert.equal(editorSaw, 1);
  assert.equal(e.defaultPrevented, false);
});

// ---------------- ime Gambit Studio ----------------

test('logo trake: Gambit / Studio', () => {
  assert.deepEqual(RAIL_LOGO, { title: 'Gambit', sub: 'Studio' });
});

test('index.html: naslov taba je Gambit Studio', () => {
  const html = readFileSync(new URL('../../web/index.html', import.meta.url), 'utf8');
  assert.ok(html.includes('<title>Gambit Studio</title>'));
});

test('poruka o prenetim fajlovima: samo kad ima šta da se kaže', () => {
  assert.equal(migratedNotice(undefined), null);
  assert.equal(migratedNotice({ moved: [], skipped: [] }), null);
  assert.equal(migratedNotice({ moved: ['a'], skipped: [] }), 'Premešteno iz starog foldera simulator/: 1 fajl');
  assert.equal(migratedNotice({ moved: ['a', 'b'], skipped: [] }), 'Premešteno iz starog foldera simulator/: 2 fajla');
  assert.equal(migratedNotice({ moved: ['a', 'b', 'c', 'd', 'e'], skipped: ['b'] }),
    'Premešteno iz starog foldera simulator/: 5 fajlova; 1 nije premešteno (ostalo u simulator/): b');
  assert.equal(migratedNotice({ moved: [], skipped: ['a', 'b'] }),
    'Iz starog foldera simulator/ ništa nije premešteno; 2 nisu premeštena (ostala u simulator/): a, b');
});
