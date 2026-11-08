// UI test za F3 (Playwright, Node): Live (ESP tasteri, naoružaj, činč, protivnik, kraj) i prevlačenje
// protivnika u brzom režimu.  python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_f3.js
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
  const errs = [], fail = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(url);
  await p.evaluate(() => localStorage.clear());
  await p.reload();
  await p.waitForSelector('#tactic option', { state: 'attached' });
  await p.selectOption('#tactic', 'primer');
  // --- live ---
  await p.click('#tabLive'); await p.click('#liveBtn');
  await p.waitForTimeout(1200);
  const lit = await p.evaluate(() => {                        // OLED nije prazan
    const c = document.querySelector('#espPanel canvas'), d = c.getContext('2d').getImageData(0, 0, 128, 64).data;
    let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] > 100) n++; return n;
  });
  if (lit < 50) fail.push('OLED prazan');
  await p.click('#addOpp');
  await p.fill('#oppX', '1000'); await p.dispatchEvent('#oppX', 'change');
  await p.click('#armBtn'); await p.waitForTimeout(600);
  await p.click('#cordBtn'); await p.waitForTimeout(2500);
  await p.click('#endBtn');
  await p.waitForFunction(() => document.getElementById('result').style.display === 'block', null, { timeout: 15000 });
  const steps = await p.$$eval('#steps tbody tr', r => r.map(x => x.textContent));
  if (!steps.length || !/blocked/.test(steps[0])) fail.push('live: prvi korak nije blocked: ' + steps);
  // --- brzi režim: prevuci protivnika na put robota ---
  await p.evaluate(() => localStorage.clear());
  await p.reload();
  await p.waitForSelector('#tactic option', { state: 'attached' });
  await p.selectOption('#tactic', 'primer');
  await p.click('#cam2d');
  await p.click('#addOpp');
  await p.click('#tabSim'); await p.click('#run');
  await p.waitForFunction(() => /^OK/.test(document.getElementById('result').textContent));
  // položaj protivnika na ekranu (projekcija iz 3D prikaza; sto nije baš u sredini kadra)
  const [cx, cy] = await p.evaluate(() => { const v = window.eurosim.view; const g = v.oppGroup.children[0];
    const pr = g.position.clone().project(v.camera); const r = v.renderer.domElement.getBoundingClientRect();
    return [r.left + (pr.x + 1) / 2 * r.width, r.top + (1 - pr.y) / 2 * r.height]; });
  await p.mouse.move(cx, cy); await p.mouse.down();
  for (let k = 1; k <= 10; k++) await p.mouse.move(cx - k * 30, cy);
  await p.mouse.up();
  await p.waitForFunction(() => /^NOT OK/.test(document.getElementById('result').textContent), null, { timeout: 15000 })
    .catch(() => fail.push('posle prevlačenja simulacija nije ponovljena'));
  if (process.argv[3]) await p.screenshot({ path: process.argv[3] });
  await b.close();
  if (errs.length) fail.push('JS: ' + errs.join(' | '));
  console.log(JSON.stringify({ ok: !fail.length, fail, lit, steps }));
  process.exit(fail.length ? 1 : 0);
})();
