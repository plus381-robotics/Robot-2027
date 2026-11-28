// Senzori: vrednosti iz snimka za dato vreme. Bez DOM-a. Kolona `t` snimka je u MILISEKUNDAMA (kao `run.duration`),
// pa je i `t` u svim funkcijama ispod u ms; samo `sec` (dužina istorije) je u sekundama.
//   lastAt(run, key, t)             vrednost u poslednjem frame-u sa t_frame <= t, ili null
//   history(run, key, t, sec = 15)  vrednosti frame-ova sa t - sec*1000 < t_frame <= t (null izostavljeni)
//   odoWheels(run, t0, t1, track)   {L, R, diff} u mm: put pasivnih točkova iz odometrijske poze (ox, oy [mm], oth [°]),
//                                   track = razmak točkova [mm]; null ako ox/oy/oth nemaju podataka

import { hasData } from '../core/run.js';

export function lastAt(run, key, t) {
  const c = run.cols[key];
  if (!c || !c.length) return null;
  const v = c[run.frameAt(t)];
  return v == null ? null : v;
}

export function history(run, key, t, sec = 15) {
  const c = run.cols[key], ts = run.cols.t;
  if (!c) return [];
  const out = [], lo = t - sec * 1000;
  for (let i = run.frameAt(t); i >= 0 && ts[i] > lo; i--) {
    if (ts[i] <= t && c[i] != null) out.push(c[i]);
  }
  return out.reverse();
}

export function odoWheels(run, t0, t1, track) {
  if (!hasData(run, 'ox') || !hasData(run, 'oy') || !hasData(run, 'oth')) return null;
  const { t, ox, oy, oth } = run.cols;
  let L = 0, R = 0;
  for (let i = 1; i < t.length; i++) {
    if (t[i] <= t0) continue;
    if (t[i] > t1) break;
    const a = i - 1;
    if (ox[a] == null || ox[i] == null || oy[a] == null || oy[i] == null || oth[a] == null || oth[i] == null) continue;
    const th0 = oth[a] * Math.PI / 180;
    let dth = (oth[i] - oth[a]) * Math.PI / 180;
    dth -= 2 * Math.PI * Math.round(dth / (2 * Math.PI));          // svedeno na [-π, π]
    const mid = th0 + dth / 2;
    const ds = (ox[i] - ox[a]) * Math.cos(mid) + (oy[i] - oy[a]) * Math.sin(mid);
    L += ds - dth * track / 2;
    R += ds + dth * track / 2;
  }
  return { L, R, diff: L - R };
}
