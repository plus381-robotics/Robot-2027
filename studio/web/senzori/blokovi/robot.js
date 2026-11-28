// Blok „Robot · IR“ (mesto sketch): skica SPREDA i POZADI jedna ispod druge (raspored: senzori/skica.js elevation). Telo
// iz Profila, lidar UVEK na vrhu tela sa isprekidanom ravni skeniranja (svetli dok stižu krugovi lidara), IR D i U kao
// lampice (samo da/ne) na low_z / high_z uz ivice tela, pogonski točkovi (±wheel_track/2) i pasivni odometrijski
// (±encoder_track/2) sa mm enkodera: put od „Nuliraj“ (store.sensZero), inače od početka snimka (podaci.js odoWheels).
// Bitovi `ir` (vidi) i `irm` (maska taktike) idu redom profile.ir_sensors (FLD FLU FRD FRU BLD BLU BRD BRU, fizička imena).
// Detalj (klik): velika skica i lista 8 senzora (mesto, vidi, maska; na plavoj strani i ime u taktici, L <-> D).
//   wheelsAt(d, track)   {L, R, diff} u mm od „Nuliraj“ (ili početka snimka) do d.t, ili null (nema odometrije)
import { esc } from '../../core/api.js';
import { odoWheels } from '../podaci.js';
import { sketchGeometry, irSensors, elevation, lamp } from '../skica.js';
import { none, ok, at, num, DASH } from './osnova.js';
import { lidarLive } from './lidar.js';

const COL = { ground: '#3d4a5a', body: '#dfe5ec', bodyFill: 'rgba(223,229,236,.08)', wheel: '#0b0d10', wheelEdge: '#556070',
  enc: '#4aa3ff', encOff: '#6b7686', lidar: '#38d9f5', lidarOff: '#20262e', mount: '#3d4a5a', text: '#e6ebf1', dim: '#97a3b3',
  sep: '#2a313c' };
const FONT = 'system-ui, sans-serif';

export function wheelsAt(d, track) {
  const run = d && d.run;
  if (!run || !run.cols || !run.cols.t || !run.cols.t.length) return null;
  const st = d.st || {}, t0 = st.sensZero != null ? st.sensZero : run.cols.t[0];
  return odoWheels(run, t0, d.t == null ? run.duration : d.t, track);
}

const bitOn = (m, bit) => (m == null ? null : !!((m >> bit) & 1));
const tacticName = n => n.replace('L', 'r').replace('R', 'L').replace('r', 'R');   // plava strana: levo <-> desno (tac._ir_bits)

function fillRect(g, r, fill, stroke) {
  g.beginPath(); g.rect(r[0], r[1], r[2] - r[0], r[3] - r[1]);
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.stroke(); }
}

function drawSketch(g, L, box, o) {
  const f = L.font, x0 = box.x, x1 = box.x + box.w;
  g.textBaseline = 'alphabetic';
  g.strokeStyle = COL.ground; g.lineWidth = 1;                                    // pod
  g.beginPath(); g.moveTo(x0 + 10, L.gy); g.lineTo(x1 - 10, L.gy); g.stroke();
  g.lineWidth = 1.6; fillRect(g, L.body, COL.bodyFill, COL.body); g.lineWidth = 1;   // telo
  for (const w of L.drive) fillRect(g, w.rect, COL.wheel, COL.wheelEdge);          // pogonski točkovi
  for (const w of L.odo) {                                                         // pasivni točkovi + mm enkodera
    const v = o.enc ? (w.left ? o.enc.L : o.enc.R) : null;
    fillRect(g, w.rect, COL.wheel, v == null ? COL.wheelEdge : COL.enc);
    const txt = `${w.name} ${v == null ? DASH : num(v)}${o.big && v != null ? ' mm' : ''}`;
    let px = f;
    g.font = `bold ${px}px ${FONT}`;
    const room = Math.abs(w.text.x - L.cx) - 3;                                     // do sredine (druga strana piše svoj)
    while (px > 8 && g.measureText(txt).width > room) { px--; g.font = `bold ${px}px ${FONT}`; }
    g.fillStyle = v == null ? COL.encOff : COL.enc; g.textAlign = w.text.align;
    g.fillText(txt, w.text.x, w.text.y);
  }
  const ld = L.lidar;                                                             // lidar na vrhu tela
  fillRect(g, ld.mount, COL.mount, null);
  fillRect(g, ld.box, o.lidarOn ? COL.lidar : COL.lidarOff, o.lidarOn ? COL.lidar : COL.wheelEdge);
  g.strokeStyle = o.lidarOn ? COL.lidar : COL.wheelEdge; g.setLineDash([6, 4]);
  g.beginPath(); g.moveTo(ld.scanX[0], ld.scanY); g.lineTo(ld.scanX[1], ld.scanY); g.stroke(); g.setLineDash([]);
  g.fillStyle = o.lidarOn ? COL.lidar : COL.encOff; g.font = `${f}px ${FONT}`; g.textAlign = 'center';
  g.fillText('lidar', L.cx, ld.labelY);
  for (const l of L.lamps) {                                                      // IR: D i U, samo da/ne
    lamp(g, l.x, l.y, l.r, bitOn(o.ir, l.bit), l.upper ? 'U' : 'D');
    g.fillStyle = COL.text; g.font = `bold ${f + 1}px ${FONT}`; g.textAlign = l.label.align; g.textBaseline = 'middle';
    g.fillText(l.name, l.label.x, l.y + 1);
    g.textBaseline = 'alphabetic';
  }
  g.textAlign = 'center';                                                          // SPREDA (stojiš ispred robota)
  g.fillStyle = COL.text; g.font = `bold ${f + 1}px ${FONT}`; g.fillText(L.title[0], L.cx, L.gy + f + 3);
  g.fillStyle = COL.dim; g.font = `${f - 1}px ${FONT}`; g.fillText(L.title[1], L.cx, L.gy + 2 * f + 5);
  g.textAlign = 'left'; g.fillText(L.sides.left, x0 + 6, L.gy - 4);                // koja strana robota je levo / desno
  g.textAlign = 'right'; g.fillText(L.sides.right, x1 - 6, L.gy - 4);
  g.textAlign = 'left';
}

