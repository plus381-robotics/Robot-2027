// UI test za fazu B plana (docs/plan-simulator-unapredjenja.md): S7 nacrt putanje dok se piše, S8 x/y pomoć
// (krst za red sa kursorom, Alt+klik = tačka sa mape). Ne čuva ništa na disk.
//   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_faza_b.js
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
  const errs = [], fail = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  const ev = (f, a) => p.evaluate(f, a);
  try {
    await p.goto(url);
    await ev(() => localStorage.clear()); await p.reload();
    await p.waitForSelector('#tactic option', { state: 'attached' });
    await p.selectOption('#tactic', 'primer');
    await p.click('#edBtn');
    await p.waitForSelector('.cm-content');
    await p.waitForFunction(() => /from tac import/.test(document.querySelector('.cm-content').textContent));
    await p.uncheck('#autoSim');
    await p.waitForFunction(() => window.eurosim.view.prevItems && window.eurosim.view.prevItems.length === 2);
    // kucanje: nova tačka se pojavi u nacrtu bez Run
    await p.click('.cm-content'); await p.keyboard.press('Control+End'); await p.keyboard.press('Enter');
    await p.keyboard.type('goto(1000, 1400, deg=90)');
    await p.waitForFunction(() => window.eurosim.view.prevItems.length === 3, null, { timeout: 5000 })
      .catch(() => fail.push('nacrt nema novu tačku'));
    const last = await ev(() => { const g = window.eurosim.view.prevItems[2]; return [g.position.x, g.position.y, g.scale.x]; });
    if (Math.abs(last[0] - 1) > 1e-6 || Math.abs(last[1] - 1.4) > 1e-6) fail.push('tačka nacrta: ' + last);
    if (last[2] !== 1.5) fail.push('tačka reda sa kursorom nije istaknuta');
    const cross = await ev(() => window.eurosim.view.cursorGroup.children.length);
    if (!cross) fail.push('nema krsta za x, y');
    const draft = await p.textContent('#edDraft');
    if (!/3 moves/.test(draft)) fail.push('natpis nacrta: ' + draft);
    // Alt+klik na sto: goto(x, y) u novi red
    await p.keyboard.press('End'); await p.keyboard.press('Enter');
    const box = await p.$eval('#view canvas', c => { const r = c.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
    await p.keyboard.down('Alt'); await p.mouse.click(box.x + box.w * 0.5, box.y + box.h * 0.5); await p.keyboard.up('Alt');
    await p.waitForTimeout(300);
    const lastLine = await ev(() => window.eurosim.ed.editor.text().trim().split('\n').pop());
    if (!/^goto\(\d+, \d+\)$/.test(lastLine)) fail.push('Alt+klik: ' + lastLine);
    // S4: panel Commands (Gambit Micro): pretraga, objašnjenje, Insert ubacuje primer
    await p.click('#edCmdBtn');
    await p.waitForSelector('#apiDrawer:not([hidden])');
    const title = await p.textContent('#apiDrawer .drawer-head b');
    if (title !== 'Gambit Micro') fail.push('naslov panela: ' + title);
    await p.fill('#apiFilter', 'goto');
    const found = await p.$$eval('#apiList details.cmd summary code', l => l.map(x => x.textContent));
    if (!found.includes('goto')) fail.push('pretraga: ' + found);
    await p.click('#apiList details.cmd[open] button.ins');
    const ins = await ev(() => window.eurosim.ed.editor.text().trim().split('\n').pop());
    if (ins !== 'goto(600, 1000)') fail.push('Insert: ' + ins);
    await p.click('#apiClose');
    // plava strana: nacrt ogledan
    await p.selectOption('#side', 'plava');
    await p.waitForFunction(() => window.eurosim.view.prevItems.length && window.eurosim.view.prevItems[0].position.x > 2, null, { timeout: 5000 })
      .catch(() => fail.push('nacrt za plavu nije ogledan'));
    if (process.argv[3]) await p.screenshot({ path: process.argv[3] });
    console.log(JSON.stringify({ ok: !fail.length && !errs.length, fail, errs, draft, lastLine }));
  } finally {
    await b.close();
  }
  process.exit(fail.length || errs.length ? 1 : 0);
})();
