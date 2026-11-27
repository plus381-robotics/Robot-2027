// Koraci: tabela koraka (#steps; klik = skok na trenutak koraka). Kartica popunjava kolonu, tabela skroluje sama.
// Broj na kartici (broj koraka) postavlja app.js (renderSteps -> setBadge('koraci', n)).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'koraci', title: 'Koraci', workspaces: ['taktike', 'voznja', 'snimci'], region: 'side', priority: 20, open: true,
  grow: true,
  mount: el => { el.appendChild(document.getElementById('steps')); },
});
