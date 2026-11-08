// UI test za plan E (docs/plan-elementi-senzori-protivnik.md): E1 oznake koraka, E2 IR senzori, E3 kamenolomi,
// E4 protivnik sa taktikom i PAMI. Ne čuva ništa u repo (localStorage se briše).
//   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_faza_e.js
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1500, height: 950 } });
  const errs = [], fail = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  const ev = (f, a) => p.evaluate(f, a);
  const result = () => p.waitForFunction(() => /OK/.test(document.getElementById('result').textContent), null, { timeout: 30000 });
  try {
    await p.goto(url);
    await ev(() => localStorage.clear()); await p.reload();
    await p.waitForSelector('#tactic option', { state: 'attached' });
    await p.selectOption('#tactic', 'kamenolomi');
    await p.click('#cam2d');
    await p.click('#tabSim'); await p.click('#run'); await result();

    // E1: jedna oznaka po koraku koji pomera robota; natpis samo za tekući korak
    const e1 = await ev(() => { const v = window.eurosim.view, r = window.eurosim.run;
      return { marks: v.stepMarks.children.length, steps: r.steps.length,
        labels: v.stepMarks.children.filter(g => g.userData.lbl.visible).length }; });
    if (!(e1.marks > 10 && e1.marks < e1.steps && e1.labels <= 1)) fail.push('E1: ' + JSON.stringify(e1));
    if ((await ev(() => fetch('/favicon.svg').then(r => r.status))) !== 200) fail.push('E1: favicon');

    // E2: 8 senzora F1..B4 iz profila; kamenolomi ih ne zaustavljaju (taktika prošla), ir_off se vidi u snimku
    const e2 = await ev(() => ({ names: window.eurosim.view.irRays.map(r => r.name).join(' '),
      off: (window.eurosim.run.cols.irm || []).some(m => m === 15) }));
    if (e2.names !== 'F1 F2 F3 F4 B1 B2 B3 B4' || !e2.off) fail.push('E2: ' + JSON.stringify(e2));
    // U2: slika IR senzora u STATE pokazuje isključene (kamenolomi: ir_off("B") posle uzimanja)
    const tOff = await ev(() => { const c = window.eurosim.run.cols; return c.t[c.irm.findIndex(m => m === 15)] + 200; });
    await ev(t => { window.eurosim.play.playing = false; window.eurosim.play.t = t; }, tOff);
    await p.click('#nextFrame');
    const u2 = await ev(() => [document.getElementById('irText').textContent, document.querySelectorAll('#irSvg .ir-s.off').length]);
    if (!/off: B1 B2 B3 B4/.test(u2[0]) || u2[1] !== 4) fail.push('U2: ' + JSON.stringify(u2));

    // E3: klik na kamenolom (projekcija iz 3D prikaza), jedan kamen manje, simulacija sa izmenjenim stolom
    const xy = await ev(() => { const v = window.eurosim.view, g = v.elGroup.children[0];
      const pr = g.position.clone().project(v.camera), r = v.renderer.domElement.getBoundingClientRect();
      return [r.left + (pr.x + 1) / 2 * r.width, r.top + (1 - pr.y) / 2 * r.height]; });
    await p.mouse.click(xy[0], xy[1]);
    await p.waitForSelector('#elEdit:not([hidden])', { timeout: 3000 }).catch(() => fail.push('E3: nema panela kamenoloma'));
    await p.click('#elLess');
    await p.waitForFunction(() => window.eurosim.run && window.eurosim.run.meta.elements[0].stones === 2, null, { timeout: 30000 })
      .catch(() => fail.push('E3: simulacija nije dobila izmenjen kamenolom'));
    await p.click('#elReset');

    // E4: protivnik sa taktikom i PAMI; snimak ima pozicije protivnika
    await p.click('#addOpp');
    await p.fill('#oppX', '2750'); await p.dispatchEvent('#oppX', 'change');
    await p.selectOption('#oppTac', 'patrola');
    await p.click('#addPami');
    await p.click('#tabSim'); await p.click('#run'); await result();
    const e4 = await ev(() => { const c = window.eurosim.run.cols; const o = c.opp || [];
      return { n: o.length && o[0].length, moved: o.length > 1 && o[o.length - 1][0][0] !== o[0][0][0] }; });
    if (e4.n !== 2 || !e4.moved) fail.push('E4: ' + JSON.stringify(e4));
    if (process.argv[3]) await p.screenshot({ path: process.argv[3] });
    console.log(JSON.stringify({ ok: !fail.length && !errs.length, fail, errs, e1, e2, e4 }));
  } finally {
    await b.close();
  }
  process.exit(fail.length || errs.length ? 1 : 0);
})();
