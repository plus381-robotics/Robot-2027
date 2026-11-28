// Senzori: zajedničko za module blokova (bez DOM-a). Oblik bloka i `d` su opisani u blokovi/index.js.
//   none()                 {status: 'none', text: 'bez podataka', vals: []}  (blok bez izvora)
//   ok(vals, text)         {status: 'ok', text (podrazumevano 'radi'), vals}
//   at(d, key)             vrednost kolone u trenutku d.t (poslednji frame sa t_frame <= d.t), ili null
//   num(v, dec)            broj sa decimalnim zarezom; null -> '—'
//   unit(text, u)          broj i jedinica sa tvrdim razmakom (u pločici se ne prelamaju)
//   mms(v) / degs(w)       m/s -> 'n mm/s'; rad/s -> 'n,n °/s' (kolone v, v_ref i w, w_ref su u m/s i rad/s)
import { lastAt } from '../podaci.js';

export const DASH = '—';
export const none = () => ({ status: 'none', text: 'bez podataka', vals: [] });
export const ok = (vals = [], text = 'radi') => ({ status: 'ok', text, vals });

export function at(d, key) {
  const run = d && d.run;
  if (!run || !run.cols || !run.cols.t || !run.cols.t.length) return null;
  return lastAt(run, key, d.t == null ? run.duration : d.t);
}

export function num(v, dec = 0) {
  if (v == null || typeof v !== 'number' || !Number.isFinite(v)) return DASH;
  return dec ? v.toFixed(dec).replace('.', ',') : String(Math.round(v) || 0);
}

export const unit = (text, u) => (text === DASH ? DASH : text + '\u00a0' + u);
export const mms = v => (v == null ? DASH : unit(num(v * 1000), 'mm/s'));
export const degs = w => (w == null ? DASH : unit(num(w * 180 / Math.PI, 1), '°/s'));
