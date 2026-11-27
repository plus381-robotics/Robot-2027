// Raspored regiona (varijanta A) bez DOM-a, da ga uveze i `node --test`. DOM radi shell/layout.js.
//   placePanels(list)              list = panelsFor(ws) -> {tool, main, side, bottom}: paneli po regionu, po prioritetu
//   isCard(p)                      bočni paneli su uvek kartice; donji samo sa `collapsible: true` (npr. grafici)
//   defaultOpen(p, ws)             p.open: true/false ili lista prostora u kojima je kartica podrazumevano otvorena
//   cardsOpen(list, ws, saved)     {id: otvorena?} za kartice tog prostora: zapamćeno stanje, inače podrazumevano;
//                                  bočnih otvorenih podrazumevano najviše MAX_OPEN (zapamćeno korisnikovo se poštuje)
//   setCard(saved, ws, id, open)   novo stanje (staro se ne menja)
//   loadCards() / saveCards(saved) localStorage `eurosim.cards` = {ws: {id: bool}}, svaki pristup u try/catch

import { WORKSPACES } from './panels.js';

export const CARDS_KEY = 'eurosim.cards';
export const MAX_OPEN = 3;
export const REGION_ORDER = ['tool', 'main', 'side', 'bottom'];

export function placePanels(list) {
  const out = { tool: [], main: [], side: [], bottom: [] };
  for (const p of list) if (out[p.region]) out[p.region].push(p);
  for (const r of REGION_ORDER) out[r].sort((a, b) => a.priority - b.priority);      // stabilno
  return out;
}

export const isCard = p => p.region === 'side' || (p.region === 'bottom' && !!p.collapsible);

export function defaultOpen(p, ws) {
  return Array.isArray(p.open) ? p.open.includes(ws) : !!p.open;
}

export function cardsOpen(list, ws, saved = {}) {
  const mine = (saved && saved[ws]) || {};
  const cards = list.filter(isCard), res = {};
  let n = cards.filter(p => p.region === 'side' && mine[p.id] === true).length;
  for (const p of cards) {
    if (typeof mine[p.id] === 'boolean') { res[p.id] = mine[p.id]; continue; }
    let o = defaultOpen(p, ws);
    if (o && p.region === 'side') { if (n >= MAX_OPEN) o = false; else n++; }
    res[p.id] = o;
  }
  return res;
}

export function setCard(saved, ws, id, open) {
  return { ...saved, [ws]: { ...((saved && saved[ws]) || {}), [id]: !!open } };
}

function clean(v) {                                    // samo poznati prostori i bool vrednosti
  const out = {};
  if (!v || typeof v !== 'object') return out;
  for (const w of WORKSPACES) {
    const m = v[w];
    if (!m || typeof m !== 'object') continue;
    for (const [id, o] of Object.entries(m)) if (typeof o === 'boolean') (out[w] || (out[w] = {}))[id] = o;
  }
  return out;
}

export function loadCards(storage = globalThis.localStorage) {
  try { return clean(JSON.parse((storage && storage.getItem(CARDS_KEY)) || '{}')); } catch (e) { return {}; }
}

export function saveCards(saved, storage = globalThis.localStorage) {
  try { if (storage) storage.setItem(CARDS_KEY, JSON.stringify(clean(saved))); } catch (e) { /* ignore */ }
}
