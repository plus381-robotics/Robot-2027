// Blok „Regulacija (PID)“ (desna kolona): zadato i stvarno za v i ω; grafici (zadato isprekidano) dolaze sa
// Zadatkom 9. Na pravom robotu Nucleo zadato još ne šalje.
import { none, ok, at, mms, degs } from './osnova.js';

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
};
