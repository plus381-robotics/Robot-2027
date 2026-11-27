// UI test prostora Snimci (Zadatak 4.5; Playwright, Node): lista sačuvanih snimaka (izvor, taktika, ishod, filter),
// učitavanje klikom (i snimak v1), 📌 Referenca + ponovna simulacija = poređenje, Uporedi sa…, ✕, „Otvori u Snimcima“
// posle kraja sesije uživo. Snimke koje napravi briše na kraju.
//   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_snimci.js [url]
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { chromium } = require('playwright');

(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1366, height: 768 } });
  const errs = [], fails = [], made = [];
  const check = (ok, what) => { if (!ok) fails.push(what); };
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error' && !/ERR_BLOCKED_BY_CLIENT/.test(m.text())) errs.push(m.text()); });
  let runsDir = null;
  try {
  await p.goto(url);
  await p.waitForSelector('#tactic option', { state: 'attached' });
  const info = await p.evaluate(() => fetch('/api/info').then(r => r.json()));
  runsDir = info.where.runs;

  // snimak v1 (bez meta.origin, robot u result) direktno u folder snimaka
  const v1name = 'ui_snimci_v1_' + Date.now();
  fs.mkdirSync(runsDir, { recursive: true });
  const v1 = { version: 1, meta: { tactic: 'primer', side: 'plava', mode: 'test' }, result: { robot: true, sim_ms: 40 },
    frames: [0, 20, 40].map(t => ({ t, x: 0.3, y: 1.0, th: 0, ox: 0.3, oy: 1.0, oth: 0 })), events: [] };
  made.push(v1name);
  fs.writeFileSync(path.join(runsDir, v1name + '.json.gz'), zlib.gzipSync(JSON.stringify(v1)));

  // brza simulacija u Taktikama, pa Snimci: Sačuvaj snimak…
  await p.click('#rail [data-ws=taktike]');
  await p.selectOption('#tactic', 'primer');
  await p.click('#sideSeg [data-v=zuta]');
  await p.click('#run');
  await p.waitForFunction(() => document.getElementById('result').style.display === 'block', null, { timeout: 30000 });
  await p.click('#rail [data-ws=snimci]');
  check(await p.isVisible('#ws-snimci-alati #save') && await p.isVisible('#ws-snimci-alati #cmpPin') &&
    await p.isVisible('#ws-snimci-alati #cmpRun'), 'red komandi Snimci');
  check(!(await p.$('#moreBtn')) && !(await p.$('#cmpTools')) && !(await p.$('#runs')), 'stari meni i #cmpTools obrisani');
  const name = 'ui_snimci_' + Date.now();
  made.push(name);                                   // pre klika: briše se i ako test padne posle čuvanja
  p.once('dialog', d => d.accept(name));
  await p.click('#save');
  await p.waitForSelector(`#snList .sn-row.cur[data-name="${name}"]`);
  const row = await p.textContent(`#snList .sn-row[data-name="${name}"]`);
  check(/^S/.test(row) && row.includes('primer') && row.includes('OK'), 'red: izvor S, taktika, ishod OK: ' + row);
  const v1row = await p.textContent(`#snList .sn-row[data-name="${v1name}"]`);
  check(/^R/.test(v1row), 'v1 sa robota: izvor R: ' + v1row);

  // filter po izvoru i tekstu
  await p.click('#snSrc [data-v=R]');
  check(!(await p.$(`#snList .sn-row[data-name="${name}"]`)) && !!(await p.$(`#snList .sn-row[data-name="${v1name}"]`)), 'filter R');
  await p.click('#snSrc [data-v=""]');
  await p.fill('#snFind', name);
  check((await p.$$('#snList .sn-row')).length === 1, 'filter tekst');
  await p.fill('#snFind', '');

  // učitaj v1 klikom (istaknut), pa sačuvan; 📌 Referenca; ponovna simulacija (Plava) -> poređenje se vidi
  await p.click(`#snList .sn-row[data-name="${v1name}"]`);
  await p.waitForSelector(`#snList .sn-row.cur[data-name="${v1name}"]`);
  check(await p.evaluate(() => window.eurosim.run.meta.origin.engine) === 'robot', 'v1 se učitava (upgrade)');
  await p.click(`#snList .sn-row[data-name="${name}"]`);
  await p.waitForSelector(`#snList .sn-row.cur[data-name="${name}"]`);
  await p.click('#cmpPin');
  check((await p.textContent('#cmpName')).includes(name) && await p.isVisible('#cmpClear'), 'referenca: ime + ✕');
  check((await p.textContent(`#snList .sn-row[data-name="${name}"]`)).includes('📌'), 'referenca 📌 u listi');
  await p.click('#rail [data-ws=taktike]');
  await p.click('#sideSeg [data-v=plava]');
  await p.click('#run');
  await p.waitForFunction(() => window.eurosim.run.meta.side === 'plava', null, { timeout: 30000 });
  await p.click('#rail [data-ws=snimci]');
  check(await p.evaluate(() => !!window.eurosim.view.cmp), 'poređenje se crta');
  check(!(await p.$('#snList .sn-row.cur')), 'nesačuvana simulacija nije istaknuta');
  await p.selectOption('#cmpRun', v1name);
  await p.waitForFunction(n => document.getElementById('cmpName').textContent.includes(n), v1name);
  // Sačuvaj snimak posle „Uporedi sa…“ čuva simulaciju koja se gleda (Plava), ne referencu (v1)
  const name2 = 'ui_snimci_b_' + Date.now();
  made.push(name2);
  p.once('dialog', d => d.accept(name2));
  await p.click('#save');
  await p.waitForSelector(`#snList .sn-row.cur[data-name="${name2}"]`);
  const sv = await p.evaluate(n => fetch('/api/runs/' + n + '?ref=1').then(r => r.json()), name2);
  check(sv.meta.side === 'plava' && sv.meta.origin.engine === 'sim', 'sačuvana je simulacija, ne referenca');
  // oznaka reference na stolu van Snimaka (ime + ✕); u Snimcima je u redu komandi
  check(!(await p.isVisible('#refTag')), 'u Snimcima nema oznake na stolu');
  await p.click('#rail [data-ws=taktike]');
  check(await p.isVisible('#refTag') && (await p.textContent('#refTagName')).includes(v1name), 'oznaka reference u Taktikama');
  await p.click('#refTagClear');
  check(!(await p.isVisible('#refTag')) && await p.evaluate(() => !window.eurosim.view.cmp), '✕ na stolu uklanja referencu');
  await p.click('#rail [data-ws=snimci]');
  await p.selectOption('#cmpRun', v1name);
  await p.waitForFunction(n => document.getElementById('cmpName').textContent.includes(n), v1name);
  await p.click('#cmpClear');
  check(await p.evaluate(() => !window.eurosim.view.cmp) && (await p.textContent('#cmpName')) === '', '✕ uklanja referencu');

  // sesija uživo: Završi -> poruka sa „Otvori u Snimcima“ -> prostor Snimci
  await p.click('#rail [data-ws=voznja]');
  await p.click('#rail [data-drive=sim]');
  await p.click('#sessStart');
  await p.waitForFunction(() => !!window.eurosim.store.get().caps, null, { timeout: 15000 });
  await p.click('#endBtn');
  await p.waitForSelector('#msgAct:not([hidden])', { timeout: 15000 });
  check((await p.textContent('#msgAct')) === 'Otvori u Snimcima', 'dugme uz poruku');
  await p.click('#msgAct');
  check(await p.evaluate(() => window.eurosim.store.get().ws) === 'snimci', 'Otvori u Snimcima vodi u Snimci');

  } catch (e) {
    fails.push('izuzetak: ' + e.message);
  } finally {                                       // simulator/runs/ ide u git: test ne sme da ostavi snimke
    if (runsDir) for (const n of made) { try { fs.unlinkSync(path.join(runsDir, n + '.json.gz')); } catch (e) { /* ignore */ } }
    await b.close();
  }
  const ok = errs.length === 0 && fails.length === 0;
  console.log(JSON.stringify({ ok, fails, errs }));
  process.exit(ok ? 0 : 1);
})();
