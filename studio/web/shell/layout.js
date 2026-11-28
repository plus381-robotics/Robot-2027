// Okvir (varijanta A): statusna traka gore, bočna traka levo, a u #content regioni radnog prostora:
//   #ws-tool    red komandi prostora (region "tool")
//   #ws-body =  #ws-main (paneli jedan pored drugog, region "main") + #ws-side (kolona sklopivih kartica, "side")
//   #ws-bottom  vreme, grafici (region "bottom"; panel sa `collapsible` je kartica)
// Svaki panel dobija svoj koren (div.ws-panel#ws-<id>) i mount(el, ctx) samo JEDNOM, na početku. Pri promeni prostora
// koren (ili njegova kartica) se PREMEŠTA u region (isti DOM čvor: FieldView, grafici i editor ostaju isti), po
// prioritetu; paneli koji nisu u tom prostoru dobiju .ws-off. Prazan region se sakrije. Stanje kartica
// (sklopljeno/otvoreno) se pamti po prostoru u localStorage `eurosim.cards` (core/regions.js).
// Zajedničke stavke reda komandi (Taktika, Strana; core/toolitems.js): koren i mount jednom, a pri promeni prostora
// čvor se premešta u panel tog prostora koji ga navodi u `shared` (na njegovo mesto data-slot, inače na kraj korena).
// Paneli sa `when(state, ws)` (npr. ESP, Postavka stola) se ponovo raspoređuju kad se promene session, caps ili drive;
// kartice sa `open(ws, state)` (Grafici u Snimcima dok postoji referenca) i kad se promeni refLabel.
// Stavke bočne trake:
//   Taktike -> otvoren editor (sesija, ako radi, nastavlja da radi, traka i njen STOP takođe);
//   Vožnja -> SIM ili ROBOT (izbor ispod stavke, store.drive): red komandi Vožnja (panels/voznja-alati.js) i kartice
//             idu za njim;  Snimci -> lista sačuvanih snimaka (osveži je: legacy.openRuns);  Test dela -> podkartice, Lidar (panels/lidar.js).
// Dok sesija radi, prelaz SIM <-> ROBOT se odbija porukom „Sesija radi: prvo je završi“; traka i njen STOP (i Esc)
// rade u svakom prostoru. Tastatura (core/keys.js): Alt+1..4 = prostori (redom kao u bočnoj traci), „?“ = prečice.
//   mountShell({store, command, legacy}) -> {go, setDrive, setBadge, openCard}
//   openCard(id): otvori karticu u tekućem prostoru (zapamti kao klik), npr. Dnevnik za ⚠ na traci
//   legacy = {notice(text, err), openEditor(), openRuns(), loadRun(name), clearRef(), openSources(anchor) (blok Izvori, toggle),
//             openRepo(), openProfile() (dijalog; ponovni klik ga zatvara), showErrors(), resizeView()}

import { panelsFor, allPanels, WORKSPACES, loadWorkspace, saveWorkspace } from '../core/panels.js';
import { placePanels, isCard, cardsOpen, setCard, loadCards, saveCards, REGION_ORDER } from '../core/regions.js';
import { allToolItems, sharedHomes, sharedMoves } from '../core/toolitems.js';
import { wsForKey, isHelpKey, isTyping } from '../core/keys.js';
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

// Alt+1..4 = radni prostor, odakle god (i iz editora i polja); preventDefault da pregledač ne prebaci svoju karticu
// (gde to dozvoljava). „?“ = spisak prečica, ali ne dok se kuca u polje ili editor.
export function installKeys(target, { go, help }) {
  const onKey = e => {
    const ws = wsForKey(e);
    if (ws) { e.preventDefault(); go(ws); return; }
    if (help && isHelpKey(e) && !isTyping(e.target)) { e.preventDefault(); help(); }
  };
  target.addEventListener('keydown', onKey);
  return () => target.removeEventListener('keydown', onKey);
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

  // Zajedničke stavke reda komandi: koren + mount jednom (pre panela); mesto dobijaju u applyPanels (placeItems).
  const items = {}, itemWhere = {};   // id -> koren stavke;  id -> id panela u kome je sada
  for (const it of allToolItems()) {
    const root = el('span', 'ti-' + it.id, 'tool-item');
    items[it.id] = root;
    it.mount(root, ctx);
  }

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
  placeItems(allPanels());            // odmah u dokument (i u Test dela, gde ih nijedan panel ne prima): app.js ih traži po id-ju
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
    const list = panelsFor(ws, caps(), store.get());
    const place = placePanels(list), open = cardsOpen(list, ws, cards, store.get());
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
    placeItems(list);
    for (const p of list) {
      const r = roots[p.id];
      if (p.shown && !(r.card && r.card.classList.contains('closed'))) p.shown(r.root, ctx);
    }
  }

  function placeItems(list) {         // zajedničke stavke u panel ovog prostora (isti čvor se seli); bez doma: ostaju
    for (const m of sharedMoves(itemWhere, sharedHomes(list))) {
      const node = items[m.id], r = roots[m.to];
      if (!node || !r) continue;
      (r.root.querySelector(`[data-slot="${m.id}"]`) || r.root).appendChild(node);
      itemWhere[m.id] = m.to;
    }
  }

  function setDrive(d) {
    d = d === 'robot' ? 'robot' : 'sim';
    const s = store.get().session;
    if (s && (s.kind === 'robot' ? 'robot' : 'sim') !== d) {               // izvor se ne menja dok sesija radi
      if (legacy.notice) legacy.notice('Sesija radi: prvo je završi');
      return false;
    }
    store.set({ drive: d });
    return true;
  }

  function go(ws) {
    if (!WORKSPACES.includes(ws)) return;
    store.set({ ws });
    saveWorkspace(ws);
    applyPanels(ws);
    const st = store.get();
    if (ws === 'taktike') legacy.openEditor();                            // sesija, ako radi, nastavlja da radi
    else if (ws === 'voznja') setDrive(st.session ? (st.session.kind === 'robot' ? 'robot' : 'sim') : st.drive);
    else if (ws === 'snimci') legacy.openRuns();
  }

  function openSources(anchor) {                  // blok Izvori (panels/izvori.js) uz Vožnju; ponovni klik ga zatvara
    go('voznja');
    legacy.openSources(anchor);
  }

  store.subscribe((st, prev) => {
    if (st.drive !== prev.drive) saveDrive(st.drive);
    if (curWs && (st.caps !== prev.caps || st.drive !== prev.drive || st.session !== prev.session || st.refLabel !== prev.refLabel))
      applyPanels(curWs);                       // `needs`: siv ili ne; `when`: ESP, Postavka stola; open(ws, state): Grafici
  });
  mountStrip($('strip'), ctx);
  const rail = mountRail($('rail'), ctx);
  installEscStop(window, () => !!store.get().session, () => command(['stop']));
  installKeys(window, { go, help: rail.toggleHelp });

  // Početak: prostor iz localStorage; primenjuje se samo kartica (editor i meni se ne otvaraju sami).
  const ws = loadWorkspace(), drive = loadDrive();
  store.set({ ws, drive });
  applyPanels(ws);
  return { go, setDrive, setBadge, openCard };
}
