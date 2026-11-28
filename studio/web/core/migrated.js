// Poruka o prenosu iz starog foldera simulator/ u studio/ (server: /api/info -> migrated = {moved, skipped}).
// null kad nema šta da se kaže. Preskočeno = ime već postoji u studio/ ili prenos nije uspeo (razlog se ne tvrdi).

const fajl = n => {
  const d = n % 10, s = n % 100;
  return `${n} ${d === 1 && s !== 11 ? 'fajl' : d >= 2 && d <= 4 && (s < 12 || s > 14) ? 'fajla' : 'fajlova'}`;
};

export function migratedNotice(m) {
  const moved = (m && m.moved) || [], skipped = (m && m.skipped) || [];
  if (!moved.length && !skipped.length) return null;
  if (!skipped.length) return `Premešteno iz starog foldera simulator/: ${fajl(moved.length)}`;
  const list = skipped.join(', ');
  return moved.length
    ? `Premešteno iz starog foldera simulator/: ${fajl(moved.length)}; ${skipped.length} nije premešteno (ostalo u simulator/): ${list}`
    : `Iz starog foldera simulator/ ništa nije premešteno; ${skipped.length} nisu premeštena (ostala u simulator/): ${list}`;
}
