// Blok „Meč i taktika“ (donji red): stanje meča (mec, match) kao na traci (shell/strip.js matchView) i taktika.
// Strana i veći prikaz dolaze sa Zadatkom 10.
import { matchView } from '../../shell/strip.js';
import { none, ok, at, DASH } from './osnova.js';

export default {
  id: 'mec', name: 'Meč i taktika', slot: 'bottom', part: null, fields: ['mec'],
  hints: ['Pre meča: prava taktika, prava strana, stanje „spreman“.'],
  view(d) {
    if (!d.src) return none();
    const m = matchView({ state: at(d, 'mec'), ms: at(d, 'match') }), tac = at(d, 'tac');
    return ok([['stanje', m.text], ['taktika', tac ? String(tac) : DASH]]);
  },
};
