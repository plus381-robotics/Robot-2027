// Poruka o prenosu iz starog foldera simulator/ u studio/ (server: /api/info -> migrated = {moved, skipped}).
// null kad nema šta da se kaže. Preskočeno = ime već postoji u studio/ ili prenos nije uspeo (razlog se ovde ne tvrdi;
// server ga piše u konzolu). Broj se slaže sa imenicom i glagolom: 1 fajl nije premešten, 2–4 fajla nisu premeštena,
// 5+ (i 11–14) fajlova nije premešteno.
//   notMoved(n) -> npr. '2 fajla nisu premeštena (ostala u simulator/)'

const form = n => {                                        // 'one' | 'few' | 'many' (srpski: 1, 2–4, ostalo; 11–14 = many)
  const d = n % 10, s = n % 100;
  return d === 1 && s !== 11 ? 'one' : d >= 2 && d <= 4 && (s < 12 || s > 14) ? 'few' : 'many';
};
const FAJL = { one: 'fajl', few: 'fajla', many: 'fajlova' };
const NOT_MOVED = { one: 'nije premešten (ostao u simulator/)', few: 'nisu premeštena (ostala u simulator/)',
  many: 'nije premešteno (ostalo u simulator/)' };

const fajl = n => `${n} ${FAJL[form(n)]}`;
export const notMoved = n => `${fajl(n)} ${NOT_MOVED[form(n)]}`;

export function migratedNotice(m) {
  const moved = (m && m.moved) || [], skipped = (m && m.skipped) || [];
  if (!moved.length && !skipped.length) return null;
  if (!skipped.length) return `Premešteno iz starog foldera simulator/: ${fajl(moved.length)}`;
  const list = skipped.join(', ');
  return moved.length
    ? `Premešteno iz starog foldera simulator/: ${fajl(moved.length)}; ${notMoved(skipped.length)}: ${list}`
    : `Iz starog foldera simulator/ ništa nije premešteno; ${notMoved(skipped.length)}: ${list}`;
}
