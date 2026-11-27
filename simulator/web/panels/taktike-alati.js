// Red komandi Taktika: Taktika i Strana (zajedničke stavke, panels/stavke.js), meč | test (nad skrivenim #mode),
// ▶ Pokreni (#run, i Ctrl+Enter), „✎ Editor“ (#edOpen, samo dok je editor zatvoren) i auto-simulacija (#autoSim,
// samo dok je editor otvoren). Ponašanje (simulate, editor) ostaje u app.js, preko istih id-jeva.
import { registerPanel } from '../core/panels.js';
import { segmented } from '../shell/segmented.js';

registerPanel({
  id: 'taktike-alati', title: 'Taktike: alati', workspaces: ['taktike'], region: 'tool', priority: 10, open: true,
  shared: ['taktika', 'strana'],
  mount: el => {
    const $ = id => document.getElementById(id);
    el.className += ' tool-row';
    const slot = name => { const s = document.createElement('span'); s.dataset.slot = name; return s; };
    const mode = $('mode');
    mode.hidden = true;
    const modeSeg = segmented(mode, { id: 'modeSeg', title: 'Kako se pokreće',
      labels: { mec: 'meč', test: 'test' },
      titles: { mec: 'Meč: naoružaj, povuci činč, 100 s (kao na takmičenju)', test: 'Test: taktika se pokreće odmah, bez meča' } });
    const auto = document.createElement('label');
    auto.id = 'autoSimWrap';
    auto.className = 'ti-label small';
    auto.title = 'Pokreni pravu simulaciju sama kad prestaneš da kucaš (kratke taktike)';
    auto.append($('autoSim'), ' auto-simulacija');
    el.append(slot('taktika'), slot('strana'), modeSeg, mode, $('run'), $('edOpen'), auto);
  },
});
