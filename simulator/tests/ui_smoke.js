// UI smoke test (Playwright, Node): otvori interfejs, pokreni simulaciju, proveri panele, nema JS grešaka.
//   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_smoke.js [url] [slika.png]
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1500, height: 900 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(url);
  await p.waitForSelector('#tactic option', { state: 'attached' });
  await p.selectOption('#tactic', 'primer');
  await p.selectOption('#side', 'zuta');
  await p.click('#run');
  await p.waitForFunction(() => document.getElementById('result').style.display === 'block', null, { timeout: 30000 });
  await p.keyboard.press('End');
  await p.waitForTimeout(300);
  const steps = await p.$$eval('#steps tbody tr', r => r.length);
  const result = await p.textContent('#result');
  if (process.argv[3]) await p.screenshot({ path: process.argv[3] });
  await b.close();
  const ok = errs.length === 0 && steps === 3 && result.startsWith('OK');
  console.log(JSON.stringify({ ok, steps, result: result.slice(0, 60), errs }));
  process.exit(ok ? 0 : 1);
})();
