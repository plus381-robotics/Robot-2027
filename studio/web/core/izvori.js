// Izvori (Zadatak 5.1) bez DOM-a, da ga uveze i `node --test`: koje kombinacije izvora po delu robota postoje, šta je
// sivo i zašto, i šta izbor znači za sesiju. Blok Izvori je panels/izvori.js (prozorčić iz bočne trake i iz reda komandi
// Vožnja); ovde je samo logika. Stanje (piše ga app.js / izvori.js):
//   drive    'sim' | 'robot'                         pogon: SIM (simulacija na laptopu) ili ROBOT (pravi/virtuelni robot)
//   sources  {lidar: 'sim'|'pravi'|'snimak', file}   izbor lidara uz simulirani pogon (hibrid); file = snimak lidara
//                                                    (studio/lidar/*.jsonl.gz); localStorage `eurosim.sources`
//   lidarFiles [ime]                                 snimci lidara (GET /api/info lidar_files); podrazumevani `files`
//   session  null | {kind, lidar, host}              sesija radi: blok se samo čita
//   helloSource  null | {engine, parts}              šta sesija stvarno koristi (poruka hello sa servera)
//
// Delovi i izvori (docs/redizajn-ui.md, „Izvor podataka po delu“): pogon, lidar, IR, mehanizmi, protivnici; svaki sim /
// pravi / snimak / lažiran. Danas rade a (sve sim), b (hibrid: lidar pravi ili iz snimka) i d (sve pravo = sesija
// ROBOT). c (robot + lažiran mehanizam) i „lažiran“ dolaze sa Fazom 6 (ESP). Pravi pogon uz simulirani lidar, IR ili
// protivnika se ne podržava.
//
//   izvoriView(st, files) -> {readOnly, preset, presets: [{id, label, title, on, disabled, reason}],
//                             rows: [{id, name, value, options: [{v, label, on, disabled, reason}], why}],
//                             lidarFile: {shown, value, files, disabled}, connect: {show, usedBy}, note}
//   applyPreset(id, st, files) -> {drive, sources} | null (sivo / sesija radi)
//   applyOption(part, v, st, files) -> {drive, sources} | null
//   normSources(src, files) -> {lidar, file}   ispravan izbor (snimak koga više nema -> prvi snimak ili sim)
//   lidarSpec(sources, files) -> 'sim' | 'robot' | 'file:<ime>'   (upit `lidar` za /ws/session; isto kao session.lidar)
//   izvoriLabel(st) -> natpis dugmeta u redu komandi Vožnja („Izvori: sve sim ▾“)
//   loadSources() / saveSources(src)   localStorage `eurosim.sources` (try/catch)

export const R_FAZA6 = 'dolazi sa Fazom 6 (ESP)';
export const R_PRAVI_POGON = 'pravi pogon traži pravi lidar i IR';
export const R_SIM_POGON = 'uz simulirani pogon pravi može da bude samo lidar (hibrid)';
export const R_PRAVI_MEH = 'pravi pogon traži prave mehanizme';
export const R_PRAVI_PROT = 'pravi pogon ne vidi simulirane protivnike';
export const R_NEMA_SNIMKA = 'nema snimljenog lidara (studio/lidar/); snima se pri vožnji sa pravim lidarom';
export const R_SESIJA = 'sesija radi: izvori se menjaju posle Završi / Prekini vezu';

export const OPT_LABEL = { sim: 'sim', pravi: 'pravi', snimak: 'snimak', lazan: 'lažiran' };

export const PARTS = [
  { id: 'pogon', name: 'pogon', opts: ['sim', 'pravi'], title: 'poza, odometrija; taktika se izvršava tamo gde je pogon' },
  { id: 'lidar', name: 'lidar', opts: ['sim', 'pravi', 'snimak'], title: 'krugovi lidara: simulirani sto, pravi lidar sa robota (WiFi) ili snimak' },
  { id: 'ir', name: 'IR', opts: ['sim', 'pravi'], title: 'IR senzori' },
  { id: 'mehanizmi', name: 'mehanizmi', opts: ['sim', 'pravi', 'lazan'], title: 'aktuatori; lažiran = robot odgovori „gotovo“ posle zadatog vremena' },
  { id: 'protivnici', name: 'protivnici', opts: ['sim', 'pravi'], title: 'protivnici: simulirani ili stvarni na stolu' },
];

