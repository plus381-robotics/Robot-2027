// UI test za fazu A plana (docs/plan-simulator-unapredjenja.md): S1 strana u Live-u, S2 Save as/Rename/Delete,
// S3 Tab u dopuni. Pravi i briše ESP32/tactics/ui_tmp_a.py i ui_tmp_b.py.
//   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_faza_a.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const DIR = path.join(__dirname, '..', '..', 'ESP32', 'tactics');
const TMP = ['ui_tmp_a', 'ui_tmp_b'].map(n => path.join(DIR, n + '.py'));
(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
  const errs = [], fail = [], answers = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('dialog', d => (d.type() === 'prompt' ? d.accept(answers.shift()) : d.accept()));
  const ev = f => p.evaluate(f);
  try {
    await p.goto(url);
    await ev(() => localStorage.clear()); await p.reload();
    await p.waitForSelector('#tactic option', { state: 'attached' });
    await p.selectOption('#tactic', 'primer');

    // S1: Live sa žutom, pa plava, Arm, činč: robot vozi po plavoj, odometrija se slaže
    await p.selectOption('#side', 'zuta');
    await p.click('#tabLive'); await p.click('#liveBtn'); await p.waitForTimeout(1500);
    await p.selectOption('#side', 'plava'); await p.waitForTimeout(800);
    await p.click('#armBtn'); await p.waitForTimeout(1200);
    if (!(await p.isVisible('#bandCord'))) fail.push('S9: nema dugmeta za činč na timeline-u dok je naoružan');
    await p.click('#bandCord'); await p.waitForTimeout(6000);                // činč sa timeline-a (S9)
    if (await p.isVisible('#bandCord')) fail.push('S9: dugme za činč ostalo posle činča');
    const s1 = await ev(() => { const r = window.eurosim.run, c = r.cols, i = c.t.length - 1;
      return { x: c.x[i], ox: c.ox[i], y: c.y[i], oy: c.oy[i], side: r.meta.side }; });
    if (!(s1.x > 1500 && Math.abs(s1.x - s1.ox) < 20 && Math.abs(s1.y - s1.oy) < 20 && s1.side === 'plava'))
      fail.push('S1 plava: ' + JSON.stringify(s1));
    await p.click('#endBtn'); await p.waitForTimeout(1000);

    // S2: Save as, Rename, Delete
    await p.click('#edBtn');
    await p.waitForSelector('.cm-content');
    await p.waitForFunction(() => /from tac import/.test(document.querySelector('.cm-content').textContent));
    answers.push('ui_tmp_a'); await p.selectOption('#edFileMenu', 'saveas'); await p.waitForTimeout(700);
    if (!fs.existsSync(TMP[0]) || (await ev(() => window.eurosim.ed.name)) !== 'ui_tmp_a') fail.push('S2 Save as');
    answers.push('ui_tmp_b'); await p.selectOption('#edFileMenu', 'rename'); await p.waitForTimeout(700);
    if (fs.existsSync(TMP[0]) || !fs.existsSync(TMP[1])) fail.push('S2 Rename');
    await p.selectOption('#edFileMenu', 'delete');
    await p.waitForFunction(() => window.eurosim.ed.name === 'primer', null, { timeout: 8000 }).catch(() => {});
    if (fs.existsSync(TMP[1]) || (await ev(() => window.eurosim.ed.name)) !== 'primer') fail.push('S2 Delete');

    // S3: "g" -> lista sa goto prvim, Tab ubaci goto(x_mm, y_mm), Tab prelazi na y; Ctrl+Space ima grupe
    await p.click('.cm-content'); await p.keyboard.press('Control+End'); await p.keyboard.press('Enter');
    await p.keyboard.type('g');
    await p.waitForSelector('.cm-tooltip-autocomplete li');
    const first = await p.$eval('.cm-tooltip-autocomplete li', x => x.textContent);
    if (!first.startsWith('goto')) fail.push('S3 prvi predlog: ' + first);
    await p.keyboard.press('Tab'); await p.keyboard.type('600'); await p.keyboard.press('Tab'); await p.keyboard.type('1000');
    const line = await ev(() => window.eurosim.ed.editor.text().split('\n').pop().trim());
    if (line !== 'goto(600, 1000)') fail.push('S3 Tab: ' + line);
    await p.keyboard.press('End'); await p.keyboard.press('Enter');
    await p.keyboard.press('Control+Space');
    await p.waitForSelector('completion-section');
    const secs = await p.$$eval('completion-section', l => l.map(x => x.textContent));
    if (secs[0] !== 'Motion') fail.push('S3 grupe: ' + secs);
    if (process.argv[3]) await p.screenshot({ path: process.argv[3] });
    console.log(JSON.stringify({ ok: !fail.length && !errs.length, fail, errs, s1, line, secs }));
  } finally {
    await b.close();
    for (const f of TMP) if (fs.existsSync(f)) fs.unlinkSync(f);
  }
  process.exit(fail.length || errs.length ? 1 : 0);
})();
