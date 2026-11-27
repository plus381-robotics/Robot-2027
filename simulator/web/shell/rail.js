// Bočna traka (varijanta A): četiri radna prostora (ikona + naziv), ispod „Vožnja“ (kad je izabrana) izbor
// SIM / ROBOT, a dole Izvori, Repo, Profil, Pomoć (nisu radni prostori).
//   mountRail(el, ctx)   ctx = {store, go(ws), setDrive('sim'|'robot'), openSources(), legacy: {openRepo, openProfile}}

export const RAIL_ITEMS = [
  { id: 'taktike', name: 'Taktike', title: 'Taktike: editor, brza simulacija i puštanje',
    icon: '<path d="M8 6 3 12l5 6M16 6l5 6-5 6M14 4l-4 16"/>' },
  { id: 'test', name: 'Test dela', title: 'Test dela robota (lidar, pogon, mehanizmi, IR)',
    icon: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>' },
  { id: 'voznja', name: 'Vožnja', title: 'Vožnja: simulacija uživo (SIM) ili pravi/virtuelni robot (ROBOT)',
    icon: '<rect x="5" y="7" width="14" height="10" rx="2"/><path d="M9 17v3M15 17v3M12 3v4M8 11h.01M16 11h.01"/>' },
  { id: 'snimci', name: 'Snimci', title: 'Snimci: sačuvaj, učitaj, uporedi',
    icon: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>' },
];

const MINI = [
  { act: 'sources', name: 'Izvori', title: 'Izvori podataka: lidar u simulaciji, veza sa robotom',
    icon: '<path d="M4 6h16M4 12h10M4 18h6"/><circle cx="18" cy="12" r="2"/><circle cx="14" cy="18" r="2"/>' },
  { act: 'repo', name: 'Repo', title: 'Timski repo (GitHub): preuzmi najnovije, sačuvaj svoje',
    icon: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 8v8M18 10a6 6 0 0 1-6 6H8"/>' },
  { act: 'profile', name: 'Profil', title: 'Profil robota: dimenzije, pogon, regulacija, IR',
    icon: '<circle cx="12" cy="12" r="3"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>' },
  { act: 'help', name: 'Pomoć', title: 'Prečice sa tastature',
    icon: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01"/>' },
];

const HELP = [
  ['Esc', 'STOP (iz svakog prostora, i iz editora)'],
  ['Razmak', 'pusti / pauza'],
  ['← / →', 'frejm nazad / napred'],
  ['Shift+← / →', 'korak nazad / napred'],
  ['Home / End', 'početak / kraj snimka'],
  ['Ctrl+Enter', 'pokreni simulaciju'],
  ['Ctrl+S', 'sačuvaj taktiku (u editoru)'],
];

const icon = p => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;

export function mountRail(el, ctx) {
  el.setAttribute('aria-label', 'Radni prostori');
  el.innerHTML = RAIL_ITEMS.map(w => `<button type="button" class="rl-ws" data-ws="${w.id}" title="${w.title}">${icon(w.icon)}<span>${w.name}</span></button>` +
    (w.id === 'voznja' ? `<span class="rl-drive" id="railDrive" hidden>
      <button type="button" data-drive="sim" title="Simulacija u stvarnom vremenu (stara kartica Live)">SIM</button>
      <button type="button" data-drive="robot" title="Pravi ili virtuelni robot (stara kartica Robot)">ROBOT</button></span>` : '')).join('') +
    '<span class="rl-grow"></span>' +
    MINI.map(m => `<button type="button" class="rl-mini" data-act="${m.act}" title="${m.title}">${icon(m.icon)}<span>${m.name}</span></button>`).join('');
  const help = document.createElement('div');
  help.id = 'railHelp'; help.className = 'rl-help'; help.hidden = true;
  help.innerHTML = '<div class="rl-help-h">Prečice <button type="button" title="Zatvori">✕</button></div>' +
    `<table>${HELP.map(([k, v]) => `<tr><td><kbd>${k}</kbd></td><td>${v}</td></tr>`).join('')}</table>`;
  document.body.appendChild(help);
  help.querySelector('button').onclick = () => { help.hidden = true; };
  document.addEventListener('pointerdown', e => {
    if (!help.hidden && !e.target.closest('#railHelp, #rail [data-act=help]')) help.hidden = true;
  });

  for (const b of el.querySelectorAll('[data-ws]')) b.onclick = () => ctx.go(b.dataset.ws);
  for (const b of el.querySelectorAll('[data-drive]')) b.onclick = () => ctx.setDrive(b.dataset.drive);
  const acts = {
    sources: () => ctx.openSources(),
    repo: () => ctx.legacy.openRepo(),
    profile: () => ctx.legacy.openProfile(),
    help: () => { help.hidden = !help.hidden; },
  };
  for (const b of el.querySelectorAll('[data-act]')) b.onclick = () => acts[b.dataset.act]();

  function render(st) {
    for (const b of el.querySelectorAll('[data-ws]')) {
      const on = b.dataset.ws === st.ws;
      b.classList.toggle('on', on);
      if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    }
    el.querySelector('#railDrive').hidden = st.ws !== 'voznja';
    for (const b of el.querySelectorAll('[data-drive]')) b.classList.toggle('on', b.dataset.drive === st.drive);
  }
  ctx.store.subscribe(render);
  render(ctx.store.get());
  return { render };
}
