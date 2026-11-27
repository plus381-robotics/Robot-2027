// Okvir (varijanta A): statusna traka gore, bočna traka levo, a u #content regioni radnog prostora:
//   #ws-tool    red komandi prostora (region "tool")
//   #ws-body =  #ws-main (paneli jedan pored drugog, region "main") + #ws-side (kolona sklopivih kartica, "side")
//   #ws-bottom  vreme, grafici (region "bottom"; panel sa `collapsible` je kartica)
// Svaki panel dobija svoj koren (div.ws-panel#ws-<id>) i mount(el, ctx) samo JEDNOM, na početku. Pri promeni prostora
// koren (ili njegova kartica) se PREMEŠTA u region (isti DOM čvor: FieldView, grafici i editor ostaju isti), po
// prioritetu; paneli koji nisu u tom prostoru dobiju .ws-off. Prazan region se sakrije. Stanje kartica
// (sklopljeno/otvoreno) se pamti po prostoru u localStorage `eurosim.cards` (core/regions.js).
// Stavke bočne trake i dalje upravljaju starim karticama (dok njihovi delovi ne pređu u panele):
//   Taktike -> stara kartica Simulate + otvoren editor;  Vožnja -> Live (SIM) ili Robot (ROBOT), izbor ispod stavke;
//   Snimci -> otvara stari meni „⋯ Runs“;  Test dela -> „Test dela dolazi u Fazi 5“.
// Dok sesija radi, prelaz SIM <-> ROBOT odbija stari setTab (sa porukom); traka i njen STOP rade u svakom prostoru.
//   mountShell({store, command, legacy}) -> {go, setDrive, setBadge, openCard}
//   openCard(id): otvori karticu u tekućem prostoru (zapamti kao klik), npr. Dnevnik za ⚠ na traci
//   legacy = {setTab(t) -> bool, openEditor(), openRuns(), openSources(drive, running), openRepo(), openProfile(), showErrors(),
//             resizeView()}

import { panelsFor, allPanels, WORKSPACES, loadWorkspace, saveWorkspace } from '../core/panels.js';
import { placePanels, isCard, cardsOpen, setCard, loadCards, saveCards, REGION_ORDER } from '../core/regions.js';
import { mountStrip } from './strip.js';
import { mountRail } from './rail.js';

const DRIVE_KEY = 'eurosim.drive';

function loadDrive() {
  try { return localStorage.getItem(DRIVE_KEY) === 'robot' ? 'robot' : 'sim'; } catch (e) { return 'sim'; }
}
function saveDrive(d) {
  try { localStorage.setItem(DRIVE_KEY, d); } catch (e) { /* ignore */ }
}

// Esc = STOP čim sesija radi, odakle god (i iz editora sa otvorenim popupom dopune). Slušalac je u fazi hvatanja na
// window-u i NE zove preventDefault/stopPropagation: CodeMirror i dalje dobija Esc i zatvara svoj popup.
export function installEscStop(target, isRunning, stop) {
  const onKey = e => {
    if (e.key !== 'Escape' || e.repeat) return;
    if (isRunning()) stop();
  };
  target.addEventListener('keydown', onKey, { capture: true });
  return () => target.removeEventListener('keydown', onKey, { capture: true });
}

function el(tag, id, cls) {
  const e = document.createElement(tag);
  if (id) e.id = id;
  if (cls) e.className = cls;
  return e;
}

