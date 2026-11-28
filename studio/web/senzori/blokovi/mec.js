// Blok „Meč i taktika“ (donji red): stanje meča (spreman / naoružan / meč sa vremenom / kraj), taktika, strana, vreme meča.
// Stanje: kolona `mec` i `match` (ms od starta meča) iz snimka; na ROBOTU bez frame-ova (Nucleo ne javlja) iz telemetrije
// ESP-a (store.robotMec, store.running), pa blok radi i tada. Zato je polje bloka pseudo-polje '@mec' (makeHas u
// blokovi/index.js: store.robotMec ili kolona `mec` snimka). Taktika: kolona `tac`, pa store.running (robot), pa taktika
// iz trake (store.snap.tactic), pa run.meta.tactic. Strana (Žuta / Plava) iz run.meta.side.
import { matchView, MATCH_MS } from '../../shell/strip.js';
import { esc } from '../../core/api.js';
import { none, at, DASH } from './osnova.js';

export const STRANA = { zuta: 'Žuta', plava: 'Plava' };
const ARMED = ['RESET', 'NAORUZAN', 'POZA'];

const sec = ms => (ms / 1000).toFixed(1).replace('.', ',') + ' s';

// {state, ms, label, cls, time, tactic, side}
export function matchInfo(d) {
  const st = d.st || {}, robot = !!(st.session && st.session.kind === 'robot');
  const run = d.run, meta = (run && run.meta) || {};
  let state = at(d, 'mec');
  if (state == null && robot && st.robotMec != null) state = st.robotMec;
  const ms = at(d, 'match');
  let label, cls;
  if (state === 'KRAJ' || (ms != null && ms >= MATCH_MS)) { label = 'KRAJ'; cls = 'end'; }
  else if (ms != null || state === 'MEC') { label = ms != null ? matchView({ state, ms }).text : 'MEČ'; cls = 'run'; }
  else if (ARMED.includes(state)) { label = 'NAORUŽAN'; cls = 'armed'; }
  else { label = 'SPREMAN'; cls = 'idle'; }
  const tactic = at(d, 'tac') || (robot ? st.running : null) || (st.snap && st.snap.tactic) || meta.tactic || null;
  return { state, ms, label, cls, time: ms != null ? sec(ms) : DASH, tactic: tactic ? String(tactic) : null,
    side: STRANA[meta.side] || null };
}

const COLOR = { idle: 'var(--ok)', armed: 'var(--warn)', run: 'var(--accent)', end: 'var(--dim)' };

export default {
  id: 'mec', name: 'Meč i taktika', slot: 'bottom', part: null, fields: ['@mec'],
  hints: ['Pre meča: prava taktika, prava strana, stanje „spreman“.'],
  view(d) {
    if (!d.src) return none();
    const m = matchInfo(d);
    return { status: 'ok', text: m.label.toLowerCase(),
      vals: [['stanje', m.label], ['taktika', m.tactic || DASH], ['strana', m.side || DASH], ['vreme', m.time]] };
  },
  html(d, big) {
    const m = matchInfo(d);
    return `<div style="padding:${big ? 24 : 6}px 12px;display:flex;flex-direction:column;gap:${big ? 12 : 4}px">
      <div style="font-size:${big ? 40 : 24}px;font-weight:800;color:${COLOR[m.cls]}">${esc(m.label)}</div>
      <div class="dim">taktika <b style="color:var(--text)">${esc(m.tactic || DASH)}</b> · strana
        <b style="color:${m.side === 'Plava' ? 'var(--blue)' : 'var(--yellow)'}">${esc(m.side || DASH)}</b> · meč ${esc(m.time)}</div>
      ${big ? '<div class="dim">Naoružaj i činč su u Vožnji; ovde se samo gleda.</div>' : ''}</div>`;
  },
};
