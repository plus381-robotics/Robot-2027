// Teren: sto (FieldView), legenda, alatke stola, „Prikaz ▾“; za sada i protivnici/kamenolomi/scenariji, poređenje,
// ESP i kartica rezultata (sve što je u #viewwrap, dok ne pređu u svoje panele). Posle svakog prikaza sto se ponovo meri.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'teren', title: 'Teren', workspaces: ['taktike', 'voznja', 'snimci'], region: 'main', priority: 20, open: true,
  mount: el => { el.appendChild(document.getElementById('viewwrap')); },
  shown: (el, ctx) => { if (ctx.legacy && ctx.legacy.resizeView) ctx.legacy.resizeView(); },    // odmah (i u pozadinskom tabu)
});
