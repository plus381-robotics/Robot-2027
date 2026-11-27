// Testovi za web/core/regions.js: gde ide koji panel i stanje kartica (sklopljeno/otvoreno) po radnom prostoru.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRegistry } from '../../web/core/panels.js';
import { placePanels, isCard, defaultOpen, cardsOpen, setCard, loadCards, saveCards, CARDS_KEY, MAX_OPEN }
  from '../../web/core/regions.js';

// Isti paneli kao u web/panels/ (Zadaci 4.1–4.3), bez mount-a.
function registry43() {
  const r = createRegistry();
  const all = ['taktike', 'voznja', 'snimci'];
  r.registerPanel({ id: 'stari-alati', workspaces: all, region: 'tool', priority: 90, open: true, shared: ['taktika', 'strana'] });
  r.registerPanel({ id: 'taktike-alati', workspaces: ['taktike'], region: 'tool', priority: 10, open: true, shared: ['taktika', 'strana'] });
  r.registerPanel({ id: 'teren', workspaces: all, region: 'main', priority: 20, open: true });
  r.registerPanel({ id: 'editor', workspaces: ['taktike'], region: 'main', priority: 10, open: true });
  r.registerPanel({ id: 'korak', workspaces: ['voznja', 'snimci'], region: 'side', priority: 10, open: true });
  r.registerPanel({ id: 'koraci', workspaces: all, region: 'side', priority: 20, open: true, grow: true });
  r.registerPanel({ id: 'dnevnik', workspaces: all, region: 'side', priority: 30, open: ['voznja', 'snimci'], grow: true });
  r.registerPanel({ id: 'stanje', workspaces: ['voznja', 'snimci'], region: 'side', priority: 40, open: false, shrink: true });
  r.registerPanel({ id: 'vreme', workspaces: all, region: 'bottom', priority: 10, open: true });
  r.registerPanel({ id: 'grafici', workspaces: all, region: 'bottom', priority: 20, collapsible: true, open: ['snimci'] });
  r.registerPanel({ id: 'test-dela', workspaces: ['test'], region: 'main', priority: 1, open: true });
  return r;
}

const ids = place => Object.fromEntries(Object.entries(place).map(([k, v]) => [k, v.map(p => p.id)]));

test('placePanels: paneli po regionu, u regionu po prioritetu (editor levo od terena)', () => {
  const r = registry43();
  assert.deepEqual(ids(placePanels(r.panelsFor('taktike'))), {
    tool: ['taktike-alati', 'stari-alati'], main: ['editor', 'teren'], side: ['koraci', 'dnevnik'], bottom: ['vreme', 'grafici'] });
  assert.deepEqual(ids(placePanels(r.panelsFor('voznja'))), {             // editor samo u Taktikama (Zadatak 4.3)
    tool: ['stari-alati'], main: ['teren'], side: ['korak', 'koraci', 'dnevnik', 'stanje'], bottom: ['vreme', 'grafici'] });
  assert.deepEqual(placePanels(r.panelsFor('snimci')).main.map(p => p.id), ['teren']);
  assert.deepEqual(placePanels(r.panelsFor('voznja')).side.map(p => p.id), ['korak', 'koraci', 'dnevnik', 'stanje']);
  assert.deepEqual(placePanels(r.panelsFor('snimci')).side.map(p => p.id), ['korak', 'koraci', 'dnevnik', 'stanje']);
  assert.deepEqual(ids(placePanels(r.panelsFor('test'))), { tool: [], main: ['test-dela'], side: [], bottom: [] });
  assert.deepEqual(ids(placePanels([])), { tool: [], main: [], side: [], bottom: [] });
});

test('placePanels: isti prioritet ostaje po redu u listi', () => {
  const r = createRegistry();
  r.registerPanel({ id: 'a', workspaces: ['voznja'], region: 'side', priority: 5 });
  r.registerPanel({ id: 'b', workspaces: ['voznja'], region: 'side', priority: 5 });
  r.registerPanel({ id: 'c', workspaces: ['voznja'], region: 'side', priority: 1 });
  assert.deepEqual(placePanels(r.panelsFor('voznja')).side.map(p => p.id), ['c', 'a', 'b']);
});

