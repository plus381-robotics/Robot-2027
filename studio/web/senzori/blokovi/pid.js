// Blok „Regulacija (PID)“ (desna kolona): zadato (isprekidano) i stvarno (puna linija) za v (mm/s) i ω (°/s), poslednjih
// 15 s (u snimku: 15 s pre kursora). Na pravom robotu Nucleo zadato ne šalje (blockSource: bez izvora, status 'none').
import { drawLines, GCOL } from '../grafik.js';
import { series } from './brzine.js';
import { none, ok, at, mms, degs } from './osnova.js';

const RAD = 180 / Math.PI;

export default {
  id: 'pid', name: 'Regulacija (PID)', slot: 'right', part: 'pogon', fields: ['v_ref', 'w_ref'],
  hints: [
    'Pošalji pomeraj 20 cm: stvarna brzina prati zadatu bez ljuljanja.',
    'Preskok manji od ~10 %, smiruje se za < 0,3 s.',
    'U simulaciji ovo je model iz Profila (regulacija).',
  ],
  view(d) {
    if (!d.src) return none();
    return ok([['v zadato', mms(at(d, 'v_ref'))], ['v', mms(at(d, 'v'))],
      ['ω zadato', degs(at(d, 'w_ref'))], ['ω', degs(at(d, 'w'))]]);
  },
  draw(g, w, h, d, big) {
    const half = (h - 8) / 2, y2 = half + 6;
    drawLines(g, 0, 2, w, half, [[series(d, 'v_ref', 1000), GCOL.set, true], [series(d, 'v', 1000), GCOL.act]],
      { big, minSpan: 100, label: big ? 'v: zadato (isprekidano) i stvarno (mm/s)' : 'v (mm/s)' });
    drawLines(g, 0, y2, w, half, [[series(d, 'w_ref', RAD), GCOL.set, true], [series(d, 'w', RAD), GCOL.actR]],
      { big, minSpan: 10, label: big ? 'ω: zadato (isprekidano) i stvarno (°/s)' : 'ω (°/s)' });
  },
};
