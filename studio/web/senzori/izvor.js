// Senzori: odakle blok dobija podatke i zašto ih nema. Bez DOM-a, da ga može da uveze i `node --test`.
//   viewMode(st)                    {mode: 'robot'|'sim'|'hibrid'|'snimak'|'nista', text}  zaglavlje Senzora
//   blockSource(block, st, has)     {src: 'pravo'|'sim'|'snimak'|null, reason, note}       oznaka bloka
//   REASONS                         razlozi "nepovezano" za pravog robota, po id-u bloka
//   SIM_REASONS                     razlozi u simulaciji (i hibridu), po id-u bloka
//
// st = {session, sens, lidarScan}: session = null | {kind: 'sim'|'robot', host, virtual, lidar: 'sim'|'robot'|'file'},
//   sens = null | {run, t, replay, name} (t je u ms, kao run.cols.t; u tekstu se piše u sekundama), lidarScan = poslednji krug lidara ili null.
// block = {id, part: 'pogon'|'lidar'|'ir'|'mehanizmi'|null, fields, simFields?, notes?: {robot?: {[polje]: tekst}}}:
//   fields = polja koja blok traži (`'@lidar'` = stigao je krug lidara; `'@mec'` = stanje meča (telemetrija ESP-a ili kolona mec); [] = blok ne zavisi od polja, npr. veza);
//   simFields (nije obavezno) zamenjuje fields u simulaciji, hibridu i puštanju snimka simulacije.
// has(polje) -> bool: da li polje stvarno stiže (pozivalac odlučuje; za '@lidar' pita se da li snimak ima krugove lidara).

export const REASONS = {
  robot: 'ESP ga još ne šalje laptopu (1 polje u telemetriji)',
  pid: 'Nucleo ga ne šalje (firmver)',
  enkoderi: 'Nucleo ga ne šalje (firmver)',
  napajanje: 'INA3221 nije podešen',
  aktuatori: 'ESP ih još ne šalje laptopu',
  ulazi: 'ESP ih još ne šalje laptopu',
};
export const SIM_REASONS = {
  napajanje: 'nema simulacije (samo pravi robot)',
  lidar: 'na ESP-u: Meni → Lidar test',
};
const R_NISTA = 'nije povezano';
const R_SNIMAK = 'nije snimljeno';
const R_NUCLEO = 'Nucleo ne javlja (nema poze)';
const R_LIDAR = 'lidar ugašen: Upali lidar';
const R_ROBOT = 'robot ga još ne šalje';
const R_SIM = 'nema podataka u simulaciji';

function mode(st) {
  const s = st && st.session;
  if (s) return s.kind === 'robot' ? 'robot' : (s.lidar === 'robot' || s.lidar === 'file') ? 'hibrid' : 'sim';
  return st && st.sens && st.sens.replay ? 'snimak' : 'nista';
}

// Prelaz stanja „pušten snimak“ (play.replay u app.js): puštanje ga pali i pauza ga ne gasi; gase ga kraj snimka, dugme
// Uživo, učitavanje drugog snimka i početak sesije. Događaji: 'play' | 'pause' | 'seek' | 'end' | 'live' | 'load' | 'session'.
export function nextReplay(replay, ev) {
  if (ev === 'play') return true;
  if (ev === 'end' || ev === 'live' || ev === 'load' || ev === 'session') return false;
  return !!replay;
}

export function viewMode(st) {
  const m = mode(st), s = st && st.session;
  if (m === 'robot') return { mode: m, text: 'Prikazuje: ' + (s.virtual ? 'virtuelni robot' : 'pravi robot · ' + s.host) };
  if (m === 'sim') return { mode: m, text: 'Prikazuje: simulacija (Vožnja SIM) · ovo nije pravi robot' };
  if (m === 'hibrid') {
    const lidar = s.lidar === 'file' ? 'iz snimka' : 'sa pravog robota';
    return { mode: m, text: `Prikazuje: hibrid · lidar ${lidar}, ostalo simulirano` };
  }
  if (m === 'snimak') {
    const t = (Number(st.sens.t || 0) / 1000).toFixed(1).replace('.', ',');
    return { mode: m, text: `Prikazuje: snimak${st.sens.name ? ' ' + st.sens.name : ''} · ${t} s` };
  }
  return { mode: 'nista', text: 'Ništa nije povezano: Poveži robota ili pokreni simulaciju u Vožnji' };
}

const res = (src, reason = null, note = null) => ({ src, reason, note });
const anyHas = (fields, has) => fields.some(f => has(f));

export function blockSource(block, st, has) {
  const m = mode(st);
  if (m === 'nista') return res(null, R_NISTA);
  const id = block.id, fields = block.fields || [];
  const isLidar = fields.includes('@lidar');
  // Polja koja se gledaju: u simulaciji (i u snimku simulacije) simFields ako ih blok ima.
  const origin = st.sens && st.sens.run && st.sens.run.meta && st.sens.run.meta.origin;
  const simLike = m === 'sim' || m === 'hibrid' || (m === 'snimak' && !(origin && origin.engine === 'robot'));
  const want = simLike && block.simFields ? block.simFields : fields;

  if (m === 'robot') {
    if (!fields.length) return res('pravo');
    if (isLidar) {
      return st.lidarScan || has('@lidar') ? res('pravo') : res(null, R_LIDAR);
    }
    const run = st.sens && st.sens.run;
    if (block.part === 'pogon' && !(run && run.cols && run.cols.t && run.cols.t.length)) return res(null, R_NUCLEO);
    if (!anyHas(want, has)) return res(null, REASONS[id] || R_ROBOT);
    const notes = block.notes && block.notes.robot;
    const miss = notes && fields.find(f => notes[f] && !has(f));
    return res('pravo', null, miss ? notes[miss] : null);
  }
  if (m === 'snimak') {
    if (!want.length) return res('snimak');
    return anyHas(want, has) ? res('snimak') : res(null, R_SNIMAK);
  }
  // sim i hibrid
  if (isLidar && m === 'hibrid') return res(st.session.lidar === 'file' ? 'snimak' : 'pravo');
  if (!want.length) return res('sim');
  if (anyHas(want, has)) return res('sim');
  return res(null, SIM_REASONS[id] || R_SIM);
}
