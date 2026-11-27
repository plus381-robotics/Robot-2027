// PRELAZNO (Zadatak 4.1): stari red komandi #bar (Repo, Profile, #msg + dugme uz poruku #msgAct) kao red komandi
// prostora; 4.6 ga razdeli (poruka). Meni „⋯ Runs“ je od 4.5 prostor Snimci (snimci-alati, kartica snimci).
// Od 4.3 Taktika i Strana su zajedničke stavke (panels/stavke.js): u Taktikama su u taktike-alati, u Vožnji (od 4.4)
// u voznja-alati, a u Snimcima ovde (mesta data-slot u #bar). Kartice Simulate /
// Live / Robot i njihovi redovi su obrisani u 4.4 (red komandi Vožnja, bočna traka SIM / ROBOT).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'stari-alati', title: 'Stari alati (prelazno)', workspaces: ['taktike', 'voznja', 'snimci'], region: 'tool',
  priority: 90, open: true, shared: ['taktika', 'strana'],
  mount: el => { el.appendChild(document.getElementById('bar')); },
});
