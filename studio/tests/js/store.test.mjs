import test from 'node:test';
import assert from 'node:assert/strict';
import { createStore } from '../../web/core/store.js';

test('store: get, set (spaja polja) i subscribe/unsubscribe', () => {
  const s = createStore({ a: 1, b: 2 });
  const seen = [];
  const off = s.subscribe((st, prev) => seen.push([st.a, prev.a]));
  s.set({ a: 5 });
  assert.deepEqual(s.get(), { a: 5, b: 2 });
  assert.deepEqual(seen, [[5, 1]]);
  s.set({ a: 5 });                                  // bez promene: bez obaveštenja
  assert.equal(seen.length, 1);
  off();
  s.set({ a: 9 });
  assert.equal(seen.length, 1);
});
