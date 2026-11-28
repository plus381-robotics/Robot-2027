// Blok „Napajanje (INA3221)“ (desna kolona): baterija krupno + ≈ % + traka sa pragom, tabela kanala V i A i lampica
// „Total stop“. INA3221 meri tri kanala: 5 V (logika) · baterija (ulaz) · posle total stopa.
// Očekivana (buduća) imena polja telemetrije, kolone snimka (danas ih NIJEDAN izvor ne šalje, pa je blok bez podataka
// sa razlogom iz izvor.js; crta se tek kad kolona `bat` postoji, a dok vrednosti nema lampica je prazna, status 'none'):
//   bat     V   napon baterije na ulazu (kanal „baterija“)       ibat   A   struja baterije (ulaz)
//   v5      V   napon 5 V logike                                  i5     A   struja 5 V
//   vstop   V   napon posle total stopa (pada na ~0 kad je pritisnut)   istop  A   struja pogona posle total stopa
// Prag baterije: Profil `power.bat_min` (V) ako postoji, inače 11,6 V. Total stop je „pritisnut“ kad je vstop < 1 V
// dok je baterija prisutna (> 5 V). Traka i % su linearni između 10,5 i 12,9 V (približno, kao na maketi).
import { history } from '../podaci.js';
import { drawLines } from '../grafik.js';
import { none, at, num, unit, DASH } from './osnova.js';

const LO = 10.5, HI = 12.9, BAT_MIN = 11.6, STOP_V = 1;
const ORANGE = '#ffb547', DIM = '#97a3b3', TEXT = '#e6ebf1', BAR = '#20262e', RED = '#ff5c5c', GREEN = '#3ecf8e';
const FONT = 'system-ui, sans-serif', MONO = 'ui-monospace, monospace';
export const CHANNELS = [
  { name: '5 V (logika)', v: 'v5', a: 'i5', color: '#38d9f5' },
  { name: 'baterija (ulaz)', v: 'bat', a: 'ibat', color: '#ff9f43' },
  { name: 'posle total stopa', v: 'vstop', a: 'istop', color: '#f7b500' },
];

export const batMin = d => {
  const p = d && d.profile && d.profile.power;
  return p && typeof p.bat_min === 'number' ? p.bat_min : BAT_MIN;
};
export const percent = v => (v == null ? null : Math.round(100 * Math.max(0, Math.min(1, (v - LO) / (HI - LO)))));
export const stopPressed = (bat, vstop) => bat != null && bat > 5 && vstop != null && vstop < STOP_V;

function readings(d) {
  const r = { bat: at(d, 'bat') };
  for (const c of CHANNELS) { r[c.v] = at(d, c.v); r[c.a] = at(d, c.a); }
  return r;
}

const hist = (d, key) => (d.run ? history(d.run, key, d.t == null ? d.run.duration : d.t) : []);

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
    const r = readings(d);
    if (r.bat == null) return { status: 'none', text: 'još nema merenja', vals: [['baterija', DASH], ['total stop', DASH]] };
    const low = r.bat < batMin(d), pressed = stopPressed(r.bat, r.vstop);
    return { status: low ? 'warn' : 'ok', text: low ? 'baterija ispod praga' : 'radi',
      vals: [['baterija', unit(num(r.bat, 2), 'V') + ' · ≈ ' + num(percent(r.bat)) + ' %'],
        ['5 V', unit(num(r.i5, 2), 'A')], ['total stop', r.vstop == null ? DASH : pressed ? 'pritisnut' : 'otpušten']] };
  },
  draw(g, w, h, d, big) {
    const r = readings(d);
    if (r.bat == null) return;
    const bigF = big ? 56 : 26, fs = big ? 15 : 11, f = Math.max(0, Math.min(1, (r.bat - LO) / (HI - LO)));
    const txt = num(r.bat, 2) + ' V', min = batMin(d), low = r.bat < min;
    g.fillStyle = low ? RED : ORANGE; g.font = '800 ' + bigF + 'px ' + FONT; g.textAlign = 'left';
    g.fillText(txt, 8, bigF + 2);
    const tw = g.measureText(txt).width;
    g.font = 'bold ' + (big ? 18 : 13) + 'px ' + FONT; g.fillText('≈ ' + num(percent(r.bat)) + ' %', 18 + tw, bigF - (big ? 18 : 12));
    g.fillStyle = DIM; g.font = (big ? 13 : 11) + 'px ' + FONT; g.fillText('baterija', 18 + tw, bigF + 1);
    const by = bigF + 10, bw = w - 16, bh = big ? 12 : 7;
    g.fillStyle = BAR; g.fillRect(8, by, bw, bh);
    g.fillStyle = low ? RED : ORANGE; g.fillRect(8, by, bw * f, bh);
    g.fillStyle = RED; g.fillRect(8 + bw * Math.max(0, Math.min(1, (min - LO) / (HI - LO))), by - 3, 2, bh + 6);
    // Lampica „Total stop“ uz desnu ivicu iznad trake
    const pressed = stopPressed(r.bat, r.vstop), lr = big ? 8 : 6, ly = by - bigF / 2 + 4;
    g.beginPath(); g.arc(w - 8 - lr, ly, lr, 0, 7);
    g.fillStyle = r.vstop == null ? BAR : pressed ? RED : GREEN; g.fill();
    g.fillStyle = DIM; g.font = (big ? 13 : 11) + 'px ' + FONT; g.textAlign = 'right';
    g.fillText('Total stop: ' + (r.vstop == null ? DASH : pressed ? 'pritisnut' : 'otpušten'), w - 16 - 2 * lr, ly + 4);
    g.textAlign = 'left';
    // Tabela kanala: kanal | V | A, tačka u boji kanala
    const cV = big ? 230 : Math.max(130, w - 120), cA = big ? 330 : w - 10;
    const y0 = by + bh + (big ? 30 : 18), rh = big ? 40 : Math.max(14, Math.min(19, (h - y0 - 20) / 4));
    g.fillStyle = DIM; g.font = (big ? 12 : 10) + 'px ' + FONT;
    g.fillText('INA3221', 8, y0 - (big ? 12 : 6));
    g.textAlign = 'right'; g.fillText('V', cV, y0 - (big ? 12 : 6)); g.fillText('A', cA, y0 - (big ? 12 : 6)); g.textAlign = 'left';
    CHANNELS.forEach((c, i) => {
      const y = y0 + i * rh + fs * 0.4;
      g.beginPath(); g.arc(12, y - fs * 0.35, big ? 5 : 4, 0, 7); g.fillStyle = c.color; g.fill();
      g.fillStyle = TEXT; g.font = fs + 'px ' + FONT; g.fillText(c.name, 22, y);
      g.font = fs + 'px ' + MONO; g.textAlign = 'right';
      g.fillText(num(r[c.v], 2), cV, y); g.fillStyle = c.color; g.fillText(num(r[c.a], 2), cA, y); g.textAlign = 'left';
      if (big) drawLines(g, cA + 30, y - rh / 2 - 4, w - cA - 40, rh - 6, [[hist(d, c.a), c.color]], { lo: 0, hi: 3 });
    });
    if (big) {
      const cy = y0 + CHANNELS.length * rh + 16;
      if (h - cy - 6 > 30) {
        drawLines(g, 0, cy, w, h - cy - 6, [[hist(d, 'bat'), ORANGE]],
          { lo: 11, hi: 12.2, big, label: 'Napon baterije (V), poslednjih 15 s' });
      }
    }
  },
};
