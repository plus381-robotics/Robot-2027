// Postavka stola (Zadatak 4.4): + Protivnik, + PAMI, scenario (učitaj / sačuvaj), Resetuj sto, „elementi igre“ (ranije
// u Prikaz ▾), a ispod uređivači izabranog protivnika (#oppEdit) i kamenoloma (#elEdit), ranije plutajući nad stolom.
// U Taktikama i u Vožnji samo uz SIM (core/voznja.js stoShown); podrazumevano sklopljena — klik na protivnika ili
// kamenolom na stolu je otvara (app.js). Ponašanje ostaje u app.js preko istih id-jeva.
import { registerPanel } from '../core/panels.js';
import { stoShown } from '../core/voznja.js';

registerPanel({
  id: 'sto', title: 'Postavka stola', workspaces: ['taktike', 'voznja'], region: 'side', priority: 25, open: false,
  when: stoShown,
  mount: el => {
    const $ = id => document.getElementById(id);
    el.append($('stoTools'), $('oppEdit'), $('elEdit'));
  },
});
