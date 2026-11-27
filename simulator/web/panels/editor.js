// Editor taktike (#editorPane, kakav jeste): otvara ga i zatvara stari kod (✎ Editor, prostor Taktike); dok je zatvoren
// panel ne zauzima mesto (klasa ed-closed prati atribut hidden na #editorPane).
// Prelazno i u Vožnji i Snimcima (kao do sada: vidi se gde god je otvoren), jer je dugme ✎ Editor još u starom
// redu komandi u svim prostorima; kad ono pređe u taktike-alati (4.2), editor ostaje samo u Taktikama.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'editor', title: 'Editor', workspaces: ['taktike', 'voznja', 'snimci'], region: 'main', priority: 10, open: true,
  mount: (el, ctx) => {
    const pane = document.getElementById('editorPane');
    el.appendChild(pane);
    const sync = () => el.classList.toggle('ed-closed', pane.hidden);
    new MutationObserver(() => {                       // otvoren/zatvoren: sto pored njega menja širinu
      sync();
      if (ctx.legacy && ctx.legacy.resizeView) ctx.legacy.resizeView();
    }).observe(pane, { attributes: true, attributeFilter: ['hidden'] });
    sync();
  },
});
