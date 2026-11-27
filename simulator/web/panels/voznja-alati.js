// Red komandi Vožnja (Zadatak 4.4), isti za SIM i ROBOT: Taktika i Strana (zajedničke stavke, panels/stavke.js), pa
//   bez sesije:   „Izvori ▾“ (panels/izvori.js, Zadatak 5.1) · „▶ Pokreni sesiju“ (SIM: Live sa izabranim lidarom;
//                 ROBOT: otvara Izvori, gde su host, lozinka, Poveži i Virtuelni robot)
//   sesija radi:  Naoruži · Povuci činč · Test · brzina + Pauza (SIM) · Pošalji · Pošalji i pokreni (ROBOT) — svaka
//                 samo ako je sesija ima u mogućnostima (hello) · Prati · Završi (SIM) / Prekini vezu (ROBOT)
//   napomena „koristi se tekst iz editora (nesačuvan)“ dok Live / Pošalji koriste nesačuvan tekst editora.
// Šta se vidi računa core/voznja.js (voznjaTools) iz store-a; ponašanje (startLive, liveSend...) je u app.js preko
// istih id-jeva. STOP nije ovde: traka (■ STOP) i Esc, iz svakog prostora.
import { registerPanel } from '../core/panels.js';
import { voznjaTools, TOOL_IDS } from '../core/voznja.js';

registerPanel({
  id: 'voznja-alati', title: 'Vožnja: alati', workspaces: ['voznja'], region: 'tool', priority: 10, open: true,
  shared: ['taktika', 'strana'],
  mount: (el, ctx) => {
    const $ = id => document.getElementById(id);
    el.className += ' tool-row';
    const slot = name => { const s = document.createElement('span'); s.dataset.slot = name; return s; };
    el.append(slot('taktika'), slot('strana'), ...['izvori', 'start', 'arm', 'cord', 'test', 'speed', 'pause', 'push', 'run',
      'follow', 'end', 'note'].map(k => $(TOOL_IDS[k])));
    const start = $('sessStart'), end = $('endBtn');
    let last = '';
    const render = st => {                             // store se menja često (svaka poruka sesije): samo na promenu
      const v = voznjaTools(st), key = JSON.stringify(v);
      if (key === last) return;
      last = key;
      for (const [k, id] of Object.entries(TOOL_IDS)) $(id).hidden = !v[k];
      start.title = v.kind === 'robot' ? 'Poveži se sa robotom (pravim ili virtuelnim): otvara Izvori (host, lozinka, Poveži, Virtuelni robot)'
        : 'Pokreni simulaciju uživo sa izabranim izvorima (Izvori ▾): ESP ekran i tasteri, činč, pomeranje protivnika dok vozi';
      end.textContent = v.endLabel;
      end.title = v.kind === 'robot' ? 'Prekini vezu sa robotom; sesija ostaje kao snimak' : 'Završi sesiju; ostaje kao snimak koji možeš da pustiš ili sačuvaš';
    };
    ctx.store.subscribe(render);
    render(ctx.store.get());
  },
});
