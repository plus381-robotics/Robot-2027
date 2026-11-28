// Blok „Odozgo · lidar“ (mesto top): krugovi lidara oko robota. Uz sesiju poslednji krug sesije (store.lidarScan),
// bez nje krug snimka u trenutku d.t. Crtanje (radar, robot, IR u uglovima, najbliža grupa) i Upali/Ugasi lidar
// dolaze sa Zadatkom 8. Detalj su postojeći paneli lidara (panels/lidar.js, sensOpen = 'lidar').
import { none, ok, num } from './osnova.js';

function scanOf(d) {
  const st = d.st || {};
  if (st.session) return st.lidarScan || null;
  return d.run && d.run.lidarAt ? d.run.lidarAt(d.t) : null;
}

export default {
  id: 'lidar', name: 'Odozgo · lidar', slot: 'top', part: 'lidar', fields: ['@lidar'],
  hints: [
    'Stavi kutiju ~50 cm ispred robota: najbliža grupa ~500 mm, ugao ~0°.',
    'Pomeri je ulevo: ugao raste (suprotno od kazaljke).',
    'Učestanost 8–12 Hz. Ispod 5 Hz: proveri napajanje i kabl lidara.',
    'Tačke van stola (sivo) se ne računaju kao prepreka.',
  ],
  view(d) {
    if (!d.src) return none();
    const s = scanOf(d);
    if (!s) return ok([], 'čeka krug lidara');
    return ok([['Hz', num(s.hz, 1)], ['tačaka', String((s.pts || []).length)]]);
  },
};
