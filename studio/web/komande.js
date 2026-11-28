// Kartica Komande u editoru (plan S4; Zadatak 4.6 iz app.js): Gambit Micro komande običnim jezikom, po grupama, sa
// parametrima, primerom, malom slikom stola za komande sa x, y i „Ubaci u kod“. Opisi iz eurosim/apidoc.py (/api/tacapi),
// potpisi iz tac.py.
//   renderCommands(listEl, tapi, filter, insert(line))
import { esc } from './core/api.js';

function tableSvg(ex) {                            // mala slika stola sa osama i tačkom iz primera
  const m = /\((\d+),\s*(\d+)/.exec(ex || '');
  const W = 240, H = 160, sx = W / 3000, sy = H / 2000;
  const pt = m ? [+m[1], +m[2]] : null;
  return `<svg class="tbl" viewBox="-52 -8 ${W + 62} ${H + 30}" width="${W + 62}" height="${H + 30}">
    <rect x="0" y="0" width="${W}" height="${H}" fill="#24302b" stroke="#6b7785"/>
    <rect x="0" y="${H - 1250 * sy}" width="${500 * sx}" height="${500 * sy}" fill="#f7b50055"/>
    <rect x="${W - 500 * sx}" y="${H - 1250 * sy}" width="${500 * sx}" height="${500 * sy}" fill="#2f7fc155"/>
    <text x="-4" y="${H + 12}" fill="#c8d0da" font-size="10" text-anchor="end">0,0</text>
    <text x="${W}" y="${H + 12}" fill="#ff9b9b" font-size="10" text-anchor="end">x 3000 →</text>
    <text x="-4" y="6" fill="#9bee9b" font-size="10" text-anchor="end">y 2000</text>
    ${pt ? `<line x1="0" y1="${H - pt[1] * sy}" x2="${pt[0] * sx}" y2="${H - pt[1] * sy}" stroke="#ffd166" stroke-dasharray="3 2"/>
    <line x1="${pt[0] * sx}" y1="${H}" x2="${pt[0] * sx}" y2="${H - pt[1] * sy}" stroke="#ffd166" stroke-dasharray="3 2"/>
    <circle cx="${pt[0] * sx}" cy="${H - pt[1] * sy}" r="4" fill="#ffd166"/>
    <text x="${pt[0] * sx + 6}" y="${H - pt[1] * sy - 5}" fill="#ffd166" font-size="10">x=${pt[0]}, y=${pt[1]}</text>` : ''}
    <text x="${250 * sx}" y="${H - 1000 * sy + 3}" fill="#f7b500" font-size="9" text-anchor="middle">start</text>
  </svg>`;
}

const ORDER = ['Motion', 'Actuators', 'Waiting', 'Sensors', 'Match time', 'Where is the robot', 'Other'];
const TITLE = { Motion: 'Kretanje', Actuators: 'Aktuatori', Waiting: 'Čekanje', Sensors: 'Senzori', 'Match time': 'Vreme meča',
  'Where is the robot': 'Gde je robot', Other: 'Ostalo' };

export function renderCommands(listEl, tapi, filter, insert) {
  const f = (filter || '').toLowerCase().trim();
  const groups = {};
  for (const [name, fn] of Object.entries(tapi.funcs)) {
    const h = fn.help || { group: 'Other', say: fn.doc, params: [], ret: '', example: '' };
    if (f && !(name + ' ' + h.say + ' ' + fn.doc).toLowerCase().includes(f)) continue;
    (groups[h.group] = groups[h.group] || []).push([name, fn, h]);
  }
  const parts = [`<p class="coords">${esc(tapi.coords || '')}</p>`];
  for (const g of ORDER.concat(Object.keys(groups).filter(k => !ORDER.includes(k)))) {
    if (!groups[g]) continue;
    parts.push(`<h4>${esc(TITLE[g] || g)}</h4>`);
    for (const [name, fn, h] of groups[g]) {
      const params = (h.params || []).map(([p, t]) => {
        const d = (fn.params.find(x => x[0] === p) || [])[1];
        const note = d == null || /default|optional/i.test(t) ? '' : d === 'None' ? ' <span class="dim">(nije obavezno)</span>' : ` <span class="dim">(podrazumevano ${esc(d)})</span>`;
        return `<tr><td><code>${esc(p)}</code>${d == null ? ' <span class="req">obavezno</span>' : ''}</td><td>${esc(t)}${note}</td></tr>`;
      }).join('');
      parts.push(`<details class="cmd"${f ? ' open' : ''}><summary><code>${esc(name)}</code> <span>${esc(h.say)}</span></summary>
        <div class="sig"><code>${esc(fn.sig)}</code></div>
        ${params ? `<table>${params}</table>` : ''}
        ${h.ret ? `<p><b>Vraća:</b> ${esc(h.ret)}</p>` : ''}
        ${h.xy ? tableSvg(h.example) : ''}
        ${h.example ? `<pre>${esc(h.example)}</pre><button class="ins" data-ex="${esc(h.example.split('\n')[0].split('#')[0].trim())}">Ubaci u kod</button>` : ''}
      </details>`);
    }
  }
  parts.push(`<h4>Imena aktuatora</h4><p>${tapi.actuators.map(a => `<code>${esc(a)}</code>`).join(' ') || '–'} <span class="dim">(ESP32/config.py ACTUATORS)</span></p>`);
  listEl.innerHTML = parts.join('');
  for (const b of listEl.querySelectorAll('button.ins')) b.onclick = () => insert(b.dataset.ex);
}
