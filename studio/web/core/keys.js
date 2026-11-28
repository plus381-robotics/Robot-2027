// Prečice sa tastature, bez DOM-a (da ga uveze i `node --test`). Slušaoce postavlja shell/layout.js (installKeys,
// installEscStop); vreme (razmak, strelice), Ctrl+Enter i Ctrl+S su u app.js / editor.js.
//   wsForKey(e)    Alt+1..4 -> radni prostor, redom kao u bočnoj traci (Taktike, Senzori, Vožnja, Snimci); inače null
//   isHelpKey(e)   „?“ -> prozorčić Prečice (Pomoć u bočnoj traci)
//   isTyping(el)   fokus je u polju za kucanje ili u editoru: „?“ se tada kuca, ne otvara spisak
//   timeKey(e, ws) vreme snimka i ▶ Pokreni (app.js): 'play' | 'frame-' | 'frame+' | 'step-' | 'step+' | 'home' | 'end' |
//                  'run' | null. Senzori nemaju vreme (tasteri ne rade ništa); Ctrl+Enter samo u Taktikama.
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

export function timeKey(e, ws) {
  if (!e) return null;
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) return ws === 'taktike' ? 'run' : null;
  if (ws === 'senzori') return null;
  switch (e.key) {
    case ' ': return 'play';
    case 'ArrowLeft': return e.shiftKey ? 'step-' : 'frame-';
    case 'ArrowRight': return e.shiftKey ? 'step+' : 'frame+';
    case 'Home': return 'home';
    case 'End': return 'end';
    default: return null;
  }
}

export const SHORTCUTS = [
  ['Esc', 'STOP dok radi sesija (iz svakog prostora, i iz editora)'],
  ['Ctrl+Enter', '▶ Pokreni: simulacija taktike (u Taktikama)'],
  ['Ctrl+S', 'Sačuvaj taktiku (u editoru; Ctrl+Shift+S: Sačuvaj kao…)'],
  ['Razmak', 'vreme: pusti / pauza (tasteri za vreme ne rade u Senzorima)'],
  ['← / →', 'vreme: frejm nazad / napred'],
  ['Shift+← / →', 'vreme: korak nazad / napred'],
  ['Home / End', 'vreme: početak / kraj snimka'],
  ['Alt+1 … 4', 'prostori: Taktike, Senzori, Vožnja, Snimci'],
  ['dupli klik na stolu', 'kopiraj koordinate (za taktiku)'],
  ['Alt+klik na stolu', 'ubaci tačku goto(x, y) u editor (Taktike)'],
  ['?', 'ovaj spisak'],
];
