// Red komandi Snimci (Zadatak 4.5): Taktika i Strana (zajedničke stavke, panels/stavke.js; kao ranije u starom redu:
// promena strane ponovo simulira prikazan snimak), „Sačuvaj snimak…“ (#save), „📌 Referenca“ (#cmpPin: snimak koji
// gledaš postaje referenca), „Uporedi sa…“ (#cmpRun: sačuvan snimak kao referenca), ime reference (#cmpName) i ✕
// (#cmpClear). Ranije: meni „⋯ Runs“ u starom redu i plutajući #cmpTools nad stolom. Ponašanje ostaje u app.js preko
// istih id-jeva.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'snimci-alati', title: 'Snimci: alati', workspaces: ['snimci'], region: 'tool', priority: 10, open: true,
  shared: ['taktika', 'strana'],
  mount: el => {
    const $ = id => document.getElementById(id);
    el.className += ' tool-row';
    const slot = name => { const s = document.createElement('span'); s.dataset.slot = name; return s; };
    el.append(slot('taktika'), slot('strana'), $('save'), $('cmpPin'), $('cmpRun'), $('cmpName'), $('cmpClear'));
  },
});
