// Senzori: vrednosti iz snimka za dato vreme. Bez DOM-a. Kolona `t` snimka je u MILISEKUNDAMA (kao `run.duration`),
// pa je i `t` u svim funkcijama ispod u ms; samo `sec` (dužina istorije) je u sekundama.
//   lastAt(run, key, t)             vrednost u poslednjem frame-u sa t_frame <= t, ili null
//   history(run, key, t, sec = 15)  vrednosti frame-ova sa t - sec*1000 < t_frame <= t (null izostavljeni)
//   odoWheels(run, t0, t1, track)   {L, R, diff} u mm: put pasivnih točkova iz odometrijske poze (ox, oy [mm], oth [°]),
//                                   skok poze (> 3000 mm/s ili > 720 °/s, postavljanje početne poze) se ne broji; track = razmak točkova [mm];
//                                   null ako ox/oy/oth nemaju podataka
//   odoSeries(run, t0, t1, track)   isto, kumulativno po frame-ovima: {t, L, R} (za grafik), ili null

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

// Pomeraj poze između dva frame-a: „skok“ (postavljanje početne poze na početku sesije, ili nemoguća brzina) se ne
// računa kao put točkova: brzina > JUMP_MM_S ili brzina okreta > JUMP_DEG_S.
const JUMP_MM_S = 3000, JUMP_DEG_S = 720;

// Kumulativni put pasivnih točkova po frame-ovima u (t0, t1]: {t: [], L: [], R: []} (mm), svaki frame posle prvog.
export function odoSeries(run, t0, t1, track) {
  if (!hasData(run, 'ox') || !hasData(run, 'oy') || !hasData(run, 'oth')) return null;
  const { t, ox, oy, oth } = run.cols;
  const out = { t: [], L: [], R: [] };
  let L = 0, R = 0;
  for (let i = 1; i < t.length; i++) {
    if (t[i] <= t0) continue;
    if (t[i] > t1) break;
    const a = i - 1;
    if (ox[a] != null && ox[i] != null && oy[a] != null && oy[i] != null && oth[a] != null && oth[i] != null) {
      const th0 = oth[a] * Math.PI / 180;
      let dth = (oth[i] - oth[a]) * Math.PI / 180;
      dth -= 2 * Math.PI * Math.round(dth / (2 * Math.PI));          // svedeno na [-π, π]
      const dx = ox[i] - ox[a], dy = oy[i] - oy[a], dt = (t[i] - t[a]) / 1000;
      const jump = !(dt > 0) || Math.hypot(dx, dy) / dt > JUMP_MM_S || Math.abs(dth) * 180 / Math.PI / dt > JUMP_DEG_S;
      if (!jump) {
        const mid = th0 + dth / 2;
        const ds = dx * Math.cos(mid) + dy * Math.sin(mid);
        L += ds - dth * track / 2;
        R += ds + dth * track / 2;
      }
    }
    out.t.push(t[i]); out.L.push(L); out.R.push(R);
  }
  return out;
}

export function odoWheels(run, t0, t1, track) {
  const s = odoSeries(run, t0, t1, track);
  if (!s) return null;
  const n = s.L.length, L = n ? s.L[n - 1] : 0, R = n ? s.R[n - 1] : 0;
  return { L, R, diff: L - R };
}
