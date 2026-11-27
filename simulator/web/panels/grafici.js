// Grafici (#charts, charts.js): sklopiva kartica u donjoj zoni; podrazumevano sklopljena u Taktikama.
// Grafik bez podataka se ne crta (charts.js); veličinu prati ResizeObserver u charts.js.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'grafici', title: 'Grafici', workspaces: ['taktike', 'voznja', 'snimci'], region: 'bottom', priority: 20,
  collapsible: true, open: ['voznja', 'snimci'],
  mount: el => { el.appendChild(document.getElementById('charts')); },
  shown: (el, ctx) => { if (ctx.legacy && ctx.legacy.resizeView) ctx.legacy.resizeView(); },   // i posle otvaranja kartice
});