test('isCard / defaultOpen: bočni uvek kartica, donji samo sklopiv; open = bool ili lista prostora', () => {
  const r = registry43();
  const get = id => r.get(id);
  for (const id of ['korak', 'koraci', 'dnevnik', 'stanje']) assert.equal(isCard(get(id)), true);
  assert.equal(isCard(get('grafici')), true);
  assert.equal(isCard(get('vreme')), false);
  assert.equal(isCard(get('teren')), false);
  assert.equal(isCard(get('stari-alati')), false);
  assert.equal(isCard(get('taktike-alati')), false);
  assert.equal(defaultOpen(get('grafici'), 'taktike'), false);   // grafici sklopljeni u Taktikama
  assert.equal(defaultOpen(get('grafici'), 'voznja'), false);   // i u Vožnji (spec)
  assert.equal(defaultOpen(get('grafici'), 'snimci'), true);
  assert.equal(defaultOpen(get('dnevnik'), 'taktike'), false);   // Dnevnik sklopljen u Taktikama
  assert.equal(defaultOpen(get('dnevnik'), 'voznja'), true);
  assert.equal(defaultOpen(get('stanje'), 'snimci'), false);
  assert.equal(defaultOpen({ open: false }, 'voznja'), false);
});

test('cardsOpen: zapamćeno stanje ima prednost, inače podrazumevano; drugi prostor ne utiče', () => {
  const r = registry43();
  const tk = r.panelsFor('taktike');
  assert.deepEqual(cardsOpen(tk, 'taktike', {}), { koraci: true, dnevnik: false, grafici: false });
  const saved = setCard({}, 'taktike', 'grafici', true);
  assert.deepEqual(cardsOpen(tk, 'taktike', saved), { koraci: true, dnevnik: false, grafici: true });
  const vz = { korak: true, koraci: true, dnevnik: true, stanje: false, grafici: false };   // tri otvorene, Stanje sklopljeno
  assert.deepEqual(cardsOpen(r.panelsFor('voznja'), 'voznja', saved), vz);
  assert.deepEqual(cardsOpen(r.panelsFor('snimci'), 'snimci', {}), { ...vz, grafici: true });
  assert.equal(cardsOpen(r.panelsFor('snimci'), 'snimci', saved).grafici, true);
  const s2 = setCard(saved, 'snimci', 'grafici', false);
  assert.equal(cardsOpen(r.panelsFor('snimci'), 'snimci', s2).grafici, false);
  assert.equal(cardsOpen(tk, 'taktike', s2).grafici, true);
  assert.deepEqual(saved, { taktike: { grafici: true } });                  // setCard ne menja staro stanje
  assert.deepEqual(cardsOpen(r.panelsFor('test'), 'test', s2), {});
});

test('cardsOpen: najviše tri bočne kartice otvorene podrazumevano; zapamćene otvorene se broje', () => {
  const r = createRegistry();
  for (let i = 1; i <= 5; i++) r.registerPanel({ id: 'k' + i, workspaces: ['voznja'], region: 'side', priority: i, open: true });
  r.registerPanel({ id: 'g', workspaces: ['voznja'], region: 'bottom', collapsible: true, open: true });
  const list = r.panelsFor('voznja');
  assert.equal(MAX_OPEN, 3);
  assert.deepEqual(cardsOpen(list, 'voznja', {}), { k1: true, k2: true, k3: true, k4: false, k5: false, g: true });
  const saved = setCard(setCard({}, 'voznja', 'k5', true), 'voznja', 'k1', false);
  assert.deepEqual(cardsOpen(list, 'voznja', saved), { k1: false, k2: true, k3: true, k4: false, k5: true, g: true });
  const all = ['k1', 'k2', 'k3', 'k4'].reduce((s, id) => setCard(s, 'voznja', id, true), {});
  assert.deepEqual(cardsOpen(list, 'voznja', all), { k1: true, k2: true, k3: true, k4: true, k5: false, g: true });
});

test('loadCards / saveCards: ključ eurosim.cards, loše vrednosti se odbacuju, izuzetak -> prazno', () => {
  assert.equal(CARDS_KEY, 'eurosim.cards');
  const mem = new Map();
  const st = { getItem: k => (mem.has(k) ? mem.get(k) : null), setItem: (k, v) => mem.set(k, v) };
  assert.deepEqual(loadCards(st), {});
  saveCards(setCard({}, 'taktike', 'grafici', true), st);
  assert.deepEqual(JSON.parse(mem.get('eurosim.cards')), { taktike: { grafici: true } });
  assert.deepEqual(loadCards(st), { taktike: { grafici: true } });
  mem.set('eurosim.cards', JSON.stringify({ taktike: { grafici: 'da', koraci: false }, svasta: { x: true }, voznja: 5 }));
  assert.deepEqual(loadCards(st), { taktike: { koraci: false } });
  mem.set('eurosim.cards', '{ne json');
  assert.deepEqual(loadCards(st), {});
  const bad = { getItem() { throw new Error('blokirano'); }, setItem() { throw new Error('blokirano'); } };
  assert.deepEqual(loadCards(bad), {});
  assert.doesNotThrow(() => saveCards({ taktike: { grafici: true } }, bad));
  assert.deepEqual(loadCards(undefined), {});
});

