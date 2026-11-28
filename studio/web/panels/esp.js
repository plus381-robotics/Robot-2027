// ESP (Zadatak 4.4): pravi ekran robota (OLED 128x64) i njegovi tasteri (enkoder, BACK, OK, STOP), web/esp.js. Kartica
// se vidi samo kad izvor ima ekran: sesija sa mogućnošću esp_screen (Live), a bez sesije uz SIM (snimljen ekran
// tekućeg snimka, tasteri ugašeni). Uz pravog robota je nema (robot ne šalje ekran). STOP ovde je taster robota u
// simuliranom ESP-u (ostaje); STOP za sesiju je na traci i Esc.
import { registerPanel } from '../core/panels.js';
import { espShown } from '../core/voznja.js';

registerPanel({
  id: 'esp', title: 'ESP', workspaces: ['voznja'], region: 'side', priority: 5, open: true, when: espShown,
  mount: el => { el.appendChild(document.getElementById('espPanel')); },
});