function draw(g, w, h, d, big) {
  const geo = sketchGeometry(d.profile), sens = irSensors(d.profile);
  const o = { ir: at(d, 'ir'), enc: wheelsAt(d, geo.odoTrack), lidarOn: lidarLive(d), big: !!big };
  const gap = big ? 12 : 6, hh = (h - gap) / 2;
  const top = { x: 0, y: 0, w, h: hh }, bot = { x: 0, y: hh + gap, w, h: hh };
  drawSketch(g, elevation(geo, sens, top, 'spreda', big), top, o);
  g.strokeStyle = COL.sep; g.lineWidth = 1;
  g.beginPath(); g.moveTo(10, hh + gap / 2); g.lineTo(w - 10, hh + gap / 2); g.stroke();
  drawSketch(g, elevation(geo, sens, bot, 'pozadi', big), bot, o);
}

// Detalj: lista 8 senzora (pored velike skice).
function html(d) {
  const sens = irSensors(d.profile), geo = sketchGeometry(d.profile), ir = at(d, 'ir'), irm = at(d, 'irm');
  const blue = !!(d.run && d.run.meta && d.run.meta.side === 'plava');
  const rows = sens.map(s => {
    const sees = bitOn(ir, s.bit), used = bitOn(irm, s.bit);
    const where = `${s.front ? 'spreda' : 'pozadi'} ${s.left ? 'levo' : 'desno'}, ${s.upper ? 'gornji' : 'donji'} `
      + `(${s.upper ? geo.irHigh : geo.irLow} mm)`;
    const name = `<b>${esc(s.name)}</b>` + (blue ? ` <span class="dim" title="Plava strana: taktika ga zove ovako">`
      + `(taktika: ${esc(tacticName(s.name))})</span>` : '');
    return `<tr class="${sees == null ? 'na' : sees ? 'on' : 'off'}"><td>${name}</td><td>${esc(where)}</td>`
      + `<td class="sz-irs">${sees == null ? DASH : sees ? '● vidi' : '○ ne'}</td>`
      + `<td>${used == null ? DASH : used ? 'uključen' : 'isključen'}</td></tr>`;
  }).join('');
  return `<p class="dim">IR je samo da/ne (domet točkićem na senzoru). Maska: koje senzore taktika koristi; isključen ne
      zaustavlja robota, ali i dalje meri.${blue ? ' Plava strana: taktika zove senzore sa zamenjenim L i R.' : ''}</p>
    <table class="sz-irt"><thead><tr><th>senzor</th><th>mesto</th><th>vidi</th><th>maska</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

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
    const sens = irSensors(d.profile), ir = at(d, 'ir'), irm = at(d, 'irm');
    const list = m => (m == null ? DASH : sens.filter(s => bitOn(m, s.bit)).map(s => s.name).join(' ') || 'nijedan');
    const all = irm != null && sens.every(s => bitOn(irm, s.bit));
    const vals = [['aktivni', list(ir)], ['maska', all ? 'svi' : list(irm)]];
    return ir == null ? { status: 'none', text: 'čeka IR', vals } : ok(vals);
  },
  draw,
  html,
};
