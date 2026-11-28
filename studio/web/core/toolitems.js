// Zajedničke stavke reda komandi (npr. Taktika, Strana): JEDAN DOM čvor koji koristi više panela-alatki (Taktike,
// Vožnja, ...). Čvor može da bude samo na jednom mestu, pa ga okvir (shell/layout.js) pri promeni prostora PREMESTI
// u panel tog prostora koji ga navodi u svom polju `shared` (isti <select>, isti slušaoci; app.js radi kroz id-jeve).
//   registerToolItem({id, title, mount(el, ctx)})   stavka se prijavi jednom; okvir joj napravi koren
//                                                    (span.tool-item#ti-<id>) i pozove mount JEDNOM
//   panel: registerPanel({..., region: 'tool', shared: ['taktika', 'strana']}); u svom korenu može da ima mesto
//          <span data-slot="taktika"></span> (inače stavka ide na kraj korena)
//   sharedHomes(panels) -> {itemId: panelId}   prvi panel u listi koji navodi stavku (lista = panelsFor(ws): po
//                                               regionu pa po prioritetu, pa pobeđuje važniji panel)
//   sharedMoves(where, homes) -> [{id, from, to}]   šta treba premestiti: stavka bez doma u novom prostoru ostaje
//                                                    gde jeste (skrivena zajedno sa svojim panelom), ne seli se
// Bez DOM-a na nivou modula, da ga uveze i `node --test`.

export function createToolItems() {
  const items = new Map();
  return {
    registerToolItem(it) {
      if (!it || !it.id) throw new Error('stavka bez id');
      if (items.has(it.id)) throw new Error('stavka već postoji: ' + it.id);
      if (typeof it.mount !== 'function') throw new Error(`stavka ${it.id}: nema mount`);
      const item = { title: it.id, ...it };
      items.set(it.id, item);
      return item;
    },
    get(id) { return items.get(id) || null; },
    all() { return [...items.values()]; },
  };
}

export function sharedHomes(panels) {
  const homes = {};
  for (const p of panels || []) {
    for (const id of p.shared || []) if (!(id in homes)) homes[id] = p.id;
  }
  return homes;
}

export function sharedMoves(where, homes) {
  const moves = [];
  for (const id of Object.keys(homes)) {
    const from = where[id] || null;
    if (from !== homes[id]) moves.push({ id, from, to: homes[id] });
  }
  return moves;
}

const registry = createToolItems();
export const registerToolItem = it => registry.registerToolItem(it);
export const allToolItems = () => registry.all();
