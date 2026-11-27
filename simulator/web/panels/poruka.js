// Poruka (Zadatak 4.6; ranije #msg u starom redu #bar): desni kraj reda komandi u SVAKOM prostoru, i u Test dela.
// app.js msg(text, err, act) piše u #msg (greška crveno, ceo tekst u title) i, kad ima akciju, pokazuje dugme
// #msgAct uz nju (npr. „Otvori u Snimcima“ posle kraja sesije); sledeća poruka ga sklanja.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'poruka', title: 'Poruka', workspaces: ['taktike', 'test', 'voznja', 'snimci'], region: 'tool', priority: 95, open: true,
  mount: el => {
    el.className += ' tool-row';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.append(document.getElementById('msg'), document.getElementById('msgAct'));
  },
});
