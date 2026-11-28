// Blok „Aktuatori“ (donji red): `act` = {id: poslednja zadata vrednost}; ime aktuatora iz store.actuators (info.actuators:
// {ime: id} iz ESP32/config.py ACTUATORS). Servo (AX): vrednost 0–1023 ↔ 0–300° (v · 300 / 1023), traka sa iglom i „↻“
// dok se vrednost menjala u poslednjih 300 ms. Sirova vrednost je u detalju (html).
// Tip aktuatora (servo / pumpa) će doći iz opcionog odeljka Profila; danas ga nema, pa se svaki aktuator crta kao servo.
// Kad se doda `[actuators.<ime>] type = "pumpa"`, isPump(d, ime) vraća true (čita d.profile.actuators[ime].type) i
// aktuator se crta kao lampica (upaljena kad je vrednost > 0) umesto trake.
import { lastAt } from '../podaci.js';
import { esc } from '../../core/api.js';
import { none, ok, at, DASH } from './osnova.js';

export const MOVING_MS = 300;
export const toDeg = v => Math.max(0, Math.min(300, v * 300 / 1023));
export const isPump = (d, name) => {
  const a = d && d.profile && d.profile.actuators;
  return !!(a && a[name] && a[name].type === 'pumpa');
};
const GREEN = '#3ecf8e', BLUE = '#4aa3ff', DIM = '#97a3b3', TEXT = '#e6ebf1', BAR = '#20262e';
const FONT = 'system-ui, sans-serif', MONO = 'ui-monospace, monospace';

// [{id, name, value|null, moving}] po id-u: poznati aktuatori (store.actuators) i svi id-ovi iz `act`.
export function actuatorRows(d) {
  const map = (d.st && d.st.actuators) || {}, byId = {};
  for (const [name, id] of Object.entries(map)) byId[String(id)] = name;
  const now = at(d, 'act'), act = now && typeof now === 'object' ? now : {};
  let before = {};
  if (d.run && d.run.cols && d.run.cols.t && d.run.cols.t.length) {
    const t = d.t == null ? d.run.duration : d.t, b = lastAt(d.run, 'act', t - MOVING_MS);
    if (b && typeof b === 'object') before = b;
  }
  const ids = [...new Set([...Object.keys(byId), ...Object.keys(act)])].sort((a, b) => Number(a) - Number(b));
  return ids.map(id => {
    const value = act[id] == null ? null : Number(act[id]);
    const moving = value != null && (before[id] == null || Number(before[id]) !== value);
    return { id, name: byId[id] || '#' + id, value, moving };
  });
}

export default {
  id: 'aktuatori', name: 'Aktuatori', slot: 'bottom', part: 'mehanizmi', fields: ['act'],
  hints: [
    'Imena dolaze iz ESP32/config.py (ACTUATORS).',
    'Servo: zadata i poslednja poznata pozicija; ↻ dok se kreće.',
    'Pumpe: upaljena / ugašena; uz struju na 5 V se vidi da li stvarno vuče.',
  ],
  view(d) {
    if (!d.src) return none();
    const rows = actuatorRows(d), got = rows.filter(r => r.value != null);
    return ok(rows.slice(0, 6).map(r => [r.name, r.value == null ? DASH : Math.round(toDeg(r.value)) + '°' + (r.moving ? ' ↻' : '')]),
      got.length ? 'radi' : 'nijedan se još nije pomerio');
  },
  draw(g, w, h, d, big) {
    const rows = actuatorRows(d);
    if (!rows.length) return;
    const fs = big ? 15 : 11, top = big ? 22 : 16, rh = Math.min(big ? 56 : 30, (h - top) / rows.length);
    g.fillStyle = DIM; g.font = (big ? 12 : 10) + 'px ' + FONT; g.textAlign = 'left';
    g.fillText('Servo (AX) · 0–300°', 8, 11);
    const lx = big ? 130 : Math.min(84, w * 0.3), bx = lx + 4, bw = Math.max(20, w - bx - (big ? 90 : 56));
    rows.forEach((r, i) => {
      const y = top + i * rh, by = y + rh / 2 - (big ? 6 : 4), bh = big ? 12 : 8, X = deg => bx + bw * deg / 300;
      g.fillStyle = TEXT; g.font = fs + 'px ' + FONT; g.textAlign = 'left'; g.fillText(r.name, 8, by + bh - 1);
      if (isPump(d, r.name)) {
        const on = r.value != null && r.value > 0, rad = big ? 9 : 6;
        g.beginPath(); g.arc(bx + rad, by + bh / 2, rad, 0, 7); g.fillStyle = on ? GREEN : BAR; g.fill();
        g.fillStyle = DIM; g.fillText(r.value == null ? DASH : on ? 'radi' : 'ugašena', bx + 2 * rad + 8, by + bh - 1);
        return;
      }
      g.fillStyle = BAR; g.fillRect(bx, by, bw, bh); g.strokeStyle = '#3d4a5a'; g.strokeRect(bx, by, bw, bh);
      if (r.value == null) { g.fillStyle = DIM; g.fillText(DASH, bx + bw + 6, by + bh - 1); return; }
      const deg = toDeg(r.value), nx = X(deg);
      g.fillStyle = r.moving ? BLUE : GREEN;
      g.beginPath(); g.moveTo(nx, by + bh + 1); g.lineTo(nx - 5, by + bh + 8); g.lineTo(nx + 5, by + bh + 8); g.fill();
      g.fillRect(nx - 1.5, by - 2, 3, bh + 4);
      g.fillStyle = r.moving ? BLUE : TEXT; g.font = 'bold ' + fs + 'px ' + MONO;
      g.fillText(Math.round(deg) + '°' + (r.moving ? ' ↻' : ''), bx + bw + 6, by + bh - 1);
    });
  },
  html(d, big) {
    if (!big) return '';
    const rows = actuatorRows(d).map(r => `<tr><td>#${esc(r.id)}</td><td><b>${esc(r.name)}</b></td>`
      + `<td>${r.value == null ? DASH : esc(String(r.value))}</td><td>${r.value == null ? DASH : Math.round(toDeg(r.value)) + '°'}</td></tr>`);
    return '<p class="dim">Sirova vrednost AX (0–1023) i ugao (0–300°). Tip aktuatora (servo / pumpa) još nije u Profilu: svi su servo.</p>'
      + `<table class="sz-irt"><tr><th>id</th><th>ime</th><th>vrednost</th><th>ugao</th></tr>${rows.join('')}</table>`;
  },
};
