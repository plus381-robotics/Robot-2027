// Editor taktike (#editorPane): samo u Taktikama. Otvara ga prostor Taktike (bočna traka) ili „✎ Editor“ u redu
// komandi, zatvara „×“ u traci editora (sto tada dobija celu širinu). Dok je zatvoren panel ne zauzima mesto (klasa
// ed-closed prati atribut hidden na #editorPane). U drugom prostoru panel je samo SKRIVEN (isti CodeMirror, tekst i
// nesačuvane izmene ostaju), ne uništava se. Dole kartice Problemi i Komande (Gambit Micro, ranije fioka nad stolom).
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'editor', title: 'Editor', workspaces: ['taktike'], region: 'main', priority: 10, open: true,
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
