// Okvir (varijanta A): statusna traka gore, bočna traka levo, glavni prostor po radnom prostoru.
// Prelazni korak (Zadatak 3.2): stari UI (#bar, #main, #timeline) je „legacy“ sadržaj glavnog prostora u Taktikama,
// Vožnji i Snimcima; stavke bočne trake upravljaju starim karticama:
//   Taktike -> stara kartica Simulate + otvoren editor;  Vožnja -> Live (SIM) ili Robot (ROBOT), izbor ispod stavke;
//   Snimci -> otvara stari meni „⋯ Runs“;  Test dela -> prazan glavni prostor „Test dela dolazi u Fazi 5“.
// Dok sesija radi, prelaz SIM <-> ROBOT odbija stari setTab (sa porukom); traka i njen STOP rade u svakom prostoru.
//   mountShell({store, command, legacy}) -> {go, setDrive}
//   legacy = {setTab(t) -> bool, openEditor(), openRuns(), openSources(drive, running), openRepo(), openProfile(), showErrors()}

import { registerPanel, panelsFor, getPanel, WORKSPACES, loadWorkspace, saveWorkspace } from '../core/panels.js';
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

export function mountShell({ store, command, legacy }) {
  const $ = id => document.getElementById(id);
  const ctx = { store, command, go, setDrive, openSources, legacy };

  // Delovi okvira u registru (paneli prelaze u Fazi 4).
  if (!getPanel('legacy')) {
    registerPanel({ id: 'legacy', title: 'Stari prikaz', workspaces: ['taktike', 'voznja', 'snimci'], region: 'main', priority: 1,
      open: true, mount: () => $('legacy') });
    registerPanel({ id: 'test-dela', title: 'Test dela', workspaces: ['test'], region: 'main', priority: 1, open: true,
      mount: el => { el.innerHTML = '<div class="ws-empty"><h2>Test dela</h2><p>Test dela dolazi u Fazi 5</p></div>'; } });
  }
  const content = $('content'), mounted = {};
  function mainEl(p) {
    if (!mounted[p.id]) {
      let el = p.id === 'legacy' ? $('legacy') : null;
      if (!el) { el = document.createElement('div'); el.className = 'ws-panel'; el.id = 'ws-' + p.id; content.appendChild(el); }
      p.mount(el, ctx);
      mounted[p.id] = el;
    }
    return mounted[p.id];
  }
  function applyPanels(ws) {
    const shown = new Set(panelsFor(ws).filter(p => p.region === 'main').map(p => p.id));
    for (const w of WORKSPACES) for (const p of panelsFor(w)) {
      if (p.region !== 'main') continue;
      mainEl(p).classList.toggle('ws-off', !shown.has(p.id));
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

  store.subscribe((st, prev) => { if (st.drive !== prev.drive) saveDrive(st.drive); });   // i stare kartice Live/Robot
  mountStrip($('strip'), ctx);
  mountRail($('rail'), ctx);
  installEscStop(window, () => !!store.get().session, () => command(['stop']));

  // Početak: prostor iz localStorage; primenjuje se samo kartica (editor i meni se ne otvaraju sami).
  const ws = loadWorkspace(), drive = loadDrive();
  store.set({ ws, drive });
  applyPanels(ws);
  if (ws === 'taktike') legacy.setTab('sim');
  else if (ws === 'voznja') setDrive(drive);
  return { go, setDrive };
}
