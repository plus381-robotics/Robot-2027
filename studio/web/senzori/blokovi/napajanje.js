// Blok „Napajanje (INA3221)“ (desna kolona): baterija i kanali 5 V · baterija (ulaz) · posle total stopa. Danas ništa
// ne stiže (INA3221 nije podešen, nema simulacije); baterija krupno, kanali i total stop dolaze sa Zadatkom 10.
import { none, ok, at, num, unit } from './osnova.js';

export default {
  id: 'napajanje', name: 'Napajanje (INA3221)', slot: 'right', part: null, fields: ['bat'],
  hints: [
    'Baterija (ulaz) iznad praga iz Profila pre meča.',
    'Pritisni total stop: napon „posle total stopa“ pada na 0, a „Total stop: pritisnut“.',
    'U mirovanju pogon (posle total stopa) ~0,2 A; visoka struja dok stoji: nešto koči.',
    '5 V: skok struje kad krenu servo ili pumpe.',
  ],
  view(d) {
    if (!d.src) return none();
    const bat = at(d, 'bat');
    return ok([['baterija', unit(num(bat, 2), 'V')]]);
  },
};
