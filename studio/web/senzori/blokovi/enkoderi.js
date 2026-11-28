// Blok „Enkoderi“ (donji red): pasivni odometrijski točkovi. Put L i D u mm od „Nuliraj“ (store.sensZero; bez toga od
// početka snimka) iz odometrijske poze ox, oy, oth i encoder_track iz Profila (podaci.js odoWheels), bez maksimuma.
// Razlika L − D oko nule (±10 mm): zelena < 5 mm, narandžasta od 5 mm (status ok / warn). U detalju grafik puta sa
// skalom koja se sama širi. „Nuliraj“ pamti d.t kao sensZero.
import { odoSeries } from '../podaci.js';
import { drawLines } from '../grafik.js';
import { none, ok, num, unit } from './osnova.js';
import { wheelsAt } from './robot.js';

const GREEN = '#3ecf8e', ORANGE = '#ffb547', BLUE = '#4aa3ff', DIM = '#97a3b3', TEXT = '#e6ebf1', BAR = '#20262e';
const FONT = 'system-ui, sans-serif', MONO = 'ui-monospace, monospace';
const LIMIT = 5, SCALE = 10;
const trackOf = d => (d.profile && d.profile.odometry && d.profile.odometry.encoder_track) || 286;

export default {
  id: 'enkoderi', name: 'Enkoderi', slot: 'bottom', part: 'pogon', fields: ['ox', 'oy', 'oth'],
  hints: [
    'Klikni Nuliraj, pa gurni robota 50 cm pravo: L i D ~500 mm, razlika manja od 5 mm.',
    'Okreni ga u mestu: L i D suprotnog znaka, iste veličine.',
    'Jedan točak stoji na nuli: kabl enkodera ili konektor.',
  ],
  view(d) {
    if (!d.src) return none();
    const w = wheelsAt(d, trackOf(d));
    if (!w) return ok([], 'odometrija stiže');
    const warn = Math.abs(w.diff) >= LIMIT;
    return { status: warn ? 'warn' : 'ok', text: warn ? 'točkovi se razlikuju' : 'radi',
      vals: [['L', unit(num(w.L), 'mm')], ['D', unit(num(w.R), 'mm')], ['L − D', unit(num(w.diff, 1), 'mm')]] };
  },
  actions(d) {
    return [{ label: 'Nuliraj', title: 'Put L i D se računa od ovog trenutka', disabled: !d.ctx || !d.src,
      run() { if (d.ctx && d.ctx.store) d.ctx.store.set({ sensZero: d.t }); } }];
  },
  draw(g, w, h, d, big) {
    const wh = wheelsAt(d, trackOf(d));
    if (!wh) return;
    const diff = wh.diff, fs = big ? 40 : 22, y1 = big ? 56 : 30, good = Math.abs(diff) < LIMIT;
    [['L', wh.L, BLUE, 0], ['D', wh.R, GREEN, 1]].forEach(([n, v, c, i]) => {
      const x = 8 + i * w / 2;
      g.fillStyle = DIM; g.font = (big ? 14 : 11) + 'px ' + FONT; g.fillText('točak ' + n, x, big ? 16 : 11);
      g.fillStyle = c; g.font = '800 ' + fs + 'px ' + MONO; g.fillText(num(v), x, y1);
      const tw = g.measureText(num(v)).width;
      g.fillStyle = DIM; g.font = (big ? 16 : 12) + 'px ' + FONT; g.fillText('mm', x + tw + 4, y1);
    });
    const by = y1 + (big ? 30 : 16), bw = w - 16, mid = 8 + bw / 2, f = Math.max(-1, Math.min(1, diff / SCALE));
    g.fillStyle = DIM; g.font = (big ? 14 : 11) + 'px ' + FONT; g.fillText('razlika L − D', 8, by);
    g.fillStyle = good ? GREEN : ORANGE; g.font = 'bold ' + (big ? 16 : 12) + 'px ' + MONO;
    g.textAlign = 'right'; g.fillText((diff >= 0 ? '+' : '') + num(diff, 1) + ' mm', w - 8, by); g.textAlign = 'left';
    const yb = by + 6, bh = big ? 12 : 8;
    g.fillStyle = BAR; g.fillRect(8, yb, bw, bh);
    g.fillStyle = 'rgba(62,207,142,.15)'; g.fillRect(mid - bw / 4, yb, bw / 2, bh);
    g.fillStyle = good ? GREEN : ORANGE; g.fillRect(Math.min(mid, mid + f * bw / 2), yb, Math.abs(f * bw / 2), bh);
    g.fillStyle = TEXT; g.fillRect(mid - 1, yb - 3, 2, bh + 6);
    if (big) {
      g.fillStyle = DIM; g.font = '12px ' + FONT; g.fillText('−10', 8, yb + bh + 14);
      g.textAlign = 'right'; g.fillText('+10 mm', w - 8, yb + bh + 14); g.textAlign = 'left';
      const cy = yb + bh + 30, ch = h - cy - 8, run = d.run;
      if (ch < 30 || !run) return;
      const t1 = d.t == null ? run.duration : d.t, t0 = d.st && d.st.sensZero != null ? d.st.sensZero : run.cols.t[0];
      const s = odoSeries(run, t0, t1, trackOf(d));
      if (!s) return;
      let k = s.t.length;
      while (k > 0 && s.t[k - 1] > t1 - 15000) k--;
      const L = s.L.slice(k), R = s.R.slice(k), all = [...L, ...R];
      const lo = Math.min(0, ...all), hi = Math.max(10, ...all), pad = (hi - lo) * 0.1;
      drawLines(g, 0, cy, w, ch, [[L, BLUE], [R, GREEN]], { big, lo: Math.floor(lo - pad), hi: Math.ceil(hi + pad),
        label: 'Pređeno od nule (mm), poslednjih 15 s · skala se sama širi' });
    }
  },
};
