// Bočna traka (varijanta A): četiri radna prostora (ikona + naziv), ispod „Vožnja“ (kad je izabrana) izbor
// SIM / ROBOT, a dole Izvori, Repo, Profil, Pomoć (nisu radni prostori). Izabrana stavka = store.ws, izbor SIM/ROBOT =
// store.drive (sesija ga postavlja na svoju vrstu), pa traka uvek pokazuje stvarni prostor i izvor.
// Repo (Zadatak 4.6; ranije i dugme „⎇ Repo“ u starom redu): vidi se samo kad je aplikacija u timskom repou
// (store.repo != null, piše ga web/repo.js), sa značkom (↓ novo na GitHub-u, ! profil, ● izmenjeno).
// Pomoć: prozorčić sa prečicama (core/keys.js SHORTCUTS); i taster „?“; zatvara ga ✕, Esc ili klik van njega.
//   mountRail(el, ctx) -> {render, toggleHelp}
//   railChanged(st, prev) -> true kad se promenilo nešto što traka crta (ws, drive, repo, vrsta sesije); store se menja
//                            ~10 puta u sekundi tokom sesije (paketi lidara, telemetrija), a traka ne treba da se crta
//   ctx = {store, go(ws), setDrive('sim'|'robot'), openSources(anchor), legacy: {openRepo, openProfile}}

import { SHORTCUTS } from '../core/keys.js';

