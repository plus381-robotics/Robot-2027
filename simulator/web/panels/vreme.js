// Vreme: komande puštanja, traka koraka sa zastavicama, klizač (#timeline bez #charts — grafici su svoj panel).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'vreme', title: 'Vreme', workspaces: ['taktike', 'voznja', 'snimci'], region: 'bottom', priority: 10, open: true,
  mount: el => { el.appendChild(document.getElementById('timeline')); },
});
