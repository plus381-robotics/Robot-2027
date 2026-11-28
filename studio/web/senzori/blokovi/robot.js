// Blok „Robot · IR“ (mesto sketch): IR senzori (samo da/ne). Bitovi `ir` (vidi) i `irm` (maska taktike) idu redom
// imena iz Profila (profile.ir_sensors: FLD FLU FRD FRU BLD BLU BRD BRU). Skica spreda i pozadi dolazi sa Zadatkom 8.
import { none, ok, at, DASH } from './osnova.js';

export default {
  id: 'robot', name: 'Robot · IR', slot: 'sketch', part: 'ir', fields: ['ir'],
  hints: [
    'Prinesi ruku svakom uglu: upali se D (donji), pa U (gornji).',
    'IR je samo da/ne: domet se podešava točkićem na samom senzoru.',
    'Svetli bez prepreke: smanji domet točkićem ili očisti senzor.',
    'Maska pokazuje koje senzore taktika trenutno koristi.',
  ],
  view(d) {
    if (!d.src) return none();
    const names = ((d.profile && d.profile.ir_sensors) || []).map(s => s.name);
    const list = m => (m == null ? DASH : names.filter((n, k) => m & (1 << k)).join(' ') || 'nijedan');
    const ir = at(d, 'ir'), irm = at(d, 'irm');
    const all = names.length && irm === (1 << names.length) - 1;
    return ok([['aktivni', list(ir)], ['maska', all ? 'svi' : list(irm)]]);
  },
};
