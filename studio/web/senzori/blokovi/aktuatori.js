// Blok „Aktuatori“ (donji red): `act` = {id: poslednja vrednost}. Imena iz ESP32/config.py ACTUATORS, servo kao traka
// 0–300° i pumpe kao lampice dolaze sa Zadatkom 10; do tada id i vrednost.
import { none, ok, at } from './osnova.js';

export default {
  id: 'aktuatori', name: 'Aktuatori', slot: 'bottom', part: 'mehanizmi', fields: ['act'],
  hints: [
    'Imena dolaze iz ESP32/config.py (ACTUATORS).',
    'Servo: zadata i poslednja poznata pozicija; ↻ dok se kreće.',
    'Pumpe: upaljena / ugašena; uz struju na 5 V se vidi da li stvarno vuče.',
  ],
  view(d) {
    if (!d.src) return none();
    const a = at(d, 'act'), list = a && typeof a === 'object' ? Object.entries(a) : [];
    return ok(list.slice(0, 6).map(([k, v]) => ['#' + k, String(v)]), list.length ? 'radi' : 'nijedan se još nije pomerio');
  },
};