export const PRESETS = [
  { id: 'a', label: 'a · sve sim', title: 'Sve simulirano na laptopu: pogon, lidar, IR, mehanizmi, protivnici' },
  { id: 'b', label: 'b · hibrid lidar', title: 'Pogon, IR, mehanizmi i protivnici simulirani; lidar pravi (sa robota preko WiFi-ja, host i lozinka u „Poveži robota“ na traci) ili iz snimka' },
  { id: 'c', label: 'c · robot + lažiran meh.', title: 'Pravi robot, mehanizmi lažirani (odgovore „gotovo“ posle zadatog vremena)' },
  { id: 'd', label: 'd · sve pravo', title: 'Pravi ili virtuelni robot: taktika radi na ESP-u (veza: „Poveži robota“ na traci)' },
];

const LIDARS = ['sim', 'pravi', 'snimak'];

export function normSources(src, files = []) {
  const s = src && typeof src === 'object' ? src : {};
  let lidar = LIDARS.includes(s.lidar) ? s.lidar : 'sim';
  let file = typeof s.file === 'string' && files.includes(s.file) ? s.file : (files[0] || null);
  if (lidar === 'snimak' && !file) lidar = 'sim';
  return { lidar, file };
}

export function lidarSpec(sources, files = []) {
  const s = normSources(sources, files);
  return s.lidar === 'pravi' ? 'robot' : s.lidar === 'snimak' ? 'file:' + s.file : 'sim';
}

// Deo -> izvor iz zahteva sesije (pre poruke hello) ili iz hello.source.parts.
function partsOfSession(st) {
  const hs = st.helloSource;
  if (hs && hs.parts && Object.keys(hs.parts).length) {
    const robot = hs.engine === 'robot';
    const out = {};
    for (const p of PARTS) out[p.id] = hs.parts[p.id] || (robot && p.id === 'pogon' ? 'pravi' : null);
    return { parts: out, engine: hs.engine };
  }
  const s = st.session || {};
  if (s.kind === 'robot') return { parts: Object.fromEntries(PARTS.map(p => [p.id, 'pravi'])), engine: 'robot' };
  const l = String(s.lidar || 'sim');
  const lidar = l === 'robot' ? 'pravi' : l.startsWith('file:') ? 'snimak' : 'sim';
  return { parts: { pogon: 'sim', lidar, ir: 'sim', mehanizmi: 'sim', protivnici: 'sim' }, engine: 'sim' };
}

function partsOfChoice(st, files) {
  if (st.drive === 'robot') return Object.fromEntries(PARTS.map(p => [p.id, 'pravi']));
  const s = normSources(st.sources, files);
  return { pogon: 'sim', lidar: s.lidar, ir: 'sim', mehanizmi: 'sim', protivnici: 'sim' };
}

export function presetOf(parts) {
  if (!parts || !parts.pogon) return null;
  if (parts.pogon === 'pravi') return parts.mehanizmi === 'lazan' ? 'c' : 'd';
  return parts.lidar && parts.lidar !== 'sim' ? 'b' : 'a';
}

// Zašto opcija v dela part ne može uz pogon `pogon` (null = može).
export function optionReason(part, v, pogon, files = []) {
  if (v === 'lazan') return R_FAZA6;
  if (part === 'pogon') return null;
  if (pogon === 'pravi') {
    if (v === 'pravi') return null;
    if (part === 'lidar' || part === 'ir') return R_PRAVI_POGON;
    return part === 'mehanizmi' ? R_PRAVI_MEH : R_PRAVI_PROT;
  }
  if (v === 'sim') return null;
  if (part === 'lidar') return v === 'snimak' && !files.length ? R_NEMA_SNIMKA : null;
  return R_SIM_POGON;
}

