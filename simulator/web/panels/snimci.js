// Snimci (Zadatak 4.5): lista sačuvanih snimaka (simulator/runs/) — red: izvor S / R / H, taktika, strana, ime, datum,
// ishod (ostalo u title); filter po izvoru i tekstu; klik = učitaj (app.js loadRun, isti put kao stari „Load run…“); snimak
// koji se gleda je istaknut, referenca ima 📌; dok sesija radi redovi su prigušeni, a klik odbija loadRun (core/snimci.js
// sessionLock). Podaci: store.runs (GET /api/runs?detail=1, app.js refreshRuns), store.runName (učitan sačuvan snimak),
// store.refName (sačuvan snimak koji je referenca), store.session. Logika liste: core/snimci.js.
import { registerPanel } from '../core/panels.js';
import { IZVORI, IZVOR_NAME, izvorOf, ishodOf, fmtDate, fmtDuration, sideName, filterRuns, countByIzvor, sessionLock }
  from '../core/snimci.js';
import { esc } from '../core/api.js';

registerPanel({
  id: 'snimci', title: 'Snimci', workspaces: ['snimci'], region: 'side', priority: 5, open: true, grow: true,
  mount: (el, ctx) => {
    el.innerHTML = `<div class="sn-tools">
        <span class="seg" id="snSrc" role="group" title="Filter po izvoru">
          <button type="button" data-v="" class="on" title="svi snimci">svi</button>
          ${IZVORI.map(k => `<button type="button" data-v="${k}" title="${IZVOR_NAME[k]}">${k}<small></small></button>`).join('')}
        </span>
        <input id="snFind" type="search" placeholder="traži: ime, taktika, strana…" title="Traži po imenu, taktici, strani, režimu, ishodu, datumu (sve reči)">
      </div>
      <div id="snList" role="list"></div>
      <div id="snEmpty" class="sn-empty"></div>`;
    const list = el.querySelector('#snList'), empty = el.querySelector('#snEmpty'), find = el.querySelector('#snFind');
    const filter = { izvor: '', text: '' };
    let last = null;

    const render = () => {
      const st = ctx.store.get(), all = st.runs || [];
      const counts = countByIzvor(all);
      for (const b of el.querySelectorAll('#snSrc button')) {
        b.classList.toggle('on', b.dataset.v === filter.izvor);
        b.setAttribute('aria-pressed', b.dataset.v === filter.izvor ? 'true' : 'false');
        if (b.dataset.v) b.querySelector('small').textContent = counts[b.dataset.v] || '';
      }
      const rows = filterRuns(all, filter), lock = sessionLock(st.session);
      list.classList.toggle('locked', !!lock);          // sesija radi: redovi prigušeni, klik odbija app.js loadRun
      list.innerHTML = rows.map(r => {
        const iz = izvorOf(r), is = ishodOf(r);
        const cur = r.name === st.runName, isRef = r.name === st.refName;
        const tac = r.tactic ? esc(r.tactic) : '<span class="dim">?</span>';
        const side = r.side ? `<span class="sn-dot ${esc(r.side)}" title="${esc(sideName(r.side))}"></span>` : '';
        const title = `${r.name}\n${IZVOR_NAME[iz]} · ${r.tactic || '?'} · ${sideName(r.side)} · ${r.mode || ''} · ${is.text}` +
          `\n${r.date || ''}${r.duration_ms != null ? ' · ' + fmtDuration(r.duration_ms) : ''}` +
          `${cur ? '\n(učitan)' : ''}${isRef ? '\n(referenca)' : ''}${lock ? '\n' + lock.load : ''}`;
        return `<button type="button" role="listitem" class="sn-row${cur ? ' cur' : ''}" data-name="${esc(r.name)}"` +
          `${cur ? ' aria-current="true"' : ''} title="${esc(title)}">` +
          `<span class="sn-src ${iz === '?' ? 'U' : iz}">${iz}</span>` +
          `<span class="sn-t">${isRef ? '📌 ' : ''}${tac}${side}<span class="sn-n">${esc(r.name)}</span></span>` +
          `<span class="sn-date">${esc(fmtDate(r.date))}</span>` +
          `<span class="sn-ok ${is.cls}" title="${esc(is.title)}">${esc(is.text)}</span></button>`;
      }).join('');
      empty.textContent = st.runs == null ? 'učitavam listu…'
        : !all.length ? 'nema sačuvanih snimaka: pokreni simulaciju ili sesiju, pa „Sačuvaj snimak…“'
          : !rows.length ? 'nijedan snimak ne odgovara filteru' : '';
      empty.hidden = !empty.textContent;
      ctx.setBadge('snimci', st.runs ? all.length : '');
      const c = list.querySelector('.sn-row.cur');
      if (c && st.runName !== last) c.scrollIntoView({ block: 'nearest' });
      last = st.runName;
    };

    el.querySelector('#snSrc').onclick = e => {
      const b = e.target.closest('button');
      if (!b) return;
      filter.izvor = b.dataset.v;
      render();
    };
    find.oninput = () => { filter.text = find.value; render(); };
    list.onclick = e => {
      const b = e.target.closest('.sn-row');
      if (b) ctx.legacy.loadRun(b.dataset.name);
    };
    ctx.store.subscribe((st, prev) => {
      if (st.runs !== prev.runs || st.runName !== prev.runName || st.refName !== prev.refName ||
        !st.session !== !prev.session) render();
    });
    render();
  },
});
