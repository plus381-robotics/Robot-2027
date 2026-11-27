import test from 'node:test';
import assert from 'node:assert/strict';
import { connect } from '../../web/core/session.js';

class FakeWS {
  constructor(url) { this.url = url; this.sent = []; this.readyState = 0; FakeWS.last = this; }
  open() { this.readyState = 1; this.onopen && this.onopen(); }
  recv(o) { this.onmessage({ data: JSON.stringify(o) }); }
  send(s) { this.sent.push(s); }
  close() { this.readyState = 3; this.onclose && this.onclose(); }
}
const loc = { protocol: 'http:', host: 'localhost:8270' };

test('connect: adresa /ws/session sa parametrima', () => {
  connect({ engine: 'sim', tactic: 'primer', obstacles: [[1, 2]], side: 'zuta' }, { WebSocket: FakeWS, location: loc });
  const u = new URL(FakeWS.last.url);
  assert.equal(u.protocol, 'ws:');
  assert.equal(u.pathname, '/ws/session');
  assert.equal(u.searchParams.get('engine'), 'sim');
  assert.equal(u.searchParams.get('tactic'), 'primer');
  assert.equal(u.searchParams.get('obstacles'), '[[1,2]]');
  connect({ engine: 'robot' }, { WebSocket: FakeWS, location: { protocol: 'https:', host: 'x' } });
  assert.equal(new URL(FakeWS.last.url).protocol, 'wss:');
});

test('poruke se šalju slušaocima po tipu; hello puni capabilities i source', () => {
  const s = connect({ engine: 'sim' }, { WebSocket: FakeWS, location: loc });
  const ws = FakeWS.last, got = [];
  for (const t of ['hello', 'data', 'state', 'reply', 'end', 'error']) s.on(t, m => got.push([t, m]));
  assert.equal(s.capabilities.size, 0);
  ws.open();
  ws.recv({ type: 'hello', source: { engine: 'sim', parts: { lidar: 'sim' } }, capabilities: ['pause', 'ir_mask'] });
  assert.ok(s.capabilities.has('pause') && s.capabilities.has('ir_mask'));
  assert.deepEqual(s.source, { engine: 'sim', parts: { lidar: 'sim' } });
  ws.recv({ type: 'data', frames: [], events: [] });
  ws.recv({ type: 'state', link: 'ok', age: 3 });
  ws.recv({ type: 'reply', cmd: 'STAT', ok: true, lines: [] });
  ws.recv({ type: 'error', error: 'x' });
  ws.recv({ type: 'end', run: null });
  assert.deepEqual(got.map(g => g[0]), ['hello', 'data', 'state', 'reply', 'error', 'end']);
});

test('command čeka otvaranje veze, pa šalje JSON listu; on vraća odjavu; close zatvara', () => {
  const s = connect({ engine: 'sim' }, { WebSocket: FakeWS, location: loc });
  const ws = FakeWS.last, n = [];
  s.command(['pause']);
  assert.equal(ws.sent.length, 0);
  ws.open();
  assert.deepEqual(ws.sent, ['["pause"]']);
  s.command(['speed', 2]);
  assert.equal(ws.sent[1], '["speed",2]');
  const off = s.on('state', m => n.push(m));
  off();
  ws.recv({ type: 'state', link: 'lost' });
  assert.equal(n.length, 0);
  const closed = []; s.on('close', () => closed.push(1));
  s.close();
  assert.equal(ws.readyState, 3);
  assert.equal(closed.length, 1);
});

test('neispravna poruka se ignoriše', () => {
  const s = connect({ engine: 'sim' }, { WebSocket: FakeWS, location: loc });
  FakeWS.last.open();
  FakeWS.last.onmessage({ data: 'nije json' });
  assert.equal(s.capabilities.size, 0);
});

test('command vraća false kad je veza zatvorena (STOP ne sme da propadne nečujno)', () => {
  const s = connect({ engine: 'robot' }, { WebSocket: FakeWS, location: loc });
  const ws = FakeWS.last;
  assert.equal(s.command(['stop']), true);          // čeka otvaranje: u redu
  assert.equal(s.open, true);
  ws.open();
  assert.equal(s.command(['stop']), true);
  assert.deepEqual(ws.sent, ['["stop"]', '["stop"]']);
  ws.readyState = 2;                                 // zatvara se
  assert.equal(s.command(['stop']), false);
  ws.readyState = 3;
  assert.equal(s.command(['stop']), false);
  assert.equal(s.open, false);
  assert.equal(ws.sent.length, 2);
});

test('onerror ide slušaocima "error"; close nosi code/reason i neposlate komande iz reda', () => {
  const s = connect({ engine: 'robot' }, { WebSocket: FakeWS, location: loc });
  const ws = FakeWS.last, errs = [], closes = [];
  s.on('error', m => errs.push(m));
  s.on('close', m => closes.push(m));
  s.command(['stop']);                               // veza se nije ni otvorila
  ws.onerror({});
  assert.deepEqual(errs, [{ type: 'error', error: 'greška veze sa serverom', transport: true }]);
  ws.readyState = 3;
  ws.onclose({ code: 1006, reason: '', wasClean: false });
  assert.deepEqual(closes, [{ code: 1006, reason: '', wasClean: false, unsent: [['stop']] }]);
});
