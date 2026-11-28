// Blok „Brzine v i ω“ (desna kolona): poslednje vrednosti; grafici kroz vreme dolaze sa Zadatkom 9.
// Na pravom robotu ω još ne stiže (napomena iz notes.robot ide uz oznaku PRAVO).
import { none, ok, at, mms, degs } from './osnova.js';

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
};
