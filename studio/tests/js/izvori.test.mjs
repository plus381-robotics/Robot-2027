// Testovi za web/core/izvori.js: blok Izvori (Zadatak 5.1) — unapred zadate kombinacije a, b, d (c sivo), izvor po
// delu robota sa razlozima za sivo, šta izbor menja (drive, sources), upit lidara za sesiju i samo čitanje u sesiji.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  izvoriView, applyPreset, applyOption, normSources, lidarSpec, izvoriLabel, presetOf, optionReason, loadSources, saveSources,
  R_FAZA6, R_PRAVI_POGON, R_SIM_POGON, R_NEMA_SNIMKA, R_SESIJA,
} from '../../web/core/izvori.js';

const FILES = ['20261101-101010.jsonl.gz', 'b.jsonl.gz'];
const opt = (v, part, val) => v.rows.find(r => r.id === part).options.find(o => o.v === val);
const pre = (v, id) => v.presets.find(p => p.id === id);

test('normSources i lidarSpec: sim / robot / file:<snimak>; snimak koga nema -> prvi ili sim', () => {
  assert.deepEqual(normSources(null, []), { lidar: 'sim', file: null });
  assert.deepEqual(normSources({ lidar: 'xyz' }, FILES), { lidar: 'sim', file: FILES[0] });
  assert.deepEqual(normSources({ lidar: 'snimak', file: 'b.jsonl.gz' }, FILES), { lidar: 'snimak', file: 'b.jsonl.gz' });
  assert.deepEqual(normSources({ lidar: 'snimak', file: 'nema.jsonl.gz' }, FILES), { lidar: 'snimak', file: FILES[0] });
  assert.deepEqual(normSources({ lidar: 'snimak', file: 'b.jsonl.gz' }, []), { lidar: 'sim', file: null });
  assert.equal(lidarSpec({ lidar: 'sim' }, FILES), 'sim');
  assert.equal(lidarSpec({ lidar: 'pravi' }, FILES), 'robot');
  assert.equal(lidarSpec({ lidar: 'snimak', file: 'b.jsonl.gz' }, FILES), 'file:b.jsonl.gz');
  assert.equal(lidarSpec({ lidar: 'snimak', file: 'b.jsonl.gz' }, []), 'sim');
});

test('a: sve sim; c sivo (Faza 6); lažiran sivo; pravi IR/mehanizmi/protivnici uz sim pogon sivo sa razlogom', () => {
  const v = izvoriView({ drive: 'sim', sources: { lidar: 'sim' }, session: null }, FILES);
  assert.equal(v.readOnly, false);
  assert.equal(v.preset, 'a');
  assert.deepEqual(v.presets.map(p => [p.id, p.on, p.disabled]), [['a', true, false], ['b', false, false], ['c', false, true], ['d', false, false]]);
  assert.equal(pre(v, 'c').reason, R_FAZA6);
  assert.deepEqual(v.rows.map(r => [r.id, r.value]), [['pogon', 'sim'], ['lidar', 'sim'], ['ir', 'sim'], ['mehanizmi', 'sim'], ['protivnici', 'sim']]);
  assert.equal(opt(v, 'pogon', 'pravi').disabled, false);
  for (const l of ['sim', 'pravi', 'snimak']) assert.equal(opt(v, 'lidar', l).disabled, false, l);
  assert.equal(opt(v, 'ir', 'pravi').reason, R_SIM_POGON);
  assert.equal(opt(v, 'mehanizmi', 'lazan').reason, R_FAZA6);
  assert.equal(opt(v, 'mehanizmi', 'lazan').label, 'lažiran');
  assert.equal(v.rows.find(r => r.id === 'mehanizmi').why, `pravi: ${R_SIM_POGON} · lažiran: ${R_FAZA6}`);
  assert.equal(v.rows.find(r => r.id === 'pogon').why, '');
  assert.equal(v.lidarFile.shown, false);
});

