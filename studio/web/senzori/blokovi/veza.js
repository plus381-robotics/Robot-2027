// Blok „Veza i zdravlje“ (donji red): veza kao na traci (shell/strip.js linkView); ne zavisi od polja (fields []),
// pa ima izvor čim radi sesija. Redovi ESP ↔ laptop, telemetrija, Nucleo ↔ ESP, RSSI / RAM / krug petlje dolaze sa
// Zadatkom 10.
import { linkView } from '../../shell/strip.js';
import { none } from './osnova.js';

export default {
  id: 'veza', name: 'Veza i zdravlje', slot: 'bottom', part: null, fields: [],
  hints: ['Telemetrija 10 Hz, ping ispod ~50 ms.', 'Nucleo javlja: inače nema poze ni brzina.'],
  view(d) {
    if (!d.src) return none();
    const L = linkView(d.st || {});
    return { status: L.cls === 'warn' || L.cls === 'bad' ? 'warn' : 'ok', text: L.text, vals: [['veza', L.text]] };
  },
};
