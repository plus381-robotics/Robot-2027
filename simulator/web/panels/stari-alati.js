// PRELAZNO (Zadatak 4.1): stari red komandi #bar (Runs, Repo, Profile, #msg) kao red komandi prostora; 4.5–4.6 ga
// razdele na snimci-alati, poruka. Od 4.3 Taktika i Strana su zajedničke stavke (panels/stavke.js): u Taktikama su u
// taktike-alati, u Vožnji (od 4.4) u voznja-alati, a u Snimcima ovde (mesta data-slot u #bar). Kartice Simulate /
// Live / Robot i njihovi redovi su obrisani u 4.4 (red komandi Vožnja, bočna traka SIM / ROBOT).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'stari-alati', title: 'Stari alati (prelazno)', workspaces: ['taktike', 'voznja', 'snimci'], region: 'tool',
  priority: 90, open: true, shared: ['taktika', 'strana'],
  mount: el => { el.appendChild(document.getElementById('bar')); },
});
