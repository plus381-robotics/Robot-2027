// Red komandi Snimci (Zadatak 4.5): „Sačuvaj snimak…“ (#save), „📌 Referenca“ (#cmpPin: snimak koji gledaš postaje
// referenca), „Uporedi sa…“ (#cmpRun: sačuvan snimak kao referenca), ime reference (#cmpName) i ✕ (#cmpClear).
// Ranije: meni „⋯ Runs“ u starom redu i plutajući #cmpTools nad stolom. Ponašanje ostaje u app.js preko istih id-jeva.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'snimci-alati', title: 'Snimci: alati', workspaces: ['snimci'], region: 'tool', priority: 10, open: true,
  mount: el => {
    const $ = id => document.getElementById(id);
    el.className += ' tool-row';
    el.append($('save'), $('cmpPin'), $('cmpRun'), $('cmpName'), $('cmpClear'));
  },
});
