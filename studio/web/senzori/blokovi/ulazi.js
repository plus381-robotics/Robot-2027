// Blok „Činč i tasteri“ (donji red): robot će slati `btn` (ESP ih još ne šalje); u simulaciji je izvor stanje meča
// (simFields ['mec']). Lampice činč, STOP, OK, NAZAD i enkoder menija dolaze sa Zadatkom 10.
import { matchView } from '../../shell/strip.js';
import { none, ok, at } from './osnova.js';

export default {
  id: 'ulazi', name: 'Činč i tasteri', slot: 'bottom', part: null, fields: ['btn'], simFields: ['mec'],
  hints: [
    'Izvuci i vrati činč: lampica se gasi i pali.',
    'Pritisni STOP, OK, NAZAD i okreni enkoder menija: svaka promena se vidi.',
  ],
  view(d) {
    if (!d.src) return none();
    return ok([['meč', matchView({ state: at(d, 'mec'), ms: at(d, 'match') }).text]]);
  },
};
