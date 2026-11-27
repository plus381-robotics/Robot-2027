// Testovi za web/shell/layout.js: Esc = STOP (hvatanje na window-u, ne smeta editoru).
import test from 'node:test';
import assert from 'node:assert/strict';
import { installEscStop } from '../../web/shell/layout.js';

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
