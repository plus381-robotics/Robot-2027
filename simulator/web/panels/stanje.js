// Stanje i IR: tabela stanja (#stgrid) i IR senzori odozgo (#irPanel; u Live simulaciji klik na senzor ga
// uključi/isključi). Podrazumevano sklopljena; deli kolonu sa Koracima i Dnevnikom, sadržaj skroluje sam (shrink).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'stanje', title: 'Stanje i IR', workspaces: ['voznja', 'snimci'], region: 'side', priority: 40, open: false,
  shrink: true,
  mount: el => { el.append(document.getElementById('stgrid'), document.getElementById('irPanel')); },
});
