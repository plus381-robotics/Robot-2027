// Prozorčić „Poveži robota“ (#vezaPop, index.html) ispod statusne trake: host (#rHost), lozinka (#rPass), Poveži
// (#rConnect), Virtuelni robot (#rVirtual). Ponašanje polja je u app.js (isti id-jevi); ovde samo otvaranje, položaj i
// zatvaranje: ✕, Esc i klik van prozorčića. Esc se ne guta (STOP šalje slušalac iz layout.js, u fazi hvatanja).
//   mountVeza({store, notice}) -> {open(anchor?) -> bool, close(), isOpen()}
// open() prvo pita connectView (shell/strip.js): dok sesija radi, razlog ide u poruku ispod trake i prozorčić se ne otvara.
import { connectView } from './strip.js';

export function mountVeza({ store, notice }) {
  const box = document.getElementById('vezaPop');
  let anchor = null;

  function place() {
    const w = box.offsetWidth, vw = innerWidth;
    const strip = document.getElementById('strip');
    const r = anchor && anchor.isConnected ? anchor.getBoundingClientRect() : null;
    const sr = strip ? strip.getBoundingClientRect() : null;
    const left = r && r.width ? Math.min(r.left, vw - w - 8) : (vw - w) / 2;
    const top = anchor && anchor.closest('#strip') && sr ? sr.bottom + 6 : r && r.width ? r.bottom + 6 : (sr ? sr.bottom + 6 : 80);
    box.style.left = Math.max(8, left) + 'px';
    box.style.top = Math.max(8, top) + 'px';
  }

  function close() { box.hidden = true; }

  function open(a) {
    const v = connectView(store.get());
    if (!v.ok) { close(); if (notice) notice(v.reason); return false; }
    anchor = a || null;
    box.hidden = false;
    place();
    const host = document.getElementById('rHost');
    if (host) host.focus();
    return true;
  }

  document.getElementById('vezaClose').onclick = close;
  document.addEventListener('pointerdown', e => {          // klik van prozorčića ga zatvara (ne i na dugmad koja ga otvaraju)
    if (box.hidden) return;
    if (e.target.closest('#vezaPop, #stripConnect, #sessStart') || (anchor && anchor.contains(e.target))) return;
    close();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !box.hidden) close(); });   // Esc i dalje šalje STOP
  addEventListener('resize', () => { if (!box.hidden) place(); });
  store.subscribe((st, prev) => { if (st.session !== prev.session && !box.hidden) close(); });      // sesija krenula / stala
  return { open, close, isOpen: () => !box.hidden };
}
