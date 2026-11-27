// Testovi za web/core/keys.js (prečice) i shell/layout.js installKeys (Alt+1..4 prostori, „?“ spisak prečica).
import test from 'node:test';
import assert from 'node:assert/strict';
import { wsForKey, isHelpKey, isTyping, SHORTCUTS } from '../../web/core/keys.js';
import { installKeys } from '../../web/shell/layout.js';
import { RAIL_ITEMS } from '../../web/shell/rail.js';

const k = (key, extra = {}) => ({ key, code: '', altKey: false, ctrlKey: false, metaKey: false, shiftKey: false, repeat: false, ...extra });

test('wsForKey: Alt+1..4 = prostori redom kao u bočnoj traci', () => {
  assert.deepEqual([1, 2, 3, 4].map(n => wsForKey(k(String(n), { altKey: true, code: 'Digit' + n }))), RAIL_ITEMS.map(w => w.id));
  assert.deepEqual([1, 2, 3, 4].map(n => wsForKey(k(String(n), { altKey: true }))), ['taktike', 'test', 'voznja', 'snimci']);
  assert.equal(wsForKey(k('¡', { altKey: true, code: 'Digit1' })), 'taktike');      // raspored gde Alt menja znak: važi code
  assert.equal(wsForKey(k('1')), null);                                             // bez Alt-a: kuca se
  assert.equal(wsForKey(k('5', { altKey: true, code: 'Digit5' })), null);
  assert.equal(wsForKey(k('0', { altKey: true, code: 'Digit0' })), null);
  assert.equal(wsForKey(k('1', { altKey: true, ctrlKey: true, code: 'Digit1' })), null);   // AltGr na Windows-u = Ctrl+Alt
  assert.equal(wsForKey(k('1', { altKey: true, shiftKey: true, code: 'Digit1' })), null);
  assert.equal(wsForKey(k('1', { altKey: true, metaKey: true, code: 'Digit1' })), null);
  assert.equal(wsForKey(k('1', { altKey: true, repeat: true, code: 'Digit1' })), null);
  assert.equal(wsForKey(null), null);
});

test('isHelpKey / isTyping: „?“ otvara spisak, ali ne dok se kuca', () => {
  assert.equal(isHelpKey(k('?', { shiftKey: true })), true);
  assert.equal(isHelpKey(k('?', { ctrlKey: true })), false);
  assert.equal(isHelpKey(k('/')), false);
  const el = (tagName, extra = {}) => ({ tagName, closest: () => null, ...extra });
  assert.equal(isTyping(el('INPUT', { type: 'text' })), true);
  assert.equal(isTyping(el('INPUT', { type: 'number' })), true);
  assert.equal(isTyping(el('INPUT', { type: 'checkbox' })), false);
  assert.equal(isTyping(el('INPUT', { type: 'range' })), false);
  assert.equal(isTyping(el('TEXTAREA')), true);
  assert.equal(isTyping(el('SELECT')), true);
  assert.equal(isTyping(el('BUTTON')), false);
  assert.equal(isTyping(el('DIV', { isContentEditable: true })), true);
  assert.equal(isTyping(el('DIV', { closest: s => (s === '.cm-editor' ? {} : null) })), true);   // CodeMirror
  assert.equal(isTyping(null), false);
});

test('SHORTCUTS: spisak ima sve prečice iz spec-a', () => {
  const keys = SHORTCUTS.map(([key]) => key).join(' | ');
  for (const want of ['Esc', 'Ctrl+Enter', 'Ctrl+S', 'Razmak', '← / →', 'Shift+← / →', 'Alt+1 … 4', 'dupli klik', 'Alt+klik', '?'])
    assert.ok(keys.includes(want), want + ' u: ' + keys);
  for (const [key, what] of SHORTCUTS) assert.ok(key && what, key);
});

const ev = (key, extra = {}) => {
  const e = new Event('keydown', { bubbles: true, cancelable: true });
  Object.assign(e, k(key, extra));
  return e;
};

test('installKeys: Alt+1..4 menja prostor (preventDefault), „?“ spisak samo van polja', () => {
  const win = new EventTarget();
  const went = [];
  let helps = 0;
  const off = installKeys(win, { go: ws => went.push(ws), help: () => helps++ });
  const e3 = ev('3', { altKey: true, code: 'Digit3' });
  win.dispatchEvent(e3);
  assert.deepEqual(went, ['voznja']);
  assert.equal(e3.defaultPrevented, true);
  win.dispatchEvent(ev('3', { code: 'Digit3' }));                       // bez Alt-a: ništa
  assert.deepEqual(went, ['voznja']);
  win.dispatchEvent(ev('?', { shiftKey: true }));
  assert.equal(helps, 1);
  const inField = ev('?', { shiftKey: true });                           // dok se kuca u polje: „?“ je znak
  Object.defineProperty(inField, 'target', { value: { tagName: 'INPUT', type: 'text', closest: () => null } });
  win.dispatchEvent(inField);
  assert.equal(helps, 1);
  off();
  win.dispatchEvent(ev('1', { altKey: true, code: 'Digit1' }));
  assert.deepEqual(went, ['voznja']);                                    // odjavljen
});
