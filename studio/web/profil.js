// Profil robota (F4), iz app.js (Zadatak 4.6): dijalog #profDialog (stavka Profil u bočnoj traci) sa svim vrednostima
// iz studio/profiles/*.toml i komentarima; (P) = pretpostavka. „Sačuvaj i koristi“ upisuje izmenjena polja u fajl
// (komentari ostaju) i sledeća simulacija ih koristi.
//   mountProfile({msg, setInfo}) -> {toggle()}
import { api } from './core/api.js';

export function mountProfile({ msg, setInfo }) {
  const $ = id => document.getElementById(id);

  async function open(file) {
    const d = file ? await api('/api/profile', { file }) : await api('/api/profile');
    const list = file ? await api('/api/profile') : d;
    $('profFile').innerHTML = (list.files || []).map(f => `<option>${f}</option>`).join('');
    $('profFile').value = d.file.split(/[\\/]/).pop();
    $('profPath').textContent = d.file;
    const body = $('profBody');
    body.innerHTML = '';
    for (const sec of d.sections) {
      const h = document.createElement('h4'); h.textContent = sec.name || 'opšte'; body.appendChild(h);
      for (const it of sec.items) {
        const row = document.createElement('div'); row.className = 'pr';
        const key = (sec.name ? sec.name + '.' : '') + it.key;
        const isBool = typeof it.value === 'boolean';
        row.innerHTML = `<span>${it.key}</span><input data-key="${key}" ${isBool ? 'type="checkbox"' : ''}>` +
          `<span class="c ${/\(P\)/.test(it.comment) ? 'p' : ''}"></span>`;
        const inp = row.querySelector('input');
        if (isBool) inp.checked = it.value; else inp.value = it.value;
        inp.dataset.orig = String(it.value);
        inp.oninput = inp.onchange = () => inp.classList.toggle('changed', (isBool ? String(inp.checked) : inp.value) !== inp.dataset.orig);
        row.querySelector('.c').textContent = it.comment;
        row.querySelector('.c').title = it.comment;
        body.appendChild(row);
      }
    }
    $('profDialog').hidden = false;
  }

  async function save() {
    const changes = {};
    for (const inp of document.querySelectorAll('#profBody input.changed')) {
      changes[inp.dataset.key] = inp.type === 'checkbox' ? inp.checked : (isNaN(+inp.value) ? inp.value : +inp.value);
    }
    try {
      const d = await api('/api/profile', { file: $('profFile').value, changes });
      setInfo(await api('/api/info'));
      msg(`profil sačuvan (izmena: ${Object.keys(changes).length}): ${d.file} · sledeća simulacija (▶ Pokreni) ga koristi`);
      $('profDialog').hidden = true;
    } catch (e) { msg(e.message, true); }
  }

  const toggle = () => ($('profDialog').hidden ? open().catch(e => msg(e.message, true)) : ($('profDialog').hidden = true));
  $('profClose').onclick = () => { $('profDialog').hidden = true; };
  $('profSave').onclick = save;
  $('profFile').onchange = e => open(e.target.value).catch(er => msg(er.message, true));
  return { toggle };
}