// Zadatak 4.4: red komandi Vožnja, kartice ESP (when: espShown) i Postavka stola (when: stoShown).
test('4.4: Vožnja SIM/ROBOT — red komandi, ESP i Postavka stola po izvoru; podrazumevano otvorene', async () => {
  const { espShown, stoShown } = await import('../../web/core/voznja.js');
  const r = registry43();
  r.registerPanel({ id: 'voznja-alati', workspaces: ['voznja'], region: 'tool', priority: 10, open: true, shared: ['taktika', 'strana'] });
  r.registerPanel({ id: 'esp', workspaces: ['voznja'], region: 'side', priority: 5, open: true, when: espShown });
  r.registerPanel({ id: 'sto', workspaces: ['taktike', 'voznja'], region: 'side', priority: 25, open: false, when: stoShown });
  const sim = { drive: 'sim', session: null, caps: null };
  const vs = r.panelsFor('voznja', [], sim);
  assert.deepEqual(ids(placePanels(vs)).tool, ['voznja-alati', 'stari-alati']);
  assert.deepEqual(ids(placePanels(vs)).side, ['esp', 'korak', 'koraci', 'sto', 'dnevnik', 'stanje']);
  assert.deepEqual(cardsOpen(vs, 'voznja', {}), { esp: true, korak: true, koraci: true, sto: false, dnevnik: false, stanje: false, grafici: false });
  const robot = { drive: 'robot', session: { kind: 'robot' }, caps: ['lidar', 'push', 'run', 'stop'] };
  const vr = r.panelsFor('voznja', robot.caps, robot);
  assert.deepEqual(ids(placePanels(vr)).side, ['korak', 'koraci', 'dnevnik', 'stanje']);   // bez ESP i Postavke stola
  assert.deepEqual(cardsOpen(vr, 'voznja', {}), { korak: true, koraci: true, dnevnik: true, stanje: false, grafici: false });
  const tk = r.panelsFor('taktike', [], robot);                                         // Taktike: Postavka stola uvek
  assert.deepEqual(ids(placePanels(tk)).side, ['koraci', 'sto', 'dnevnik']);
  assert.deepEqual(cardsOpen(tk, 'taktike', {}), { koraci: true, sto: false, dnevnik: false, grafici: false });
});

// Zadatak 4.5: pravi paneli (web/panels/index.js se uvozi bez DOM-a): prostor Snimci — red komandi snimci-alati,
// kartica Snimci (lista) prva i otvorena; Korak sada i Dnevnik u Snimcima podrazumevano sklopljeni (mesto za listu),
// u Vožnji ostaju otvoreni.
test('4.5: Snimci — red komandi i kartica liste (pravi paneli)', async () => {
  await import('../../web/panels/index.js');
  const { panelsFor } = await import('../../web/core/panels.js');
  const sim = { drive: 'sim', session: null, caps: null };
  const sn = panelsFor('snimci', [], sim);
  assert.deepEqual(ids(placePanels(sn)), { tool: ['snimci-alati', 'stari-alati'], main: ['teren'],
    side: ['snimci', 'korak', 'koraci', 'dnevnik', 'stanje'], bottom: ['vreme', 'grafici'] });
  assert.deepEqual(cardsOpen(sn, 'snimci', {}), { snimci: true, korak: false, koraci: true, dnevnik: false, stanje: false, grafici: true });
  const vz = panelsFor('voznja', [], sim);
  assert.deepEqual(cardsOpen(vz, 'voznja', {}), { esp: true, korak: true, koraci: true, sto: false, dnevnik: false, stanje: false, grafici: false });
  const vr = panelsFor('voznja', ['lidar', 'push', 'run', 'stop'], { drive: 'robot', session: { kind: 'robot' } });
  assert.deepEqual(cardsOpen(vr, 'voznja', {}), { korak: true, koraci: true, dnevnik: true, stanje: false, grafici: false });
  for (const ws of ['taktike', 'voznja', 'test']) {                     // lista i njen red komandi samo u Snimcima
    const l = panelsFor(ws, [], sim).map(p => p.id);
    assert.ok(!l.includes('snimci') && !l.includes('snimci-alati'), ws);
  }
});
