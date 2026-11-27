// Klijent sesije: jedna WebSocket veza /ws/session?engine=sim|robot|replay&..  (server: eurosim/server.py).
// Poruke servera: hello, data, state, reply, end, error (+ "close" kad se veza zatvori); komande su JSON liste.
//   const s = connect({engine: 'sim', tactic: 'primer', ...});  s.on('data', m => ...);  s.command(['pause']);  s.close();
// `capabilities` (Set) i `source` stižu u poruci hello.
export function connect({ engine, ...params }, env = {}) {
  const WS = env.WebSocket || globalThis.WebSocket;
  const loc = env.location || globalThis.location;
  const q = new URLSearchParams({ engine });
  for (const [k, v] of Object.entries(params)) {
    if (v == null) continue;
    q.set(k, typeof v === 'object' ? JSON.stringify(v) : String(v));
  }
  const ws = new WS(`${loc.protocol === 'https:' ? 'wss' : 'ws'}://${loc.host}/ws/session?${q}`);
  const listeners = {};
  const queue = [];
  const session = {
    capabilities: new Set(),
    source: null,
    command(c) {
      const s = JSON.stringify(c);
      if (ws.readyState === 1) ws.send(s);
      else if (ws.readyState === 0) queue.push(s);        // još se povezuje: šalje se čim se otvori
    },
    on(type, fn) {
      (listeners[type] = listeners[type] || new Set()).add(fn);
      return () => listeners[type].delete(fn);
    },
    close() { ws.close(); },
  };
  const emit = (type, m) => { for (const fn of [...(listeners[type] || [])]) fn(m); };
  ws.onopen = () => { for (const s of queue.splice(0)) ws.send(s); };
  ws.onmessage = ev => {
    let m;
    try { m = JSON.parse(ev.data); } catch { return; }
    if (!m || typeof m.type !== 'string') return;
    if (m.type === 'hello') {
      session.source = m.source || null;
      session.capabilities.clear();
      for (const c of m.capabilities || []) session.capabilities.add(c);
    }
    emit(m.type, m);
  };
  ws.onclose = () => emit('close', {});
  return session;
}
