// Dnevnik: „ESP↔STM32 poruke“ i „samo greške“ (#logTools) + redovi dnevnika (#log; klik = skok na trenutak).
// Koji redovi se vide određuje core/log.js (logLines), crta ih app.js (renderLog); broj na kartici = broj redova
// grešaka (setBadge iz app.js). U Taktikama podrazumevano sklopljen.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'dnevnik', title: 'Dnevnik', workspaces: ['taktike', 'voznja', 'snimci'], region: 'side', priority: 30,
  open: ['voznja'], grow: true,        // u Snimcima sklopljen: mesto za listu snimaka (4.5)
  mount: el => { el.append(document.getElementById('logTools'), document.getElementById('log')); },
});
