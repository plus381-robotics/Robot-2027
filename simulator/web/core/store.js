// Najmanji mogući store: stanje + pretplata. set(patch) spaja polja i obaveštava samo ako se nešto promenilo.
export function createStore(initial = {}) {
  let state = { ...initial };
  const subs = new Set();
  return {
    get: () => state,
    set(patch) {
      const changed = Object.keys(patch).some(k => !Object.is(state[k], patch[k]));
      if (!changed) return;
      const prev = state;
      state = { ...state, ...patch };
      for (const fn of [...subs]) fn(state, prev);
    },
    subscribe(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
  };
}
