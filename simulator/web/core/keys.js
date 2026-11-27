// Prečice sa tastature, bez DOM-a (da ga uveze i `node --test`). Slušaoce postavlja shell/layout.js (installKeys,
// installEscStop); vreme (razmak, strelice), Ctrl+Enter i Ctrl+S su u app.js / editor.js.
//   wsForKey(e)    Alt+1..4 -> radni prostor, redom kao u bočnoj traci (Taktike, Test dela, Vožnja, Snimci); inače null
//   isHelpKey(e)   „?“ -> prozorčić Prečice (Pomoć u bočnoj traci)
//   isTyping(el)   fokus je u polju za kucanje ili u editoru: „?“ se tada kuca, ne otvara spisak
//   SHORTCUTS      [[tasteri, šta radi]] za prozorčić Prečice

import { WORKSPACES } from './panels.js';

export function wsForKey(e) {
  if (!e || !e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || e.repeat) return null;
  const m = /^Digit([1-4])$/.exec(e.code || '') || /^([1-4])$/.exec(e.key || '');   // code: i na rasporedima gde Alt menja znak
  return m ? WORKSPACES[+m[1] - 1] : null;
}

export const isHelpKey = e => !!e && e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.repeat;

export function isTyping(el) {
  if (!el) return false;
  if (el.isContentEditable || (el.closest && el.closest('.cm-editor'))) return true;
  const tag = el.tagName;
  return tag === 'TEXTAREA' || tag === 'SELECT' || (tag === 'INPUT' && !['range', 'checkbox', 'button', 'radio'].includes(el.type));
}

export const SHORTCUTS = [
  ['Esc', 'STOP dok radi sesija (iz svakog prostora, i iz editora)'],
  ['Ctrl+Enter', '▶ Pokreni: simulacija taktike'],
  ['Ctrl+S', 'Sačuvaj taktiku (u editoru; Ctrl+Shift+S: Sačuvaj kao…)'],
  ['Razmak', 'vreme: pusti / pauza'],
  ['← / →', 'vreme: frejm nazad / napred'],
  ['Shift+← / →', 'vreme: korak nazad / napred'],
  ['Home / End', 'vreme: početak / kraj snimka'],
  ['Alt+1 … 4', 'prostori: Taktike, Test dela, Vožnja, Snimci'],
  ['dupli klik na stolu', 'kopiraj koordinate (za taktiku)'],
  ['Alt+klik na stolu', 'ubaci tačku goto(x, y) u editor (Taktike)'],
  ['?', 'ovaj spisak'],
];
