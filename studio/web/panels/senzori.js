// Senzori (Zadatak 7): pregled svih senzora robota po maketi B i detalj bloka na klik. Dva panela:
//   senzori-alati (red komandi)  „Senzori“ (u detalju „← Svi senzori“: sensOpen = null) · šta se prikazuje
//                                (senzori/izvor.js viewMode, u boji izvora) · bez veze dugme „Poveži robota“
//                                (ctx.openConnect) · dok se prikazuje pušten snimak dugme „Uživo“ (događaj senzori-uzivo,
//                                sluša ga app.js: stop puštanja, sens.replay = false) · desno brojač „● n radi · ● n upozorenja · ○ n bez podataka“.
//                                U detalju lidara (posle njega idu lidar-alati): „← Svi senzori“, lampica, ime i oznaka
//                                izvora (SNIMAK dok detalj lidara pušta snimak krugova, store.lidarSrc).
//   senzori (glavni region)      mreža blokova (senzori/blokovi/, mesto po slot-u: top · sketch · right · bottom) ili
//                                detalj jednog bloka: veliki prikaz + kartice Vrednosti, Šta fali, Kako proveriti,
//                                Izvor. Nema ga u detalju lidara: tada su tu postojeći paneli lidara (panels/lidar.js).
// Klik (ili Enter) na pločicu: store.sensOpen = id bloka (lidar: postojeći paneli). Esc i dalje znači samo STOP.
// Podaci: store.sens (app.js bridgeSens: run, t u ms), session, lidarScan, profile...; oznaka izvora po bloku iz
// blockSource (senzori/blokovi/index.js evalBlocks; d.ctx = ctx panela za dugmad bloka, d.redraw = schedule kad blok
// dobije odgovor servera, npr. grupe lidara). Crta se najviše 10 puta u sekundi (setTimeout + rAF) i samo dok
// je izabran prostor Senzori; HTML se pravi iznova samo kad se promeni izvor nekog bloka ili otvoreni detalj, inače se
// menjaju samo lampice, tekstovi, dugmad bloka i platna.
import { registerPanel } from '../core/panels.js';
import { esc } from '../core/api.js';
import { viewMode } from '../senzori/izvor.js';
import { BLOCKS, SLOTS, evalBlocks, counts, warnWord } from '../senzori/blokovi/index.js';

const MIN_MS = 100;                                  // najviše 10 crtanja u sekundi
const BADGE = { pravo: 'PRAVO', sim: 'SIM', snimak: 'SNIMAK' };
const BADGE_TITLE = { pravo: 'Podatak stiže sa robota', sim: 'Podatak je iz simulacije (nije pravi robot)',
  snimak: 'Podatak je iz snimka' };
const LAMP_TITLE = { ok: 'radi', warn: 'upozorenje', none: 'bez podataka' };
const FIELD_NAME = { '@lidar': 'krugovi lidara' };

const R = { ctx: null, tool: null, main: null, pending: false, last: -Infinity, sig: null, refs: {}, logged: new Set() };

const blockOf = id => BLOCKS.find(b => b.id === id) || null;
const detailId = st => (st.sensOpen && st.sensOpen !== 'lidar' && blockOf(st.sensOpen) ? st.sensOpen : null);
const setText = (el, t) => { if (el.textContent !== t) el.textContent = t; };
const setHTML = (el, h) => { if (el._h !== h) { el._h = h; el.innerHTML = h; } };
const setCls = (el, c) => { if (el.className !== c) el.className = c; };
const setTitle = (el, t) => { if (el.title !== t) el.title = t; };

function badgeHTML(src) {
  return `<span class="sz-badge ${src || 'none'}" title="${esc(src ? BADGE_TITLE[src] : 'Nema podataka za ovaj blok')}">`
    + `${src ? BADGE[src] : 'nepovezano'}</span>`;
}

// ---------------- osvežavanje (najviše 10 Hz, samo u Senzorima) ----------------

function schedule() {
  if (R.pending || !R.ctx || R.ctx.store.get().ws !== 'senzori') return;
  R.pending = true;
  setTimeout(() => requestAnimationFrame(render), Math.max(0, MIN_MS - (performance.now() - R.last)));
}

