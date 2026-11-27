// Korak sada: ime i broj tekućeg koraka, traka do timeout-a, „traje / završen · sledeći“ (#stepnow, piše ga app.js).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'korak', title: 'Korak sada', workspaces: ['voznja', 'snimci'], region: 'side', priority: 10, open: true,
  mount: el => { el.appendChild(document.getElementById('stepnow')); },
});