test('b: hibrid sa pravim lidarom ili snimkom; snimak bez snimaka sivo', () => {
  const v = izvoriView({ drive: 'sim', sources: { lidar: 'snimak', file: 'b.jsonl.gz' } }, FILES);
  assert.equal(v.preset, 'b');
  assert.equal(opt(v, 'lidar', 'snimak').on, true);
  assert.deepEqual(v.lidarFile, { shown: true, value: 'b.jsonl.gz', files: FILES, disabled: false });
  assert.deepEqual(izvoriView({ drive: 'sim', sources: { lidar: 'pravi' } }, FILES).connect, { show: true, usedBy: 'lidar' });
  assert.deepEqual(izvoriView({ drive: 'sim', sources: { lidar: 'sim' } }, FILES).connect, { show: false, usedBy: null });
  const none = izvoriView({ drive: 'sim', sources: { lidar: 'sim' } }, []);
  assert.equal(opt(none, 'lidar', 'snimak').reason, R_NEMA_SNIMKA);
  assert.equal(opt(none, 'lidar', 'pravi').disabled, false);
  assert.equal(izvoriView({ drive: 'sim', sources: { lidar: 'snimak', file: 'x' } }, []).preset, 'a');   // nema snimka -> sim
});

test('d: pravi pogon traži pravi lidar i IR (sim/snimak sivo); lažiran Faza 6', () => {
  const v = izvoriView({ drive: 'robot', sources: { lidar: 'snimak', file: 'b.jsonl.gz' } }, FILES);
  assert.equal(v.preset, 'd');
  assert.ok(v.rows.every(r => r.value === 'pravi'));
  for (const l of ['sim', 'snimak']) assert.equal(opt(v, 'lidar', l).reason, R_PRAVI_POGON, l);
  assert.equal(opt(v, 'ir', 'sim').reason, R_PRAVI_POGON);
  assert.equal(opt(v, 'mehanizmi', 'lazan').reason, R_FAZA6);
  assert.ok(opt(v, 'protivnici', 'sim').disabled && opt(v, 'mehanizmi', 'sim').disabled);
  assert.equal(opt(v, 'pogon', 'sim').disabled, false);
  assert.equal(v.lidarFile.shown, false);
  assert.equal(v.connect.usedBy, 'robot');
  assert.deepEqual(v.connect, { show: true, usedBy: 'robot' });                // polja veze su na traci („Poveži robota“)
  assert.ok(!('inputs' in v.connect) && !('buttons' in v.connect));
  assert.equal(optionReason('lidar', 'pravi', 'pravi'), null);
});

test('applyPreset / applyOption: a, b, d menjaju drive i sources; c i sivo ne rade ništa', () => {
  const st = { drive: 'sim', sources: { lidar: 'sim', file: null }, session: null };
  assert.deepEqual(applyPreset('a', { ...st, sources: { lidar: 'pravi' } }, FILES), { drive: 'sim', sources: { lidar: 'sim', file: FILES[0] } });
  assert.deepEqual(applyPreset('b', st, FILES), { drive: 'sim', sources: { lidar: 'pravi', file: FILES[0] } });
  assert.deepEqual(applyPreset('b', { ...st, sources: { lidar: 'snimak', file: 'b.jsonl.gz' } }, FILES).sources, { lidar: 'snimak', file: 'b.jsonl.gz' });
  assert.equal(applyPreset('d', st, FILES).drive, 'robot');
  assert.equal(applyPreset('c', st, FILES), null);
  assert.deepEqual(applyOption('lidar', 'snimak', st, FILES), { drive: 'sim', sources: { lidar: 'snimak', file: FILES[0] } });
  assert.equal(applyOption('lidar', 'snimak', st, []), null);                 // nema snimaka
  assert.equal(applyOption('pogon', 'pravi', st, FILES).drive, 'robot');
  assert.equal(applyOption('pogon', 'sim', { ...st, drive: 'robot' }, FILES).drive, 'sim');
  assert.equal(applyOption('ir', 'pravi', st, FILES), null);
  assert.equal(applyOption('lidar', 'sim', { ...st, drive: 'robot' }, FILES), null);
  assert.equal(applyOption('mehanizmi', 'lazan', { ...st, drive: 'robot' }, FILES), null);
  assert.equal(applyOption('lidar', 'pravi', { ...st, drive: 'robot' }, FILES).drive, 'robot');   // već izabrano
  assert.equal(applyOption('ir', 'sim', st, FILES).drive, 'sim');
  const ses = { ...st, session: { kind: 'sim', lidar: 'sim' } };                // sesija radi: ništa
  assert.equal(applyPreset('b', ses, FILES), null);
  assert.equal(applyOption('lidar', 'pravi', ses, FILES), null);
  assert.equal(applyOption('pogon', 'pravi', ses, FILES), null);
});