export const RAIL_ITEMS = [
  { id: 'taktike', name: 'Taktike', title: 'Taktike: editor, brza simulacija i puštanje (Alt+1)',
    icon: '<path d="M8 6 3 12l5 6M16 6l5 6-5 6M14 4l-4 16"/>' },
  { id: 'senzori', name: 'Senzori', title: 'Senzori: pregled svih senzora robota (Alt+2)',
    icon: '<path d="M4 16a8 8 0 1 1 16 0"/><path d="M12 16l4-5"/><circle cx="12" cy="16" r="1.5"/>' },
  { id: 'voznja', name: 'Vožnja', title: 'Vožnja: simulacija uživo (SIM) ili pravi/virtuelni robot (ROBOT) (Alt+3)',
    icon: '<rect x="5" y="7" width="14" height="10" rx="2"/><path d="M9 17v3M15 17v3M12 3v4M8 11h.01M16 11h.01"/>' },
  { id: 'snimci', name: 'Snimci', title: 'Snimci: sačuvaj, učitaj, uporedi (Alt+4)',
    icon: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>' },
];

const MINI = [
  { act: 'sources', name: 'Izvori', title: 'Izvori: šta je simulirano, a šta pravo (sve sim, hibrid sa pravim lidarom ili snimkom, pravi robot) i veza sa robotom',
    icon: '<path d="M4 6h16M4 12h10M4 18h6"/><circle cx="18" cy="12" r="2"/><circle cx="14" cy="18" r="2"/>' },
  { act: 'repo', name: 'Repo', title: 'Timski repo (GitHub): preuzmi najnovije, sačuvaj svoje',
    icon: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 8v8M18 10a6 6 0 0 1-6 6H8"/>' },
  { act: 'profile', name: 'Profil', title: 'Profil robota: dimenzije, pogon, regulacija, IR',
    icon: '<circle cx="12" cy="12" r="3"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>' },
  { act: 'help', name: 'Pomoć', title: 'Prečice sa tastature (?)',
    icon: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01"/>' },
];

// Logo na vrhu trake (ikonica + „Gambit“ / „Studio“ kao u maketi).
export const RAIL_LOGO = { title: 'Gambit', sub: 'Studio' };
const KNIGHT = '<path d="M7 20h10M8 20l1-4c-2-1-3-3-2-5l4-5 1-2 1 2c3 1 5 4 4 8l-1 6"/><path d="M11 8h.01"/>';

const sessionKind = st => (st.session ? st.session.kind : null);
export const railChanged = (st, prev) => !prev || st.ws !== prev.ws || st.drive !== prev.drive || st.repo !== prev.repo ||
  sessionKind(st) !== sessionKind(prev);

const icon = p => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;

export function mountRail(el, ctx) {
  el.setAttribute('aria-label', 'Radni prostori');
  el.innerHTML = `<div class="rl-logo" title="${RAIL_LOGO.title} ${RAIL_LOGO.sub}">${icon(KNIGHT)}<b>${RAIL_LOGO.title}</b><span>${RAIL_LOGO.sub}</span></div>` +
    RAIL_ITEMS.map(w => `<button type="button" class="rl-ws" data-ws="${w.id}" title="${w.title}">${icon(w.icon)}<span>${w.name}</span></button>` +
    (w.id === 'voznja' ? `<span class="rl-drive" id="railDrive" hidden>
      <button type="button" data-drive="sim" title="Simulacija u stvarnom vremenu (sesija uživo, ESP ekran i tasteri)">SIM</button>
      <button type="button" data-drive="robot" title="Pravi ili virtuelni robot preko WiFi-ja (Poveži)">ROBOT</button></span>` : '')).join('') +
    '<span class="rl-grow"></span>' +
    MINI.map(m => `<button type="button" class="rl-mini" data-act="${m.act}" title="${m.title}">${icon(m.icon)}<span>${m.name}</span>` +
      (m.act === 'repo' ? '<b class="badge rl-badge" id="repoBadge" hidden></b>' : '') + '</button>').join('');
  const help = document.createElement('div');
  help.id = 'railHelp'; help.className = 'rl-help'; help.hidden = true;
  help.setAttribute('role', 'dialog'); help.setAttribute('aria-label', 'Prečice sa tastature');
  help.innerHTML = '<div class="rl-help-h">Gambit Studio · prečice <button type="button" title="Zatvori (Esc)">✕</button></div>' +
    `<table>${SHORTCUTS.map(([k, v]) => `<tr><td><kbd>${k}</kbd></td><td>${v}</td></tr>`).join('')}</table>`;
  document.body.appendChild(help);
  const toggleHelp = () => { help.hidden = !help.hidden; };
  help.querySelector('button').onclick = () => { help.hidden = true; };
  document.addEventListener('pointerdown', e => {
    if (!help.hidden && !e.target.closest('#railHelp, #rail [data-act=help]')) help.hidden = true;
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !help.hidden) help.hidden = true; });   // Esc i dalje šalje STOP

  for (const b of el.querySelectorAll('[data-ws]')) b.onclick = () => ctx.go(b.dataset.ws);
  for (const b of el.querySelectorAll('[data-drive]')) b.onclick = () => ctx.setDrive(b.dataset.drive);
  const acts = {
    sources: b => ctx.openSources(b),
    repo: () => ctx.legacy.openRepo(),
    profile: () => ctx.legacy.openProfile(),
    help: toggleHelp,
  };
  for (const b of el.querySelectorAll('[data-act]')) b.onclick = () => acts[b.dataset.act](b);
  const repoBtn = el.querySelector('[data-act=repo]'), badge = el.querySelector('#repoBadge');
  const repoTitle = repoBtn.title;

  function render(st) {
    for (const b of el.querySelectorAll('[data-ws]')) {
      const on = b.dataset.ws === st.ws;
      b.classList.toggle('on', on);
      if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    }
    el.querySelector('#railDrive').hidden = st.ws !== 'voznja';
    for (const b of el.querySelectorAll('[data-drive]')) b.classList.toggle('on', b.dataset.drive === st.drive);
    const r = st.repo;                             // null: nije timski repo (standalone / van repoa): stavke nema
    repoBtn.hidden = !r;
    badge.hidden = !(r && r.badge);
    badge.textContent = (r && r.badge) || '';
    repoBtn.title = repoTitle + (r && r.title ? '\n' + r.title : '');
  }
  ctx.store.subscribe((st, prev) => { if (railChanged(st, prev)) render(st); });
  render(ctx.store.get());
  return { render, toggleHelp };
}
