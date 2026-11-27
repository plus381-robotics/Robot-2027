// PRELAZNO (Zadatak 4.1): stari red komandi #bar (Simulate/Live/Robot, Runs, Repo, Profile, #msg) kao red komandi
// prostora; 4.4–4.6 ga razdele na voznja-alati, snimci-alati, poruka. Od 4.3 Taktika i Strana su zajedničke stavke
// (panels/stavke.js): u Taktikama su u taktike-alati, a u Vožnji i Snimcima ovde (mesta data-slot u #bar), dok
// Vožnja ne dobije svoj red (4.4).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'stari-alati', title: 'Stari alati (prelazno)', workspaces: ['taktike', 'voznja', 'snimci'], region: 'tool',
  priority: 90, open: true, shared: ['taktika', 'strana'],
  mount: el => { el.appendChild(document.getElementById('bar')); },
});