test('sesija radi: samo čitanje, iz hello.source (pre hello iz zahteva sesije)', () => {
  const hib = { drive: 'sim', sources: { lidar: 'sim' }, session: { kind: 'sim', lidar: 'file:b.jsonl.gz' },
    helloSource: { engine: 'sim', parts: { pogon: 'sim', lidar: 'snimak', ir: 'sim', mehanizmi: 'sim', protivnici: 'sim' } } };
  const v = izvoriView(hib, FILES);
  assert.equal(v.readOnly, true);
  assert.equal(v.preset, 'b');                                                  // sesija, ne izbor (a)
  assert.ok(v.presets.every(p => p.disabled && p.reason === R_SESIJA));
  assert.ok(v.rows.every(r => r.options.every(o => o.disabled) && r.why === ''));
  assert.equal(opt(v, 'lidar', 'snimak').on, true);
  assert.deepEqual(v.lidarFile, { shown: true, value: 'b.jsonl.gz', files: ['b.jsonl.gz'], disabled: true });
  assert.equal(v.connect.show, false);                                          // sesija radi: ništa za povezivanje
  assert.match(v.note, /Završi/);
  const before = izvoriView({ drive: 'sim', session: { kind: 'sim', lidar: 'robot' }, helloSource: null }, FILES);
  assert.equal(before.preset, 'b');
  assert.equal(opt(before, 'lidar', 'pravi').on, true);
  const rob = izvoriView({ drive: 'robot', session: { kind: 'robot' }, helloSource: { engine: 'robot', parts: { pogon: 'pravi', lidar: 'pravi' } } }, FILES);
  assert.equal(rob.preset, 'd');
  assert.equal(rob.rows.find(r => r.id === 'ir').value, null);                  // izvor ne javlja: ništa nije izabrano
  assert.match(rob.note, /Prekini vezu/);
  assert.equal(presetOf({ pogon: 'pravi', mehanizmi: 'lazan' }), 'c');
});

test('izvoriLabel: natpis dugmeta u redu komandi', () => {
  assert.equal(izvoriLabel({ drive: 'sim', sources: { lidar: 'sim' } }, FILES), 'Izvori: sve sim ▾');
  assert.equal(izvoriLabel({ drive: 'sim', sources: { lidar: 'pravi' } }, FILES), 'Izvori: hibrid, pravi lidar ▾');
  assert.equal(izvoriLabel({ drive: 'sim', sources: { lidar: 'snimak' }, lidarFiles: FILES }), 'Izvori: hibrid, lidar iz snimka ▾');
  assert.equal(izvoriLabel({ drive: 'robot', sources: { lidar: 'pravi' } }, FILES), 'Izvori: sve pravo ▾');
});

test('loadSources / saveSources: localStorage eurosim.sources; bez localStorage-a podrazumevano', () => {
  assert.deepEqual(loadSources(), { lidar: 'sim', file: null });               // node: nema localStorage
  saveSources({ lidar: 'pravi' });                                              // ne baca
  const mem = {};
  globalThis.localStorage = { getItem: k => mem[k] ?? null, setItem: (k, v) => { mem[k] = String(v); } };
  try {
    saveSources({ lidar: 'snimak', file: 'b.jsonl.gz' });
    assert.equal(mem['eurosim.sources'], '{"lidar":"snimak","file":"b.jsonl.gz"}');
    assert.deepEqual(loadSources(), { lidar: 'snimak', file: 'b.jsonl.gz' });
    mem['eurosim.sources'] = '{nije json';
    assert.deepEqual(loadSources(), { lidar: 'sim', file: null });
  } finally { delete globalThis.localStorage; }
});