export function izvoriView(st = {}, files = st.lidarFiles || []) {
  const readOnly = !!st.session;
  const ses = readOnly ? partsOfSession(st) : null;
  const parts = readOnly ? ses.parts : partsOfChoice(st, files);
  const preset = presetOf(parts);
  const presets = PRESETS.map(p => {
    const reason = readOnly ? R_SESIJA : p.id === 'c' ? R_FAZA6 : null;
    return { ...p, on: p.id === preset, disabled: !!reason, reason };
  });
  const rows = PARTS.map(p => {
    const value = parts[p.id] || null;
    const options = p.opts.map(v => {
      const reason = readOnly ? R_SESIJA : optionReason(p.id, v, parts.pogon, files);
      return { v, label: OPT_LABEL[v], on: v === value, disabled: !!reason, reason };
    });
    const why = [];                                    // vidljiv razlog sivih opcija u redu (bez sesije)
    if (!readOnly) {
      const by = new Map();
      for (const o of options) if (o.disabled) by.set(o.reason, [...(by.get(o.reason) || []), o.label]);
      for (const [r, labels] of by) why.push(`${labels.join(', ')}: ${r}`);
    }
    return { id: p.id, name: p.name, title: p.title, value, options, why: why.join(' · ') };
  });
  const sel = normSources(st.sources, files);
  const sesFile = readOnly && String((st.session || {}).lidar || '').startsWith('file:') ? st.session.lidar.slice(5) : null;
  const lidarFile = readOnly
    ? { shown: parts.lidar === 'snimak', value: sesFile, files: sesFile ? [sesFile] : [], disabled: true }
    : { shown: parts.lidar === 'snimak', value: sel.file, files, disabled: false };
  // Veza sa robotom je na statusnoj traci („Poveži robota“, shell/veza.js); ovde samo uputa: d i pravi lidar u hibridu (b)
  // traže host i lozinku odatle.
  const usedBy = parts.pogon === 'pravi' ? 'robot' : parts.lidar === 'pravi' ? 'lidar' : null;
  const connect = { show: !readOnly && usedBy != null, usedBy };
  const note = readOnly ? (ses.engine === 'robot' ? 'Sesija sa robotom radi: izvori se samo čitaju (menjaju se posle Prekini vezu)'
    : 'Sesija uživo radi: izvori se samo čitaju (menjaju se posle Završi)') : '';
  return { readOnly, preset, presets, rows, lidarFile, connect, note };
}

export function applyPreset(id, st = {}, files = st.lidarFiles || []) {
  if (st.session) return null;
  const src = normSources(st.sources, files);
  if (id === 'a') return { drive: 'sim', sources: { ...src, lidar: 'sim' } };
  if (id === 'b') return { drive: 'sim', sources: { ...src, lidar: src.lidar === 'sim' ? 'pravi' : src.lidar } };
  if (id === 'd') return { drive: 'robot', sources: src };
  return null;                                         // c: Faza 6
}

export function applyOption(part, v, st = {}, files = st.lidarFiles || []) {
  if (st.session) return null;
  const src = normSources(st.sources, files);
  if (part === 'pogon') return v === 'pravi' ? { drive: 'robot', sources: src } : v === 'sim' ? { drive: 'sim', sources: src } : null;
  const pogon = st.drive === 'robot' ? 'pravi' : 'sim';
  if (optionReason(part, v, pogon, files)) return null;
  if (part === 'lidar' && pogon === 'sim') return { drive: 'sim', sources: { ...src, lidar: v } };
  return { drive: st.drive === 'robot' ? 'robot' : 'sim', sources: src };       // već izabrano (jedina dozvoljena)
}

export function izvoriLabel(st = {}, files = st.lidarFiles || []) {
  const p = partsOfChoice(st, files);
  const name = p.pogon === 'pravi' ? 'sve pravo' : p.lidar === 'pravi' ? 'hibrid, pravi lidar'
    : p.lidar === 'snimak' ? 'hibrid, lidar iz snimka' : 'sve sim';
  return `Izvori: ${name} ▾`;
}

const KEY = 'eurosim.sources';

export function loadSources() {                     // snimak se proverava kasnije (normSources sa spiskom snimaka)
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || 'null');
    return { lidar: LIDARS.includes(s && s.lidar) ? s.lidar : 'sim', file: s && typeof s.file === 'string' ? s.file : null };
  } catch (e) { return { lidar: 'sim', file: null }; }
}

export function saveSources(src) {
  try { localStorage.setItem(KEY, JSON.stringify(src)); } catch (e) { /* ignore */ }
}
