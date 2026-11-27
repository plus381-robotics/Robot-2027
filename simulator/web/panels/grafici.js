// Grafici (#charts, charts.js): sklopiva kartica u donjoj zoni; podrazumevano sklopljena svuda (spec: grafici
// sklopljeni; na 768 px otvoreni grafici ostavljaju listi Snimaka 3–4 reda), osim u Snimcima dok se snimak poredi
// sa referencom (store.refLabel). Kad je korisnik jednom otvori/sklopi u nekom prostoru, važi njegov izbor.
// Grafik bez podataka se ne crta (charts.js); veličinu prati ResizeObserver u charts.js.
import { registerPanel } from '../core/panels.js';

export const graficiOpen = (ws, st) => ws === 'snimci' && !!(st && st.refLabel);

registerPanel({
  id: 'grafici', title: 'Grafici', workspaces: ['taktike', 'voznja', 'snimci'], region: 'bottom', priority: 20,
  collapsible: true, open: graficiOpen,
  mount: el => { el.appendChild(document.getElementById('charts')); },
  shown: (el, ctx) => { if (ctx.legacy && ctx.legacy.resizeView) ctx.legacy.resizeView(); },   // i posle otvaranja kartice
});
