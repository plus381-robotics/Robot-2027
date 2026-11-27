// Timski repo kao radni prostor (plan S10), iz app.js (Zadatak 4.6):
//   - traka #repoBanner kad aplikacija nije u repou Robot-2027 (crveno; „Nastavi bez repoa“ = žuto, samo ovaj tab):
//     Kloniraj repo…, Otvori folder repoa…, Nastavi bez repoa;
//   - dijalog #repoDialog (stavka Repo u bočnoj traci): šta je novo na GitHub-u, Preuzmi najnovije (git pull),
//     Sačuvaj na GitHub (commit + push samo taktika i profila);
//   - store.repo: null kad nije repo (stavka Repo se ne vidi), inače {badge, title} za značku na stavci Repo.
//   mountRepo({store, msg, getInfo, setInfo, onPulled}) -> {toggle(), refresh(fetch)}
import { api, esc } from './core/api.js';

export function mountRepo({ store, msg, getInfo, setInfo, onPulled }) {
  const $ = id => document.getElementById(id);
  const where = () => getInfo().where || {};

  function showBanner() {
    const w = where();
    const b = $('repoBanner');
    if (w.mode === 'repo') { b.hidden = true; document.title = 'Eurosim'; return; }
    let local = false;
    try { local = sessionStorage.getItem('eurosim.norepo') === '1'; } catch (e) { /* ignore */ }
    b.hidden = false;
    b.classList.toggle('local', local);
    $('rbLocal').hidden = local;
    $('repoBannerText').textContent = local
      ? `⚠ Bez repoa: taktike i profili se čuvaju SAMO na ovom računaru (${w.home}). Niko drugi ih ne vidi.`
      : '⚠ Eurosim nije pokrenut iz repoa Robot-2027. Taktike i profil robota se NE čuvaju u timski repo i ' +
        'niko drugi ih neće videti. Pokreni ga iz kloniranog repoa (start.bat / start.sh) ili:';
    document.title = 'Eurosim (BEZ REPOA)';
  }

  async function switched(d) {
    if (d.note) alert(d.note);
    location.reload();                                // sve (taktike, profil, putanje) iz novog repoa
  }

  async function openFolder() {
    const w = where();
    const def = (w.user_home || '') + (w.user_home && w.user_home.includes('\\') ? '\\' : '/') + 'Robot-2027';
    const path = prompt('Folder repoa Robot-2027 na ovom računaru (u njemu su ESP32 i simulator):', def);
    if (!path) return;
    try { await switched(await api('/api/repo/open', { path })); } catch (e) { alert(e.message); }
  }

  async function clone() {
    const parent = prompt('U koji folder da kloniram timski repo? (unutra nastaje folder Robot-2027)\n' +
      'Treba Git; GitHub može da traži prijavu.', where().user_home || '');
    if (!parent) return;
    msg('kloniram Robot-2027 sa GitHub-a… (može da potraje minut)');
    try { await switched(await api('/api/repo/clone', { parent })); } catch (e) { msg(e.message, true); alert(e.message); }
  }

  async function refresh(fetch = false) {
    if (where().mode !== 'repo') { store.set({ repo: null }); return null; }
    let st;
    try { st = await api('/api/repo/status' + (fetch ? '?fetch=1' : '')); } catch (e) { st = { error: e.message }; }
    const n = (st.changed || []).length, behind = st.behind || 0, prof = (st.profile_changed_upstream || []).length;
    store.set({ repo: {
      badge: [behind ? `↓${behind}` : '', prof ? '! profil' : '', n ? `●${n}` : ''].filter(Boolean).join(' '),
      title: [behind ? `${behind} novo na GitHub-u: Preuzmi najnovije` : '', prof ? 'profil robota je promenjen na GitHub-u' : '',
        n ? `${n} izmenjen(ih) fajl(ova) nije sačuvano na GitHub` : ''].filter(Boolean).join('\n') } });
    if (!$('repoDialog').hidden) render(st);
    return st;
  }

  function render(st) {
    $('repoRoot').textContent = st.root || '';
    const b = [];
    if (st.error) b.push(`<p class="err">${esc(st.error)}</p>`);
    if (st.branch) b.push(`<p>grana <b>${esc(st.branch)}</b> · ${esc(st.commit || '')}</p>`);
    if (st.behind != null) b.push(`<p>${st.behind ? `<span class="warn">${st.behind} novo na GitHub-u</span>` : 'isto kao na GitHub-u'}` +
      `${st.ahead ? ` · ${st.ahead} tvojih još nije poslato` : ''}</p>`);
    else if (st.branch) b.push('<p class="dim">ova grana još nije na GitHub-u</p>');
    if ((st.profile_changed_upstream || []).length) b.push(`<p class="warn">Profil robota je promenjen na GitHub-u (${st.profile_changed_upstream.map(esc).join(', ')}): Preuzmi najnovije.</p>`);
    const ch = st.changed || [];
    b.push(ch.length ? `<p>Izmenjeno ovde, još nije na GitHub-u:</p><ul>${ch.map(c => `<li><code>${esc(c.state)}</code> ${esc(c.file)}</li>`).join('')}</ul>`
      : '<p class="dim">Nema izmenjenih taktika ni profila.</p>');
    $('repoBody').innerHTML = b.join('');
  }

  async function check() { $('repoBody').textContent = 'proveravam GitHub…'; render(await refresh(true) || {}); }

  async function toggle() {                           // stavka Repo u bočnoj traci (ponovni klik zatvara)
    const d = $('repoDialog'); d.hidden = !d.hidden;
    if (!d.hidden) await check();
  }

  showBanner();
  $('rbOpen').onclick = openFolder;
  $('rbClone').onclick = clone;
  $('rbLocal').onclick = () => { try { sessionStorage.setItem('eurosim.norepo', '1'); } catch (e) { /* ignore */ } showBanner(); };
  $('repoClose').onclick = () => { $('repoDialog').hidden = true; };
  $('repoFetch').onclick = check;
  $('repoPull').onclick = async () => {
    try { render(await api('/api/repo/pull', {})); setInfo(await api('/api/info')); onPulled(); msg('preuzeto najnovije sa GitHub-a'); refresh(); }
    catch (e) { alert(e.message); }
  };
  $('repoSave').onclick = async () => {
    try { render(await api('/api/repo/save', { message: $('repoMsg').value })); $('repoMsg').value = ''; msg('sačuvano na GitHub'); refresh(); }
    catch (e) { alert(e.message); }
  };
  refresh();
  return { toggle, refresh };
}
