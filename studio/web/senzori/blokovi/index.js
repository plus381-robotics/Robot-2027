// Senzori: spisak blokova (raspored B) i procena za prikaz. Bez DOM-a, da ga uveze i `node --test`.
//   BLOCKS                    blokovi redom; mesto u rasporedu (slot): 'top' lidar odozgo · 'sketch' skica robota ·
//                             'right' desna kolona (brzine, PID, napajanje) · 'bottom' donji red
//   SLOTS                     dozvoljena mesta
//   makeHas(st)               has(polje) za blockSource: '@lidar' = krug sesije (st.lidarScan) ili krugovi u snimku
//                             st.sens.run; '@mec' = stanje meča iz telemetrije ESP-a (st.robotMec, i bez Nucleo frame-ova)
//                             ili kolona `mec` snimka; ostalo hasData(st.sens.run, polje); bez snimka false
//   evalBlocks(st, blocks?, env?)  [{b, s: {src, reason, note}, d, v: {status, text, vals, foot?, error?}}] za svaki
//                             blok (view koji baci izuzetak daje status 'none' sa tekstom greške, ostali blokovi rade).
//                             env = {ctx, redraw} od panela (panels/senzori.js); bez njega (testovi) d.ctx = d.redraw = null
//   counts(list)              {ok, warn, none}: brojač u zaglavlju („● n radi · ● n upozorenja · ○ n bez podataka“)
//   warnWord(n)               'upozorenje' | 'upozorenja'
//
// Modul bloka (podrazumevani export, web/senzori/blokovi/<id>.js):
//   {id, name, slot, part, fields, simFields?, notes?, hints: string[],
//    view(d) -> {status: 'ok'|'warn'|'none', text: string, vals: [[ime, vrednost], ...], foot?: string},
//    draw?(g, w, h, d, big), html?(d, big) -> string, actions?(d) -> [{label, run(), disabled?, title?}]}
//   part / fields / simFields / notes: za oznaku izvora (senzori/izvor.js blockSource); hints: „Kako proveriti“.
//   d = {st, run, t, src, reason, note, profile, ctx, redraw}: st = store, run i t (ms) iz st.sens (app.js bridgeSens),
//       src = 'pravo'|'sim'|'snimak'|null i reason / note iz blockSource, profile = store.profile (/api/info),
//       ctx = ctx panela (ctx.command(c) šalje komandu sesije; za actions.run) ili null, redraw() = zakaži novo crtanje
//       (npr. kad stigne odgovor servera) ili null.
//   Bez izvora (src null) view vraća status 'none'. foot = kratak tekst u dnu pločice posle vals (npr. „grupe računa
//   laptop“). draw crta na platno w × h (CSS px; big = u detalju), html je prikaz bez platna; bez oba se u pločici
//   krupno pišu vals. Blok sa draw i html: pločica je samo platno, detalj platno i pored njega html (npr. skica + lista).

import { hasData } from '../../core/run.js';
import { blockSource } from '../izvor.js';
import lidar from './lidar.js';
import robot from './robot.js';
import brzine from './brzine.js';
import pid from './pid.js';
import napajanje from './napajanje.js';
import aktuatori from './aktuatori.js';
import enkoderi from './enkoderi.js';
import ulazi from './ulazi.js';
import mec from './mec.js';
import veza from './veza.js';

export const SLOTS = ['top', 'sketch', 'right', 'bottom'];
export const BLOCKS = [lidar, robot, brzine, pid, napajanje, aktuatori, enkoderi, ulazi, mec, veza];

export function makeHas(st) {
  const run = (st && st.sens && st.sens.run) || null;
  return k => {
    if (k === '@lidar') return !!(st && st.lidarScan) || !!(run && run.lidars && run.lidars.length);
    if (k === '@mec') return !!(st && st.session && st.session.kind === 'robot' && st.robotMec != null) || (!!run && !!run.cols && hasData(run, 'mec'));
    return !!run && !!run.cols && hasData(run, k);
  };
}

export function evalBlocks(st, blocks = BLOCKS, env = null) {
  st = st || {};
  const sens = st.sens || null, run = (sens && sens.run) || null, t = sens && sens.t != null ? sens.t : 0;
  const has = makeHas(st), profile = st.profile || null;
  const ctx = (env && env.ctx) || null, redraw = (env && env.redraw) || null;
  return blocks.map(b => {
    const s = blockSource(b, st, has);
    const d = { st, run, t, src: s.src, reason: s.reason, note: s.note, profile, ctx, redraw };
    let v;
    try { v = b.view(d); } catch (e) { v = { status: 'none', text: 'greška u bloku: ' + e.message, vals: [], error: e }; }
    return { b, s, d, v };
  });
}

export function counts(list) {
  const c = { ok: 0, warn: 0, none: 0 };
  for (const x of list) c[x.v.status === 'ok' || x.v.status === 'warn' ? x.v.status : 'none']++;
  return c;
}

export const warnWord = n => (n % 10 === 1 && n % 100 !== 11 ? 'upozorenje' : 'upozorenja');