function render() {
  R.pending = false;
  const st = R.ctx.store.get();
  if (st.ws !== 'senzori') return;
  R.last = performance.now();
  const list = evalBlocks(st, BLOCKS, { ctx: R.ctx, redraw: schedule });   // d.ctx: dugmad bloka; d.redraw: odgovor servera
  for (const x of list) {
    if (x.v.error && !R.logged.has(x.b.id)) { R.logged.add(x.b.id); console.error('Senzori, blok ' + x.b.id, x.v.error); }
  }
  renderTool(st, list);
  if (st.sensOpen !== 'lidar') renderMain(st, list);
}

function start(ctx) {
  if (R.ctx) return;
  R.ctx = ctx;
  ctx.store.subscribe(st => { if (st.ws === 'senzori') schedule(); });
}

// ---------------- red komandi ----------------

function mountTool(el, ctx) {
  start(ctx);
  el.className += ' tool-row';
  el.innerHTML = `<button type="button" class="sz-back" hidden title="Nazad na pregled svih senzora">← Svi senzori</button>
    <b class="sz-title">Senzori</b>
    <span class="sz-cur" hidden><span class="sz-lamp none"></span><b class="sz-cur-name"></b><span class="sz-badge none"></span></span>
    <span class="sz-showing"></span>
    <button type="button" class="sz-live" hidden title="Nazad na uživo: prekida puštanje snimka">Uživo</button>
    <button type="button" class="primary sz-connect" hidden aria-haspopup="dialog"
      title="Poveži se sa pravim ili virtuelnim robotom (host, lozinka)">Poveži robota</button>
    <span class="sz-grow"></span>
    <span class="sz-count" title="Blokovi: radi · upozorenje · bez podataka"></span>`;
  const q = s => el.querySelector(s);
  R.tool = { root: el, back: q('.sz-back'), title: q('.sz-title'), cur: q('.sz-cur'), curLamp: q('.sz-cur .sz-lamp'),
    curName: q('.sz-cur-name'), curBadge: q('.sz-cur .sz-badge'), showing: q('.sz-showing'), live: q('.sz-live'), connect: q('.sz-connect'),
    count: q('.sz-count') };
  R.tool.back.onclick = () => ctx.store.set({ sensOpen: null });
  R.tool.live.onclick = () => document.dispatchEvent(new CustomEvent('senzori-uzivo'));   // app.js: stani i vrati se uživo
  R.tool.connect.onclick = () => ctx.openConnect && ctx.openConnect(R.tool.connect);   // dok sesija radi: poruka
}

function renderTool(st, list) {
  const T = R.tool;
  if (!T) return;
  const open = st.sensOpen || null, inLidar = open === 'lidar', vm = viewMode(st);
  T.back.hidden = !open;
  T.title.hidden = !!open;
  T.root.classList.toggle('sz-in-lidar', inLidar);
  T.cur.hidden = !inLidar;
  if (inLidar) {
    const x = list.find(y => y.b.id === 'lidar'), file = st.lidarSrc === 'snimak';
    const src = file ? 'snimak' : x.s.src, status = file ? 'ok' : x.v.status;
    setCls(T.curLamp, 'sz-lamp ' + status);
    setTitle(T.curLamp, LAMP_TITLE[status] || '');
    setText(T.curName, x.b.name);
    setCls(T.curBadge, 'sz-badge ' + (src || 'none'));
    setText(T.curBadge, src ? BADGE[src] : 'nepovezano');
    setTitle(T.curBadge, file ? 'Detalj lidara pušta snimak krugova (studio/lidar/)' : x.s.src ? vm.text : x.s.reason || '');
  }
  T.showing.hidden = inLidar;
  const virt = vm.mode === 'robot' && st.session && st.session.virtual;      // virtuelni robot: boja simulacije, ne robota
  setCls(T.showing, 'sz-showing m-' + (virt ? 'sim' : vm.mode));
  setText(T.showing, vm.text);
  setTitle(T.showing, vm.text);
  T.live.hidden = vm.mode !== 'snimak';
  T.connect.hidden = vm.mode !== 'nista';
  T.count.hidden = inLidar;
  if (!inLidar) {
    const c = counts(list);
    setHTML(T.count, `<span class="ok">●</span> ${c.ok} radi · <span class="warn">●</span> ${c.warn} ${warnWord(c.warn)}`
      + ` · <span class="none">○</span> ${c.none} bez podataka`);
  }
}

// ---------------- mreža blokova i detalj ----------------

