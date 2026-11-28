// Senzori: mali crtač grafika (linije kroz vreme). Bez DOM-a: g je 2D kontekst platna (testovi daju lažni).
//   drawLines(g, x, y, w, h, series, opt)
//     series  [[brojevi, boja, isprekidano?], ...]: svaki niz se crta zdesna (najnovija vrednost uz desnu ivicu)
//     opt     {lo?, hi?, label?, minSpan?, n?, big?}: lo / hi zadata skala; bez njih skala sama (sa malom marginom, a
//             ravan niz ne deli nulom); minSpan = najmanji raspon automatske skale; n = broj tačaka cele širine
//             (podrazumevano najduži niz); big = deblje linije i brojevi skale uz levu ivicu
//   autoScale(series, minSpan?)  {lo, hi} za dati skup nizova
export const GCOL = { grid: '#2a313c', dim: '#97a3b3', set: '#e6ebf1', act: '#4aa3ff', actR: '#3ecf8e' };

export function autoScale(series, minSpan = 0) {
  let lo = Infinity, hi = -Infinity;
  for (const s of series) for (const v of s[0]) if (Number.isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  if (lo > hi) return { lo: -1, hi: 1 };
  let span = hi - lo;
  if (span < minSpan) { const m = (lo + hi) / 2; lo = m - minSpan / 2; hi = m + minSpan / 2; span = minSpan; }
  if (!(span > 1e-9)) { const e = Math.max(Math.abs(lo) * 0.1, 1); return { lo: lo - e, hi: hi + e }; }
  return { lo: lo - span * 0.1, hi: hi + span * 0.1 };
}

const short = v => (Math.abs(v) >= 100 ? String(Math.round(v)) : String(Math.round(v * 10) / 10).replace('.', ','));

export function drawLines(g, x, y, w, h, series, opt = {}) {
  const sc = autoScale(series, opt.minSpan || 0);
  const lo = opt.lo != null ? opt.lo : sc.lo;
  let hi = opt.hi != null ? opt.hi : sc.hi;
  if (!(hi > lo)) hi = lo + 1;
  const pad = opt.big ? 34 : 4, x0 = x + pad, pw = Math.max(1, w - pad - 2);
  const n = opt.n || Math.max(2, ...series.map(s => s[0].length));
  g.strokeStyle = GCOL.grid; g.lineWidth = 1; g.strokeRect(x0, y, pw, h);
  if (lo < 0 && hi > 0) {
    const zy = y + h * hi / (hi - lo);
    g.beginPath(); g.moveTo(x0, zy); g.lineTo(x0 + pw, zy); g.stroke();
  }
  if (opt.big) {
    g.fillStyle = GCOL.dim; g.font = '11px system-ui, sans-serif';
    g.fillText(short(hi), x + 2, y + 10); g.fillText(short(lo), x + 2, y + h - 2);
  }
  for (const [arr, col, dash] of series) {
    g.strokeStyle = col; g.lineWidth = opt.big ? 2 : 1.6; g.setLineDash(dash ? [5, 4] : []);
    g.beginPath();
    let started = false;
    arr.forEach((v, i) => {
      if (!Number.isFinite(v)) { started = false; return; }
      const px = x0 + pw * (i + n - arr.length) / (n - 1), py = y + h * (hi - v) / (hi - lo);
      if (started) g.lineTo(px, py); else { g.moveTo(px, py); started = true; }
    });
    g.stroke(); g.setLineDash([]);
  }
  if (opt.label) {
    g.fillStyle = GCOL.dim; g.font = (opt.big ? 12 : 11) + 'px system-ui, sans-serif';
    g.fillText(opt.label, x0 + 6, y + 14);
  }
}
