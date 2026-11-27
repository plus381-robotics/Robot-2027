// PRELAZNO (Zadatak 4.1): stari red komandi #bar (Tactic/Side/Editor, Simulate/Live/Robot, Runs, Repo, Profile, #msg)
// kao red komandi prostora. Sadržaj se ne menja; 4.2–4.5 ga razdele na taktike-alati, voznja-alati, snimci-alati, poruka.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'stari-alati', title: 'Stari alati (prelazno)', workspaces: ['taktike', 'voznja', 'snimci'], region: 'tool',
  priority: 90, open: true,
  mount: el => { el.appendChild(document.getElementById('bar')); },
});
