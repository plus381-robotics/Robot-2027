// UI test za F2 (Playwright, Node): editor taktika. Napravi i obriše ESP32/tactics/ui_test_tmp.py.
//   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_f2.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const TMP = path.join(__dirname, '..', '..', 'ESP32', 'tactics', 'ui_test_tmp.py');
(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1700, height: 980 } });
  const errs = [], fail = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('dialog', d => d.accept('ui_test_tmp'));
  try {
    await p.goto(url);
    await p.evaluate(() => localStorage.clear()); await p.reload();
    await p.waitForSelector('#tactic option', { state: 'attached' });
    await p.selectOption('#tactic', 'primer');
    await p.click('#edBtn');
    await p.waitForSelector('.cm-content');
    await p.waitForFunction(() => /from tac import/.test(document.querySelector('.cm-content').textContent));
    // dopuna koda
    await p.click('.cm-content'); await p.keyboard.press('Control+End');
    await p.keyboard.type('\ngoto(600)\nwai');
    await p.keyboard.press('Control+Space');
    await p.waitForSelector('.cm-tooltip-autocomplete li');
    const compl = await p.$$eval('.cm-tooltip-autocomplete li', l => l.map(x => x.textContent));
    if (!compl.some(c => c.startsWith('wait_until'))) fail.push('dopuna: ' + compl);
    await p.keyboard.press('Escape');
    // greške dok se kuca
    await p.waitForFunction(() => /fali `y`/.test(document.getElementById('edProblems').textContent), null, { timeout: 5000 })
      .catch(() => fail.push('nema greške za goto(600)'));
    // nova taktika, pokretanje, isticanje linije, čuvanje
    await p.click('#edNew');
    await p.waitForFunction(() => /START = /.test(document.querySelector('.cm-content').textContent));
    await p.click('#edRun');
    await p.waitForFunction(() => /^OK/.test(document.getElementById('result').textContent), null, { timeout: 20000 })
      .catch(() => fail.push('nova taktika nije prošla simulaciju'));
    await p.evaluate(() => { window.eurosim.play.t = 2000; });
    await p.click('#nextFrame');
    const cur = await p.$$eval('.cm-step-cur', l => l.map(x => x.textContent));
    if (!cur.length) fail.push('linija koraka nije istaknuta');
    if (fs.existsSync(TMP)) fail.push('fajl napravljen pre Save');
    await p.click('#edSave');
    await p.waitForFunction(() => /^saved/.test(document.getElementById('edState').textContent));
    if (!fs.existsSync(TMP)) fail.push('Save nije napravio fajl');
    if (process.argv[3]) await p.screenshot({ path: process.argv[3] });
    console.log(JSON.stringify({ ok: !fail.length && !errs.length, fail, errs, compl: compl.slice(0, 3), cur }));
  } finally {
    await b.close();
    if (fs.existsSync(TMP)) fs.unlinkSync(TMP);
  }
  process.exit(fail.length || errs.length ? 1 : 0);
})();