function mountMain(el, ctx) {
  start(ctx);
  R.main = el;
  el.addEventListener('click', e => {
    if (e.target.closest('button')) return;                    // dugmad bloka (actions) imaju svoj onclick
    const t = e.target.closest('[data-open]');
    if (t) ctx.store.set({ sensOpen: t.dataset.open });
  });
  el.addEventListener('keydown', e => {
    if ((e.key !== 'Enter' && e.key !== ' ') || e.target.closest('button')) return;
    const t = e.target.closest('[data-open]');
    if (t) { e.preventDefault(); ctx.store.set({ sensOpen: t.dataset.open }); }
  });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => schedule()).observe(el);
}

// Telo pločice ili detalja: razlog kad nema izvora, inače platno (draw), HTML bloka (html) ili krupne vrednosti. Blok sa
// oba (npr. skica robota + lista senzora): u detalju platno i pored njega HTML, u pločici samo platno.
function bodyHTML(x, big) {
  if (!x.s.src) return `<div class="sz-why"><b>${esc(x.s.reason || 'nepovezano')}</b></div>`;
  if (x.b.draw && x.b.html && big) return '<div class="sz-dsplit"><div class="sz-dcv"><canvas></canvas></div><div class="sz-html"></div></div>';
  if (x.b.draw) return '<canvas></canvas>';
  if (x.b.html) return '<div class="sz-html"></div>';
  return '<div class="sz-big"></div>';
}

function tileHTML(x) {
  const b = x.b;
  return `<div class="sz-tile${x.s.src ? '' : ' none'}" data-open="${esc(b.id)}" data-id="${esc(b.id)}" role="button"
      tabindex="0" title="${esc(b.name)}: klik za detalj">
    <div class="sz-th"><span class="sz-lamp none"></span><b>${esc(b.name)}</b>${badgeHTML(x.s.src)}<span class="sz-acts"></span></div>
    <div class="sz-body">${bodyHTML(x)}</div>
    <div class="sz-vals"></div></div>`;
}

function sourceText(x, st) {
  const s = st.session, src = x.s.src;
  if (src === 'pravo') return s && s.kind !== 'robot' ? 'Pravi lidar (hibrid: ostalo je simulirano)' : 'Pravi robot (telemetrija ESP-a)';
  if (src === 'sim' && s && s.kind === 'robot') return 'Virtuelni robot (pravi ESP kod nad simuliranim STM32-jem): ovo nije pravi robot';
  if (src === 'sim') return 'Simulacija (Vožnja SIM): ovo nije pravi robot';
  if (src === 'snimak') return 'Snimak' + (st.sens && st.sens.name ? ' ' + st.sens.name : '');
  return 'nema podataka';
}

function detailHTML(x, st) {
  const b = x.b, need = x.s.src ? x.s.note : x.s.reason;
  const simLike = x.s.src === 'sim' && !(st.session && st.session.kind === 'robot');    // virtuelni robot: polja kao robot
  const fields = (simLike && b.simFields ? b.simFields : b.fields || []).map(f => FIELD_NAME[f] || f);
  return `<div class="sz-detail" data-id="${esc(b.id)}">
    <div class="sz-dh"><span class="sz-lamp none"></span><h3>${esc(b.name)}</h3>${badgeHTML(x.s.src)}
      <span class="sz-state dim"></span><span class="sz-grow"></span><span class="sz-acts"></span></div>
    <div class="sz-dbody">
      <div class="sz-dviz">${bodyHTML(x, true)}</div>
      <div class="sz-dside">
        <section class="sz-card"><h5>Vrednosti</h5><table class="sz-vt"></table></section>
        ${need ? `<section class="sz-card need"><h5>Šta fali</h5><p>${esc(need)}</p></section>` : ''}
        <section class="sz-card"><h5>Kako proveriti</h5><ol>${b.hints.map(h => `<li>${esc(h)}</li>`).join('')}</ol></section>
        <section class="sz-card"><h5>Izvor</h5><p>${esc(sourceText(x, st))}</p>
          <p class="dim">polja: ${esc(fields.join(', ') || 'nijedno (stanje sesije)')}</p></section>
      </div>
    </div></div>`;
}

function refsOf(root) {
  const q = s => root.querySelector(s);
  return { root, lamp: q('.sz-lamp'), acts: q('.sz-acts'), state: q('.sz-state'), canvas: q('canvas'), big: q('.sz-big'),
    html: q('.sz-html'), vals: q('.sz-vals'), table: q('.sz-vt'), actList: [], actSig: null };
}

