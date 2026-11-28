// Blok „Brzine v i ω“ (desna kolona): poslednje vrednosti i dva mala grafika, v (mm/s) i ω (°/s), poslednjih 15 s
// (u snimku: 15 s pre kursora). Na pravom robotu ω još ne stiže: umesto grafika ide napomena (d.note iz notes.robot).
//   series(d, key, k)   istorija kolone (15 s do d.t) pomnožena sa k (m/s -> mm/s: 1000; rad/s -> °/s: 180/π)
import { hasData } from '../../core/run.js';
import { history } from '../podaci.js';
import { drawLines, GCOL } from '../grafik.js';
import { none, ok, at, mms, degs } from './osnova.js';

const RAD = 180 / Math.PI;
export const series = (d, key, k) => (d.run && d.run.cols && d.run.cols.t && d.run.cols.t.length
  ? history(d.run, key, d.t == null ? d.run.duration : d.t).map(v => v * k) : []);

export default {
  id: 'brzine', name: 'Brzine v i ω', slot: 'right', part: 'pogon', fields: ['v', 'w'],
  notes: { robot: { w: 'ω: ESP je još ne šalje laptopu' } },
  hints: [
    'Dok vozi pravo, ω je oko nule.',
    'U mirovanju obe su nula; šum veći od ~5 mm/s znači da enkoder „trese“.',
  ],
  view(d) {
    if (!d.src) return none();
    return ok([['v', mms(at(d, 'v'))], ['ω', degs(at(d, 'w'))]]);
  },
  draw(g, w, h, d, big) {
    const half = (h - 8) / 2, y2 = half + 6;
    drawLines(g, 0, 2, w, half, [[series(d, 'v', 1000), '#4aa3ff']], { big, minSpan: 100, label: 'v (mm/s)' });
    if (d.run && hasData(d.run, 'w')) {
      drawLines(g, 0, y2, w, half, [[series(d, 'w', RAD), '#38d9f5']], { big, minSpan: 10, label: 'ω (°/s)' });
    } else {
      g.fillStyle = GCOL.dim; g.font = '12px system-ui, sans-serif';
      g.fillText(d.note || 'ω: nema podataka', big ? 40 : 10, y2 + half / 2 + 4);
    }
  },
};
