// PRELAZNO (Zadatak 4.1): stara desna kolona #side-panel (State + IR + korak sada, Steps, Log) kao jedna kartica.
// Sadržaj se ne menja; 4.2–4.6 ga razdele na korak, koraci, dnevnik, stanje.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'stari-paneli', title: 'Stari paneli (prelazno)', workspaces: ['taktike', 'voznja', 'snimci'], region: 'side',
  priority: 90, open: true, grow: true,
  mount: el => { el.appendChild(document.getElementById('side-panel')); },
});
