// Blok „Enkoderi“ (donji red): pasivni odometrijski točkovi. Put L i D od „Nuliraj“ (iz odometrijske poze ox, oy, oth
// i encoder_track iz Profila, senzori/podaci.js odoWheels), razlika L − D sa pragom i grafik dolaze sa Zadatkom 9.
// Do tada samo oznaka izvora: put od početka snimka bi brojao i postavljanje početne poze (skok 0,0 -> start).
import { none, ok } from './osnova.js';

export default {
  id: 'enkoderi', name: 'Enkoderi', slot: 'bottom', part: 'pogon', fields: ['ox', 'oy', 'oth'],
  hints: [
    'Klikni Nuliraj, pa gurni robota 50 cm pravo: L i D ~500 mm, razlika manja od 5 mm.',
    'Okreni ga u mestu: L i D suprotnog znaka, iste veličine.',
    'Jedan točak stoji na nuli: kabl enkodera ili konektor.',
  ],
  view(d) {
    return d.src ? ok([], 'odometrija stiže') : none();
  },
};