export function mountShell({ store, command, legacy }) {
  const $ = id => document.getElementById(id);
  const ctx = { store, command, go, setDrive, openSources, setBadge, openCard, legacy };

  // Regioni (ispod repo trake, ako je ima).
  const content = $('content');
  const region = { tool: el('div', 'ws-tool'), main: el('div', 'ws-main'), side: el('aside', 'ws-side'), bottom: el('div', 'ws-bottom') };
  const body = el('div', 'ws-body');
  body.append(region.main, region.side);
  content.append(region.tool, body, region.bottom);

  // Paneli: koren + (za kartice) okvir kartice; mount jednom.
  const roots = {};                 // id -> {p, root, box, card?, badge?, why?, arrow?}
  let cards = loadCards(), curWs = null;
  for (const p of allPanels()) {
    const root = el('div', 'ws-' + p.id, 'ws-panel');
    const r = { p, root, box: root };
    if (isCard(p)) {
      const card = el('section', 'card-' + p.id, 'ws-card ws-card-' + p.region + (p.grow ? ' grow' : '') + (p.shrink ? ' shrink' : ''));
      const head = el('button', null, 'ws-card-h');
      head.type = 'button';
      const title = el('span', null, 'ws-card-t');
      title.textContent = p.title;
      r.badge = el('span', null, 'badge ws-card-badge'); r.badge.hidden = true;
      r.why = el('span', null, 'ws-card-why dim small');
      r.arrow = el('span', null, 'ws-card-arrow');
      head.append(title, r.badge, r.why, r.arrow);
      head.onclick = () => toggleCard(p.id);
      card.append(head, root);
      Object.assign(r, { card, head, box: card });
    }
    region[p.region].appendChild(r.box);
    r.box.classList.add('ws-off');
    roots[p.id] = r;
    p.mount(root, ctx);
  }
  const parts = $('parts');                           // index.html: stari delovi čekaju ovde dok ih paneli ne preuzmu
  if (parts && !parts.children.length) parts.remove();

  function setOpen(r, open) {
    r.card.classList.toggle('closed', !open);
    r.head.setAttribute('aria-expanded', open ? 'true' : 'false');
    r.arrow.textContent = open ? '▾' : '▸';
  }

  function toggleCard(id) {
    const r = roots[id];
    if (!r || !r.card || !curWs) return;
    const open = r.card.classList.contains('closed');
    cards = setCard(cards, curWs, id, open);
    saveCards(cards);
    setOpen(r, open);
    if (open && r.p.shown) r.p.shown(r.root, ctx);
  }

  function openCard(id) {
    const r = roots[id];
    if (r && r.card && r.card.classList.contains('closed') && !r.box.classList.contains('ws-off')) toggleCard(id);
  }

  function setBadge(id, text) {
    const r = roots[id];
    if (!r || !r.badge) return;
    r.badge.textContent = text == null ? '' : String(text);
    r.badge.hidden = text == null || text === '';
  }

  function caps() {
    const c = store.get().caps;
    return c instanceof Set ? c : new Set(c || []);
  }

  function applyPanels(ws) {
    curWs = ws;
    const list = panelsFor(ws, caps());
    const place = placePanels(list), open = cardsOpen(list, ws, cards);
    const shown = new Set(list.map(p => p.id));
    for (const id in roots) roots[id].box.classList.toggle('ws-off', !shown.has(id));
    for (const name of REGION_ORDER) {
      const box = region[name];
      const want = place[name].map(p => roots[p.id].box);
      const have = [...box.children].filter(c => want.includes(c));
      if (have.length !== want.length || have.some((c, i) => c !== want[i])) for (const b of want) box.appendChild(b);
      for (const p of place[name]) {
        const r = roots[p.id];
        r.box.classList.toggle('ws-dis', !!p.disabled);
        if (r.card) { setOpen(r, open[p.id]); r.why.textContent = p.disabled ? p.reason : ''; }
      }
      box.hidden = !want.length;
    }
    for (const p of list) {
      const r = roots[p.id];
      if (p.shown && !(r.card && r.card.classList.contains('closed'))) p.shown(r.root, ctx);
    }
  }

  function setDrive(d) {
    d = d === 'robot' ? 'robot' : 'sim';
    if (!legacy.setTab(d === 'robot' ? 'robot' : 'live')) return false;      // sesija radi: stari setTab odbija sa porukom
    store.set({ drive: d });
    return true;
  }

  function go(ws) {
    if (!WORKSPACES.includes(ws)) return;
    store.set({ ws });
    saveWorkspace(ws);
    applyPanels(ws);
    const st = store.get();
    if (ws === 'taktike') { legacy.setTab('sim'); legacy.openEditor(); }
    else if (ws === 'voznja') setDrive(st.session ? (st.session.kind === 'robot' ? 'robot' : 'sim') : st.drive);
    else if (ws === 'snimci') legacy.openRuns();
  }

  function openSources() {
    go('voznja');
    const st = store.get();
    legacy.openSources(st.drive, !!st.session);
  }

  store.subscribe((st, prev) => {
    if (st.drive !== prev.drive) saveDrive(st.drive);                     // i stare kartice Live/Robot
    if (st.caps !== prev.caps && curWs) applyPanels(curWs);                 // panel sa `needs`: siv ili ne
  });
  mountStrip($('strip'), ctx);
  mountRail($('rail'), ctx);
  installEscStop(window, () => !!store.get().session, () => command(['stop']));

  // Početak: prostor iz localStorage; primenjuje se samo kartica (editor i meni se ne otvaraju sami).
  const ws = loadWorkspace(), drive = loadDrive();
  store.set({ ws, drive });
  applyPanels(ws);
  if (ws === 'taktike') legacy.setTab('sim');
  else if (ws === 'voznja') setDrive(drive);
  return { go, setDrive, setBadge, openCard };
}
