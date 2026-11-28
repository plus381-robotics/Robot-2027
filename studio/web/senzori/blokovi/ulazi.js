// Blok „Činč i tasteri“ (donji red): lampice činč, STOP, OK, NAZAD i enkoder menija. Robot će slati `btn` (ESP ga još ne šalje;
// kad stigne kao {cinc, stop, ok, nazad, enk}, lampice ga čitaju); u simulaciji je izvor stanje meča (simFields ['mec']):
// činč umetnut dok je meč naoružan i čeka (RESET, NAORUZAN), izvučen od poze nadalje (POZA, MEC, KRAJ ili `match` postoji);
// STOP, OK, NAZAD i enkoder menija se ne simuliraju („—“). Na ROBOTU nema izvora (razlog iz izvor.js).
import { none, ok, at, DASH } from './osnova.js';
import { matchInfo } from './mec.js';

const GREEN = '#3ecf8e', DIM = '#97a3b3', TEXT = '#e6ebf1', BAR = '#20262e';
const FONT = 'system-ui, sans-serif';

// {cinc: true|false|null, stop, ok, nazad: true|false|null, enk: broj|null}; null = nepoznato („—“)
export function inputsOf(d) {
  const btn = at(d, 'btn');
  if (btn && typeof btn === 'object') {
    const b = k => (btn[k] == null ? null : !!btn[k]);
    return { cinc: b('cinc'), stop: b('stop'), ok: b('ok'), nazad: b('nazad'), enk: btn.enk == null ? null : Number(btn.enk) };
  }
  const m = matchInfo(d);
  let cinc = null;
  if (m.ms != null || ['POZA', 'MEC', 'KRAJ'].includes(m.state)) cinc = false;
  else if (m.state === 'RESET' || m.state === 'NAORUZAN') cinc = true;
  return { cinc, stop: null, ok: null, nazad: null, enk: null };
}

const cincText = c => (c == null ? DASH : c ? 'umetnut' : 'izvučen');

export default {
  id: 'ulazi', name: 'Činč i tasteri', slot: 'bottom', part: null, fields: ['btn'], simFields: ['mec'],
  hints: [
    'Izvuci i vrati činč: lampica se gasi i pali.',
    'Pritisni STOP, OK, NAZAD i okreni enkoder menija: svaka promena se vidi.',
  ],
  view(d) {
    if (!d.src) return none();
    const i = inputsOf(d), tx = c => (c == null ? DASH : c ? 'pritisnut' : 'otpušten');
    return ok([['činč', cincText(i.cinc)], ['STOP', tx(i.stop)], ['OK', tx(i.ok)], ['NAZAD', tx(i.nazad)],
      ['enkoder', i.enk == null ? DASH : 'poz. ' + i.enk]]);
  },
  draw(g, w, h, d, big) {
    const i = inputsOf(d);
    const items = [['Činč', i.cinc, cincText(i.cinc)], ['STOP', i.stop], ['OK', i.ok], ['NAZAD', i.nazad],
      ['Enkoder', i.enk == null ? null : true, i.enk == null ? DASH : 'poz. ' + i.enk]];
    const cw = w / items.length;
    items.forEach(([n, on, sub], k) => {
      const x = cw * k + cw / 2, y = h / 2 - (big ? 20 : 8), r = big ? 22 : 13;
      g.beginPath(); g.arc(x, y, r, 0, 7); g.fillStyle = on ? GREEN : BAR; g.fill();
      g.strokeStyle = on ? 'transparent' : '#556070'; g.stroke();
      g.textAlign = 'center'; g.fillStyle = TEXT; g.font = (big ? 15 : 12) + 'px ' + FONT; g.fillText(n, x, y + r + (big ? 22 : 16));
      g.fillStyle = DIM; g.font = (big ? 13 : 11) + 'px ' + FONT;
      g.fillText(sub || (on == null ? DASH : on ? 'pritisnut' : 'otpušten'), x, y + r + (big ? 40 : 29));
      g.textAlign = 'left';
    });
  },
};