function build(open, list, st) {
  R.refs = {};
  if (open) {
    const x = list.find(y => y.b.id === open);
    R.main.innerHTML = detailHTML(x, st);
    R.refs[open] = refsOf(R.main.firstElementChild);
    return;
  }
  const slot = {};
  for (const s of SLOTS) slot[s] = [];
  for (const x of list) (slot[x.b.slot] || slot.bottom).push(tileHTML(x));
  R.main.innerHTML = `<div class="sz-grid">${SLOTS.map(s => `<div class="sz-slot sz-slot-${s}">${slot[s].join('')}</div>`).join('')}</div>`;
  for (const x of list) R.refs[x.b.id] = refsOf(R.main.querySelector(`.sz-tile[data-id="${x.b.id}"]`));
}

function renderMain(st, list) {
  if (!R.main) return;
  const open = detailId(st);
  const sig = JSON.stringify([open, viewMode(st).mode, list.map(x => [x.b.id, x.s.src, x.s.reason, x.s.note])]);
  if (sig !== R.sig) { R.sig = sig; build(open, list, st); }
  for (const x of list) {
    const r = R.refs[x.b.id];
    if (r) update(r, x, !!open);
  }
}

function valsHTML(vals, big) {
  if (big) return vals.map(([k, v]) => `<span><small>${esc(k)}</small><b>${esc(v)}</b></span>`).join('');
  return vals.map(([k, v]) => `<span>${esc(k)} <b>${esc(v)}</b></span>`).join('');
}

function fit(cv) {
  const box = cv.parentElement.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  const w = Math.max(10, Math.floor(box.width)), h = Math.max(10, Math.floor(box.height));
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    cv.style.width = w + 'px'; cv.style.height = h + 'px';
  }
  const g = cv.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  return { g, w, h };
}

function renderActs(r, x) {
  let acts = [];
  try { acts = x.b.actions ? x.b.actions(x.d) || [] : []; } catch (e) { console.error('Senzori, dugmad bloka ' + x.b.id, e); }
  r.actList = acts;
  const sig = JSON.stringify(acts.map(a => [a.label, !!a.disabled, a.title || '']));
  if (sig === r.actSig) return;
  r.actSig = sig;
  r.acts.replaceChildren(...acts.map((a, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = a.label;
    btn.disabled = !!a.disabled;
    if (a.title) btn.title = a.title;
    btn.onclick = e => {
      e.stopPropagation();
      const cur = r.actList[i];
      if (cur && !cur.disabled) { cur.run(); schedule(); }
    };
    return btn;
  }));
}

function update(r, x, big) {
  const v = x.v, status = ['ok', 'warn'].includes(v.status) ? v.status : 'none';
  setCls(r.lamp, 'sz-lamp ' + status);
  setTitle(r.lamp, v.text || LAMP_TITLE[status]);
  if (r.state) setText(r.state, v.text || '');
  renderActs(r, x);
  if (x.s.src) {
    if (r.canvas && x.b.draw) {
      const { g, w, h } = fit(r.canvas);
      try { x.b.draw(g, w, h, x.d, big); } catch (e) { console.error('Senzori, crtanje bloka ' + x.b.id, e); }
    }
    if (r.html && x.b.html) setHTML(r.html, x.b.html(x.d, big));
    if (r.big) setHTML(r.big, v.vals.length ? valsHTML(v.vals, true) : `<span class="dim">${esc(v.text)}</span>`);
  }
  if (r.vals) {                                     // red ispod pločice: vrednosti (kad ih telo ne piše krupno), foot, napomena
    const foot = v.foot ? `<span class="sz-foot">${esc(v.foot)}</span>` : '';
    const note = x.s.note ? `<span class="sz-note">${esc(x.s.note)}</span>` : '';
    setHTML(r.vals, (r.big ? '' : valsHTML(v.vals, false)) + foot + note);
    setTitle(r.vals, r.vals.textContent);
  }
  if (r.table) {
    setHTML(r.table, v.vals.length ? v.vals.map(([k, val]) => `<tr><td>${esc(k)}</td><td>${esc(val)}</td></tr>`).join('')
      : '<tr><td class="dim">—</td></tr>');
  }
}

// ---------------- prijava ----------------

registerPanel({
  id: 'senzori-alati', title: 'Senzori', workspaces: ['senzori'], region: 'tool', priority: 1, open: true,
  mount: (el, ctx) => mountTool(el, ctx),
  shown: () => schedule(),
});

registerPanel({
  id: 'senzori', title: 'Senzori', workspaces: ['senzori'], when: st => st.sensOpen !== 'lidar', region: 'main',
  priority: 1, open: true,
  mount: (el, ctx) => mountMain(el, ctx),
  shown: () => schedule(),
});
