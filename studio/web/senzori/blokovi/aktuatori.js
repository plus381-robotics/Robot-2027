// Blok „Aktuatori“ (donji red): `act` = {id: poslednja zadata vrednost}; ime aktuatora iz store.actuators (info.actuators:
// {ime: id} iz ESP32/config.py ACTUATORS). Kako se crta zavisi od tipa iz Profila (actType):
//   bez tipa (danas svi)  ime i sirova vrednost, bez uglova i trake (ne zna se šta vrednost znači)
//   servo (AX)            vrednost 0–1023 ↔ 0–300° (v · 300 / 1023), traka sa iglom i „↻“ dok se vrednost menjala u
//                         poslednjih 300 ms
//   pumpa                 lampica: radi (vrednost > 0) / ugašena
// Tip je u opcionom odeljku Profila (studio/profiles/*.toml), po imenu iz ACTUATORS, odvojeno od `default_ms` i
// `[actuators.ms]` da se ne sudare:
//   [actuators.type]
//   lift = "servo"
//   pumpa_l = "pumpa"
// Stiže kao d.profile.actuators.type (/api/info → profile.actuators); drugi tipovi (npr. ventil) se crtaju kao bez tipa.
// Sirova vrednost (i ugao za servo) je i u detalju (html).
import { lastAt } from '../podaci.js';
import { esc } from '../../core/api.js';
import { none, ok, at, DASH } from './osnova.js';

export const MOVING_MS = 300;
export const TYPES = ['servo', 'pumpa'];
export const toDeg = v => Math.max(0, Math.min(300, v * 300 / 1023));
export const actType = (d, name) => {
  const a = d && d.profile && d.profile.actuators, types = a && a.type && typeof a.type === 'object' ? a.type : null;
  return types && TYPES.includes(types[name]) ? types[name] : null;
};
export const isPump = (d, name) => actType(d, name) === 'pumpa';
const GREEN = '#3ecf8e', BLUE = '#4aa3ff', DIM = '#97a3b3', TEXT = '#e6ebf1', BAR = '#20262e';
const FONT = 'system-ui, sans-serif', MONO = 'ui-monospace, monospace';

// [{id, name, type, value|null, moving}] po id-u: poznati aktuatori (store.actuators) i svi id-ovi iz `act`.
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
    const value = act[id] == null ? null : Number(act[id]), name = byId[id] || '#' + id;
    const moving = value != null && (before[id] == null || Number(before[id]) !== value);
    return { id, name, type: actType(d, name), value, moving };
  });
}

// Tekst vrednosti po tipu: servo ugao (i ↻ dok se kreće), pumpa radi / ugašena, bez tipa sirova vrednost.
function valueText(r) {
  if (r.value == null) return DASH;
  if (r.type === 'servo') return Math.round(toDeg(r.value)) + '°' + (r.moving ? ' ↻' : '');
  if (r.type === 'pumpa') return r.value > 0 ? 'radi' : 'ugašena';
  return String(r.value);
}

export default {
  id: 'aktuatori', name: 'Aktuatori', slot: 'bottom', part: 'mehanizmi', fields: ['act'],
  hints: [
    'Imena dolaze iz ESP32/config.py (ACTUATORS); tip (servo / pumpa) iz Profila, odeljak [actuators.type].',
    'Bez tipa: sirova vrednost kako ju je taktika zadala.',
    'Servo: zadata i poslednja poznata pozicija; ↻ dok se kreće.',
    'Pumpe: upaljena / ugašena; uz struju na 5 V se vidi da li stvarno vuče.',
  ],
  view(d) {
    if (!d.src) return none();
    const rows = actuatorRows(d), got = rows.filter(r => r.value != null);
    return ok(rows.slice(0, 6).map(r => [r.name, valueText(r)]), got.length ? 'radi' : 'nijedan se još nije pomerio');
  },
  draw(g, w, h, d, big) {
    const rows = actuatorRows(d);
    if (!rows.length) return;
    const fs = big ? 15 : 11, top = big ? 22 : 16, rh = Math.min(big ? 56 : 30, (h - top) / rows.length);
    const servo = rows.some(r => r.type === 'servo');
    g.fillStyle = DIM; g.font = (big ? 12 : 10) + 'px ' + FONT; g.textAlign = 'left';
    g.fillText(servo ? 'Servo (AX) · 0–300°' : 'Sirova vrednost (tip nije u Profilu)', 8, 11);
    const lx = big ? 130 : Math.min(84, w * 0.3), bx = lx + 4, bw = Math.max(20, w - bx - (big ? 90 : 56));
    rows.forEach((r, i) => {
      const y = top + i * rh, by = y + rh / 2 - (big ? 6 : 4), bh = big ? 12 : 8, X = deg => bx + bw * deg / 300;
      g.fillStyle = TEXT; g.font = fs + 'px ' + FONT; g.textAlign = 'left'; g.fillText(r.name, 8, by + bh - 1);
      if (r.type === 'pumpa') {
        const on = r.value != null && r.value > 0, rad = big ? 9 : 6;
        g.beginPath(); g.arc(bx + rad, by + bh / 2, rad, 0, 7); g.fillStyle = on ? GREEN : BAR; g.fill();
        g.fillStyle = DIM; g.fillText(valueText(r), bx + 2 * rad + 8, by + bh - 1);
        return;
      }
      if (r.type !== 'servo') {                       // bez tipa: samo sirova vrednost, bez trake i uglova
        g.fillStyle = r.value == null ? DIM : TEXT; g.font = (r.value == null ? '' : 'bold ') + fs + 'px ' + MONO;
        g.fillText(valueText(r), bx, by + bh - 1);
        return;
      }
      g.fillStyle = BAR; g.fillRect(bx, by, bw, bh); g.strokeStyle = '#3d4a5a'; g.strokeRect(bx, by, bw, bh);
      if (r.value == null) { g.fillStyle = DIM; g.fillText(DASH, bx + bw + 6, by + bh - 1); return; }
      const deg = toDeg(r.value), nx = X(deg);
      g.fillStyle = r.moving ? BLUE : GREEN;
      g.beginPath(); g.moveTo(nx, by + bh + 1); g.lineTo(nx - 5, by + bh + 8); g.lineTo(nx + 5, by + bh + 8); g.fill();
      g.fillRect(nx - 1.5, by - 2, 3, bh + 4);
      g.fillStyle = r.moving ? BLUE : TEXT; g.font = 'bold ' + fs + 'px ' + MONO;
      g.fillText(valueText(r), bx + bw + 6, by + bh - 1);
    });
  },
  html(d, big) {
    if (!big) return '';
    const rows = actuatorRows(d).map(r => `<tr><td>#${esc(r.id)}</td><td><b>${esc(r.name)}</b></td><td>${esc(r.type || DASH)}</td>`
      + `<td>${r.value == null ? DASH : esc(String(r.value))}</td>`
      + `<td>${r.type === 'servo' && r.value != null ? Math.round(toDeg(r.value)) + '°' : DASH}</td></tr>`);
    return '<p class="dim">Sirova vrednost kako ju je taktika zadala. Ugao (AX 0–1023 ↔ 0–300°) samo za tip servo; tip se'
      + ' zadaje u Profilu, odeljak [actuators.type] (ime = "servo" ili "pumpa"). Bez tipa se ne zna šta vrednost znači.</p>'
      + `<table class="sz-irt"><tr><th>id</th><th>ime</th><th>tip</th><th>vrednost</th><th>ugao</th></tr>${rows.join('')}</table>`;
  },
};
