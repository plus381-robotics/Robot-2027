// Izvori (Zadatak 5.1): jedan blok za mešanje izvora podataka. Prozorčić #izvori (index.html) se otvara iz bočne trake
// (stavka Izvori) i iz reda komandi Vožnja (dugme „Izvori ▾“ #izvoriBtn). Sadržaj:
//   - unapred zadate kombinacije a (sve sim) · b (hibrid: lidar pravi ili iz snimka) · c (sivo: Faza 6) · d (sve pravo)
//   - red po delu robota (pogon, lidar, IR, mehanizmi, protivnici) sa izvorima sim / pravi / snimak / lažiran;
//     nedozvoljeno je sivo, a razlog piše ispod reda (i u title)
//   - veza sa robotom NIJE ovde: „Poveži robota“ na statusnoj traci (shell/veza.js, #vezaPop; host i lozinka važe i za
//     pravi lidar u hibridu). Preset d (sve pravo) i dugme „Poveži robota…“ ovde otvaraju taj prozorčić (openConnect).
// Dok sesija radi blok se samo čita i pokazuje šta sesija stvarno koristi (hello.source). Logika (šta je dozvoljeno,
// razlozi, šta izbor menja) je u core/izvori.js. Izbor: store.drive (pogon: SIM/ROBOT, isti kao u bočnoj traci) i
// store.sources {lidar, file} (localStorage `eurosim.sources`).
//   mountIzvori({store, setDrive(d) -> bool, openConnect(anchor) -> bool}) -> {open(anchor), close(), toggle(anchor), isOpen()}
import { izvoriView, applyPreset, applyOption, izvoriLabel, normSources, saveSources } from '../core/izvori.js';
import { esc } from '../core/api.js';

export function mountIzvori({ store, setDrive, openConnect }) {
  const $ = id => document.getElementById(id);
  const box = $('izvori'), btn = $('izvoriBtn');
  let anchor = null, lastKey = '';

  function place() {
    const w = box.offsetWidth, h = box.offsetHeight, vw = innerWidth, vh = innerHeight;
    const r = anchor && anchor.isConnected ? anchor.getBoundingClientRect() : null;
    let left, top;
    if (r && anchor.closest('#rail')) {                    // uz bočnu traku, poravnato sa stavkom (i ne ispod ekrana)
      left = r.right + 8; top = Math.min(r.top, vh - h - 8);
    } else if (r && r.width) {                             // ispod dugmeta u redu komandi
      left = Math.min(r.left, vw - w - 8); top = r.bottom + 6;
      if (top + h > vh - 8) top = Math.max(8, vh - h - 8);
    } else { left = (vw - w) / 2; top = 80; }
    box.style.left = Math.max(8, left) + 'px';
    box.style.top = Math.max(8, top) + 'px';
  }

  function act(r) {                                       // r = {drive, sources} iz core/izvori.js; null = sivo
    if (!r) return;
    const st = store.get();
    if (r.drive !== st.drive && !setDrive(r.drive)) return;
    store.set({ sources: r.sources });
  }

  function connectNow(a) {                                // d: odmah pokaži „Poveži robota“ (isti prozorčić kao sa trake)
    if (!openConnect || !openConnect(a)) return;
    close();
  }

  function render(st) {
    const label = izvoriLabel(st);
    if (btn.textContent !== label) btn.textContent = label;
    if (box.hidden) return;
    const v = izvoriView(st);
    const key = JSON.stringify([v, st.session && st.session.host]);
    if (key === lastKey) return;
    lastKey = key;
    box.classList.toggle('ro', v.readOnly);
    $('izvNote').textContent = v.note;
    const presets = $('izvPresets');
    presets.innerHTML = v.presets.map(p => `<button type="button" data-p="${p.id}" class="${p.on ? 'on' : ''}" aria-pressed="${p.on}"` +
      `${p.disabled ? ' disabled' : ''} title="${esc(p.title + (p.reason ? ' (' + p.reason + ')' : ''))}">${esc(p.label)}</button>`).join('');
    for (const b of presets.querySelectorAll('button')) b.onclick = () => {
      const r = applyPreset(b.dataset.p, store.get());
      act(r);
      if (r && b.dataset.p === 'd' && store.get().drive === 'robot') connectNow(btn);
    };
    const table = $('izvParts');
    table.innerHTML = v.rows.map(r => `<tr data-part="${r.id}"><th title="${esc(r.title)}">${esc(r.name)}</th><td>` +
      `<span class="seg" role="group" aria-label="${esc(r.name)}">` +
      r.options.map(o => `<button type="button" data-v="${o.v}" class="${o.on ? 'on' : ''}" aria-pressed="${o.on}"` +
        `${o.disabled ? ' disabled' : ''}${o.reason ? ` title="${esc(o.label + ': ' + o.reason)}"` : ''}>${esc(o.label)}</button>`).join('') +
      '</span>' +
      (r.id === 'lidar' && v.lidarFile.shown ? `<select id="izvLidarFile" title="Snimak lidara (studio/lidar/): krugovi se ponavljaju u krug"${v.lidarFile.disabled ? ' disabled' : ''}>` +
        v.lidarFile.files.map(f => `<option value="${esc(f)}"${f === v.lidarFile.value ? ' selected' : ''}>${esc(f.replace('.jsonl.gz', ''))}</option>`).join('') +
        '</select>' : '') +
      (r.why ? `<div class="izv-why">${esc(r.why)}</div>` : '') + '</td></tr>').join('');
    for (const b of table.querySelectorAll('button')) {
      b.onclick = () => act(applyOption(b.closest('tr').dataset.part, b.dataset.v, store.get()));
    }
    const sel = $('izvLidarFile');
    if (sel && !v.lidarFile.disabled) sel.onchange = () => {
      const s = store.get();
      store.set({ sources: { ...normSources(s.sources, s.lidarFiles || []), lidar: 'snimak', file: sel.value } });
    };
    // Veza sa robotom je na traci: ovde samo uputa kad d ili pravi lidar traže host i lozinku
    $('izvConn').hidden = !v.connect.show;
    $('izvConnTxt').textContent = v.connect.usedBy === 'robot' ? 'd (sve pravo): robot se povezuje sa trake, „Poveži robota“ (pravi ili virtuelni).'
      : v.connect.usedBy === 'lidar' ? 'Pravi lidar u hibridu (b): host i lozinka su u „Poveži robota“ na traci.' : '';
    place();
  }

  function open(a) {
    anchor = a || null;
    box.hidden = false;
    lastKey = '';
    render(store.get());
    place();
  }
  function close() { box.hidden = true; }
  function toggle(a) { if (!box.hidden && (a || null) === anchor) close(); else open(a); }

  $('izvClose').onclick = close;
  $('izvConnBtn').onclick = () => connectNow(btn);
  btn.onclick = () => toggle(btn);
  document.addEventListener('pointerdown', e => {          // klik van prozorčića ga zatvara (ne i klik na dugme koje ga otvara)
    if (!box.hidden && !e.target.closest('#izvori, #izvoriBtn, #rail [data-act=sources]')) close();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !box.hidden) close(); });   // Esc i dalje šalje STOP
  addEventListener('resize', () => { if (!box.hidden) place(); });
  store.subscribe((st, prev) => {
    if (st.sources !== prev.sources) saveSources(st.sources);
    render(st);
  });
  render(store.get());
  return { open, close, toggle, isOpen: () => !box.hidden };
}
