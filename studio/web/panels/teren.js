// Teren: sto (FieldView), legenda, alatke stola, „Prikaz ▾“; za sada i protivnici/kamenolomi/scenariji, poređenje,
// ESP i kartica rezultata (sve što je u #viewwrap, dok ne pređu u svoje panele). Posle svakog prikaza sto se ponovo meri.
import { registerPanel } from '../core/panels.js';
import { refTagView } from '../core/snimci.js';

registerPanel({
  id: 'teren', title: 'Teren', workspaces: ['taktike', 'voznja', 'snimci'], region: 'main', priority: 20, open: true,
  mount: (el, ctx) => {
    el.appendChild(document.getElementById('viewwrap'));
    // Oznaka reference na stolu (van Snimaka): store.refLabel (app.js setRef); klik na ime = Snimci, ✕ = ukloni.
    const tag = document.getElementById('refTag'), name = document.getElementById('refTagName');
    name.onclick = () => ctx.go('snimci');
    document.getElementById('refTagClear').onclick = () => ctx.legacy.clearRef();
    const render = st => {
      const v = refTagView(st.refLabel, st.ws);
      tag.hidden = !v;
      if (v) { name.textContent = v.text; tag.title = v.title; }
    };
    ctx.store.subscribe((st, prev) => { if (st.refLabel !== prev.refLabel || st.ws !== prev.ws) render(st); });
    render(ctx.store.get());
  },
  shown: (el, ctx) => { if (ctx.legacy && ctx.legacy.resizeView) ctx.legacy.resizeView(); },    // odmah (i u pozadinskom tabu)
});
