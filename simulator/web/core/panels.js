// Registar panela (okvir varijante A): panel se prijavi jednom, okvir ga prikaže u radnim prostorima koje navodi.
//   registerPanel({id, title, workspaces: ['taktike', ...], region: 'main'|'side'|'bottom'|'tool', priority,
//                  needs: [cap|dataKey], open, mount(el, ctx), update(state)})
//     open: true/false ili lista prostora u kojima je kartica podrazumevano otvorena (core/regions.js);
//     dodatno (shell/layout.js): collapsible (donji panel kao kartica), grow (kartica popunjava bočnu kolonu),
//     shown(el, ctx) posle svakog prikaza (npr. teren: ponovo izmeri sto)
//   panelsFor(workspace, caps) -> [panel]   po regionu, pa po priority (manji broj = važniji, ide prvi);
//                                            needs koji nije u caps -> {..., disabled: true, reason: 'potrebno: ...'}
//   allPanels() -> [panel]                     svi prijavljeni (okvir ih montira jednom, na početku)
//   ctx = { store, command(c), go(workspace), setDrive, openSources, setBadge(id, text), legacy }
// Paneli su u web/panels/ (jedan fajl po panelu, prijava pri uvozu panels/index.js).
// Bez DOM-a na nivou modula, da ga uveze i `node --test`.

export const WORKSPACES = ['taktike', 'test', 'voznja', 'snimci'];
export const WS_KEY = 'eurosim.ws';                 // localStorage: poslednji radni prostor
export const REGIONS = ['main', 'side', 'bottom', 'tool'];

export function createRegistry() {
  const panels = new Map();
  return {
    registerPanel(p) {
      if (!p || !p.id) throw new Error('panel bez id');
      if (panels.has(p.id)) throw new Error('panel već postoji: ' + p.id);
      const region = p.region || 'side';
      if (!REGIONS.includes(region)) throw new Error(`panel ${p.id}: nepoznat region ${region}`);
      const ws = p.workspaces || [];
      for (const w of ws) if (!WORKSPACES.includes(w)) throw new Error(`panel ${p.id}: nepoznat radni prostor ${w}`);
      const panel = { title: p.id, priority: 100, needs: [], open: false, ...p, region, workspaces: [...ws] };
      panels.set(p.id, panel);
      return panel;
    },
    panelsFor(workspace, caps = []) {
      const have = caps instanceof Set ? caps : new Set(caps);
      const order = (a, b) => REGIONS.indexOf(a.region) - REGIONS.indexOf(b.region) || a.priority - b.priority;
      return [...panels.values()]
        .filter(p => p.workspaces.includes(workspace))
        .sort(order)                                  // stabilno: isti prioritet ostaje po redu prijave
        .map(p => {
          const missing = (p.needs || []).filter(n => !have.has(n));
          return missing.length ? { ...p, disabled: true, reason: 'potrebno: ' + missing.join(', ') } : { ...p, disabled: false, reason: '' };
        });
    },
    get(id) { return panels.get(id) || null; },
    all() { return [...panels.values()]; },
  };
}

const registry = createRegistry();
export const registerPanel = p => registry.registerPanel(p);
export const panelsFor = (workspace, caps) => registry.panelsFor(workspace, caps);
export const getPanel = id => registry.get(id);
export const allPanels = () => registry.all();

// Radni prostor u localStorage (svaki pristup u try/catch: privatni prozor, blokiran storage).
export function loadWorkspace(storage = globalThis.localStorage, def = 'taktike') {
  try {
    const w = storage && storage.getItem(WS_KEY);
    return WORKSPACES.includes(w) ? w : def;
  } catch (e) { return def; }
}

export function saveWorkspace(ws, storage = globalThis.localStorage) {
  try { if (storage && WORKSPACES.includes(ws)) storage.setItem(WS_KEY, ws); } catch (e) { /* ignore */ }
}
