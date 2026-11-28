// Blok „Veza i zdravlje“ (donji red): redovi ESP ↔ laptop (kao na traci, shell/strip.js linkView), telemetrija (frame-ova u
// poslednjoj sekundi, „—“ bez frame-ova), Nucleo ↔ ESP (ROBOT: frame-ovi stižu = „javlja“, inače „ne javlja“; SIM:
// „simulirano“; snimak: „iz snimka“) i RSSI / RAM / krug petlje ESP-a („—“: ESP ih još ne šalje). Ne zavisi od polja
// (fields []), pa ima izvor čim radi sesija; ne koristi Nucleo frame-ove za „ESP ↔ laptop“ (iz store: telemetry, linkAge).
import { linkView } from '../../shell/strip.js';
import { esc } from '../../core/api.js';
import { none, DASH } from './osnova.js';

export const NOT_SENT = 'ESP ih još ne šalje';

// Frame-ova u poslednjoj sekundi do d.t (Hz); null kad nema barem dva frame-a u tom prozoru.
export function telemetryHz(d) {
  const run = d.run, ts = run && run.cols && run.cols.t;
  if (!ts || !ts.length) return null;
  const t = d.t == null ? run.duration : d.t;
  let n = 0;
  for (let i = run.frameAt(t); i >= 0 && ts[i] > t - 1000; i--) if (ts[i] <= t) n++;
  return n >= 2 ? n : null;
}

// [[naziv, klasa 'ok'|'warn'|'bad'|'idle', tekst], ...]
export function rows(d) {
  const st = d.st || {}, L = linkView(st), ses = st.session, robot = !!(ses && ses.kind === 'robot');
  const frames = !!(d.run && d.run.cols && d.run.cols.t && d.run.cols.t.length);
  const hz = telemetryHz(d);
  let nucleo;
  if (d.src === 'snimak') nucleo = ['idle', 'iz snimka'];
  else if (robot) nucleo = frames ? ['ok', 'javlja'] : ['warn', 'ne javlja'];
  else nucleo = ['idle', 'simulirano'];
  return [['ESP ↔ laptop', L.cls, L.text], ['telemetrija', hz == null ? 'idle' : 'ok', hz == null ? DASH : hz + ' Hz'],
    ['Nucleo ↔ ESP', ...nucleo], ['WiFi RSSI', 'idle', DASH], ['RAM ESP-a', 'idle', DASH], ['krug petlje ESP-a', 'idle', DASH]];
}

const DOT = { ok: 'var(--ok)', warn: 'var(--warn)', bad: 'var(--fail)', idle: 'var(--dim)' };

export default {
  id: 'veza', name: 'Veza i zdravlje', slot: 'bottom', part: null, fields: [],
  hints: ['Telemetrija 10 Hz, ping ispod ~50 ms.', 'Nucleo javlja: inače nema poze ni brzina.'],
  view(d) {
    if (!d.src) return none();
    const r = rows(d), bad = r[0][1] === 'warn' || r[0][1] === 'bad' || (r[2][2] === 'ne javlja');
    return { status: bad ? 'warn' : 'ok', text: r[0][2], vals: [['veza', r[0][2]], ['telemetrija', r[1][2]], ['Nucleo', r[2][2]]],
      foot: 'RSSI, RAM, krug petlje: ' + NOT_SENT };
  },
  html(d, big) {
    const body = rows(d).map(([k, c, v]) => `<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;`
      + `margin-right:7px;background:${DOT[c] || DOT.idle}"></span>${esc(k)}</td>`
      + `<td style="text-align:right;font-family:ui-monospace,monospace">${esc(v)}</td></tr>`).join('');
    return `<table style="width:100%;font-size:${big ? 16 : 12}px;padding:${big ? 16 : 2}px 10px;border-spacing:0 ${big ? 6 : 0}px">${body}</table>`
      + `<div class="dim" style="padding:0 10px;font-size:${big ? 13 : 11}px">RSSI, RAM i krug petlje: ${NOT_SENT}.</div>`;
  },
};
