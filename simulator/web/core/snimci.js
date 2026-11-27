// Lista sačuvanih snimaka (prostor Snimci): izvor S / R / H, ishod, datum i filter. Bez DOM-a (node --test).
// Red liste dolazi sa servera (GET /api/runs?detail=1):
//   {name, date (ISO, lokalno vreme servera), engine 'sim'|'robot', lidar 'sim'|'pravi'|'snimak'|null, tactic, side,
//    mode, ok true|false|null, duration_ms, error?}

export const IZVORI = ['S', 'R', 'H'];
export const IZVOR_NAME = { S: 'simulacija', R: 'robot', H: 'hibrid (simulacija sa pravim ili snimljenim lidarom)',
  '?': 'nepoznat (fajl se ne čita)' };

// Izvor snimka: R = robot; H = simulacija sa lidarom koji nije simuliran (pravi ili iz snimka); S = simulacija;
// '?' = fajl se ne čita (server javi error).
export function izvorOf(r) {
  if (!r) return 'S';
  if (r.error) return '?';
  if (r.engine === 'robot') return 'R';
  if (r.lidar && r.lidar !== 'sim') return 'H';
  return 'S';
}

// Ishod: ok (bez greške), greška, nepoznato (robot ne javlja ishod; oštećen fajl).
export function ishodOf(r) {
  if (r && r.error) return { text: 'nečitljiv', cls: 'err', title: r.error };
  if (r && r.ok === true) return { text: 'OK', cls: 'ok', title: 'taktika je završila bez greške' };
  if (r && r.ok === false) return { text: 'greška', cls: 'err', title: 'taktika je stala sa greškom (blokiran, timeout…)' };
  return { text: '–', cls: 'dim', title: 'ishod nije poznat (snimak sa robota)' };
}

// '2026-11-27T14:05:09+01:00' -> '27.11. 14:05' (vreme kako ga je server zapisao, bez preračunavanja zone).
export function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso || '');
  return m ? `${m[3]}.${m[2]}. ${m[4]}:${m[5]}` : '';
}

export function fmtDuration(ms) {
  if (typeof ms !== 'number' || !isFinite(ms)) return '';
  return `${(ms / 1000).toFixed(1)} s`;
}

const SIDE = { zuta: 'Žuta', plava: 'Plava' };
export const sideName = s => SIDE[s] || s || '';

// Za pretragu: mala slova, bez kvačica (č -> c, ž -> z, đ -> d).
export function fold(s) {
  return String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd');
}

// Tekst po kome se traži: ime fajla, taktika, strana, režim, ishod, datum.
export function searchText(r) {
  return fold([r.name, r.tactic, r.side, sideName(r.side), r.mode, ishodOf(r).text, fmtDate(r.date)].join(' '));
}

// filter = {izvor: '' | 'S' | 'R' | 'H', text}; tekst: sve reči (razmak) moraju da se nađu.
export function filterRuns(list, { izvor = '', text = '' } = {}) {
  const words = fold(text).split(/\s+/).filter(Boolean);
  return (list || []).filter(r => (!izvor || izvorOf(r) === izvor) && words.every(w => searchText(r).includes(w)));
}

// Broj snimaka po izvoru (za dugmad filtera).
export function countByIzvor(list) {
  const out = { S: 0, R: 0, H: 0 };
  for (const r of list || []) { const k = izvorOf(r); if (k in out) out[k]++; }
  return out;
}
