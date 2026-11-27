// UI test za okvir varijante A (Playwright, Node, 1366×768): bočna traka, statusna traka, STOP, Esc = STOP svuda,
// stanje veze robota.   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_shell.js [url]
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2] || 'http://localhost:8270/';
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1366, height: 768 } });
  const errs = [], fail = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.addInitScript(() => {                         // beleži sve što stranica pošalje preko WebSocket-a
    window.__sent = [];
    const send = WebSocket.prototype.send;
    WebSocket.prototype.send = function (d) { window.__sent.push(d); return send.call(this, d); };
  });
  await p.goto(url);
  await p.evaluate(() => localStorage.clear());
  await p.reload();
  await p.waitForSelector('#tactic option', { state: 'attached' });
  await p.selectOption('#tactic', 'primer');
  const stops = () => p.evaluate(() => window.__sent.filter(s => s === '["stop"]').length);
  const linkText = () => p.textContent('#stripLink');
  try {
    // --- okvir ---
    const items = await p.$$eval('#rail [data-ws]', l => l.map(x => x.textContent.trim()));
    if (items.length !== 4) fail.push('bočna traka: ' + items.length + ' stavke');
    if (!/SIM/.test(await p.textContent('#stripSrc'))) fail.push('traka ne pokazuje SIM');
    const box = await p.$eval('#stripStop', e => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, h: r.height, w: r.width }; });
    if (!(box.l >= 0 && box.t >= 0 && box.r <= 1366 && box.b <= 768)) fail.push('STOP nije ceo u prozoru: ' + JSON.stringify(box));
    if (box.h < 54 || box.w < 150) fail.push('STOP premali: ' + JSON.stringify(box));
    if (!(await p.isVisible('#stripStop'))) fail.push('STOP nije vidljiv');
    if ((await p.$eval('#strip', e => e.getBoundingClientRect().height)) !== 72) fail.push('traka nije visoka 72 px');
    await p.click('#rail [data-ws=test]');
    if (!/Test dela dolazi u Fazi 5/.test(await p.textContent('#content'))) fail.push('Test dela: nema poruke');
    if (await p.isVisible('#bar')) fail.push('Test dela: stari UI se vidi');
    await p.click('#rail [data-act=profile]').catch(() => {});               // Profil se vidi i u Test dela (Zadatak 4.1)
    if (!(await p.isVisible('#profDialog'))) fail.push('Test dela: Profil se ne vidi');
    await p.click('#profClose').catch(() => {});

    // --- regioni (Zadatak 4.1): teren u glavnom delu, vreme + grafici dole, grafici sklopivi i zapamćeni ---
    await p.click('#rail [data-ws=taktike]');
    await p.waitForSelector('#ws-editor:not(.ed-closed)', { timeout: 10000 }).catch(() => fail.push('Taktike: editor se nije otvorio'));
    for (const id of ['#ws-teren #viewwrap', '#ws-editor #editorPane', '#ws-vreme #timeline', '#ws-grafici #charts', '#ws-stari-alati #bar',
      '#ws-side #card-koraci #steps', '#ws-side #card-dnevnik #log', '#ws-side #card-dnevnik #showProto', '#ws-side #card-dnevnik #logErrOnly'])
      if (!(await p.$(id))) fail.push('region: nema ' + id);
    if (await p.$('#side-panel, #card-stari-paneli')) fail.push('stari-paneli još postoji');
    // Taktike: Koraci otvoreni, Dnevnik sklopljen, Korak sada i Stanje i IR nisu u ovom prostoru (Zadatak 4.2)
    const tkCards = await p.$$eval('#ws-side > .ws-card:not(.ws-off)', l => l.map(c => c.id + (c.classList.contains('closed') ? '-' : '+')));
    if (tkCards.join() !== 'card-koraci+,card-dnevnik-') fail.push('Taktike kartice: ' + tkCards);
    if (!(await p.$eval('#card-grafici', e => e.classList.contains('closed')))) fail.push('Taktike: grafici nisu sklopljeni');
    const terenH = await p.$eval('#ws-teren', e => e.getBoundingClientRect().height);
    if (terenH < 420) fail.push('teren nizak: ' + terenH);
    await p.click('#card-grafici .ws-card-h');
    if (!(await p.isVisible('#charts'))) fail.push('grafici se ne otvaraju');
    await p.reload(); await p.waitForSelector('#tactic option', { state: 'attached' });
    if (await p.$eval('#card-grafici', e => e.classList.contains('closed'))) fail.push('grafici: stanje nije zapamćeno');
    await p.click('#card-grafici .ws-card-h');

    // --- Live: Esc šalje STOP, i iz editora sa otvorenim popupom dopune ---
    await p.click('#rail [data-ws=voznja]');
    await p.click('#rail [data-drive=sim]');
    if (!(await p.$eval('#tabLive', e => e.classList.contains('on')))) fail.push('Vožnja SIM nije otvorila Live');
    await p.click('#liveBtn');
    await p.waitForFunction(() => window.eurosim.run && window.eurosim.run.live, null, { timeout: 15000 });
    // Vožnja: Korak sada, Koraci, Dnevnik otvoreni, Stanje i IR sklopljeno; kolona ne skroluje (Zadatak 4.2)
    const vzCards = await p.$$eval('#ws-side > .ws-card:not(.ws-off)', l => l.map(c => c.id + (c.classList.contains('closed') ? '-' : '+')));
    if (vzCards.join() !== 'card-korak+,card-koraci+,card-dnevnik+,card-stanje-') fail.push('Vožnja kartice: ' + vzCards);
    await p.click('#card-stanje .ws-card-h');                      // IR: klik na senzor u Live = ir_mask
    await p.waitForSelector('#irBox .ir-s.click');
    await p.click('#irBox .ir-s.click');
    await p.waitForTimeout(300);
    if (!(await p.evaluate(() => window.__sent.some(s => /ir_mask/.test(s))))) fail.push('IR klik nije poslao ir_mask');
    const side = await p.$eval('#ws-side', e => [e.scrollHeight, e.clientHeight]);
    if (side[0] > side[1]) fail.push('bočna kolona skroluje: ' + side);
    await p.click('#armBtn'); await p.waitForTimeout(600);
    await p.click('#cordBtn'); await p.waitForTimeout(1500);
    if (!/MEČ/.test(await p.textContent('#stripMatch'))) fail.push('traka: meč ne odbrojava: ' + await p.textContent('#stripMatch'));
    let n = await stops();
    await p.evaluate(() => document.activeElement && document.activeElement.blur());   // fokus van polja
    await p.keyboard.press('Escape');
    await p.waitForTimeout(300);
    if (await stops() !== n + 1) fail.push('Esc (sto) nije poslao ["stop"]');
    await p.click('#rail [data-ws=taktike]');                     // editor se otvara; kartica Simulate odbijena dok Live radi
    await p.waitForSelector('.cm-content');
    await p.waitForFunction(() => /from tac import/.test(document.querySelector('.cm-content').textContent));
    if (!(await p.evaluate(() => !!window.eurosim.store.get().session))) fail.push('prelaz u Taktike ugasio sesiju');
    await p.click('.cm-content'); await p.keyboard.press('Control+End');
    await p.keyboard.type('\nwai');
    await p.keyboard.press('Control+Space');
    await p.waitForSelector('.cm-tooltip-autocomplete li');
    n = await stops();
    await p.keyboard.press('Escape');
    await p.waitForTimeout(300);
    if (await stops() !== n + 1) fail.push('Esc iz editora (popup dopune) nije poslao ["stop"]');
    if (await p.$('.cm-tooltip-autocomplete')) fail.push('Esc nije zatvorio popup dopune');
    n = await stops();
    await p.click('#rail [data-ws=test]');                         // STOP iz trake radi i u Test dela
    await p.click('#stripStop');
    await p.waitForTimeout(300);
    if (await stops() !== n + 1) fail.push('STOP iz trake (Test dela) nije poslao ["stop"]');
    await p.click('#rail [data-ws=voznja]');
    await p.click('#endBtn');
    await p.waitForFunction(() => !window.eurosim.store.get().session, null, { timeout: 15000 });

    // --- virtuelni robot: posle prekida telemetrije „podaci stari“, pa „veza izgubljena“ ---
    await p.click('#rail [data-drive=robot]');
    await p.click('#robotBtn');
    await p.click('#rVirtual');
    await p.waitForFunction(() => /ROBOT/.test(document.getElementById('stripSrc').textContent), null, { timeout: 15000 });
    await p.waitForFunction(() => document.getElementById('stripLink').textContent === 'povezan', null, { timeout: 20000 });
    await p.evaluate(() => fetch('/api/vrobot', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'stop' }) }));
    await p.waitForFunction(() => /podaci stari/.test(document.getElementById('stripLink').textContent), null, { timeout: 5000 })
      .catch(async () => fail.push('nema „podaci stari“: ' + await linkText()));
    await p.waitForFunction(() => /veza izgubljena/.test(document.getElementById('stripLink').textContent), null, { timeout: 10000 })
      .catch(async () => fail.push('nema „veza izgubljena“: ' + await linkText()));
    n = await stops();
    await p.keyboard.press('Escape');                              // STOP i dalje šalje kad je veza izgubljena
    await p.waitForTimeout(300);
    if (await stops() !== n + 1) fail.push('Esc (robot, veza izgubljena) nije poslao ["stop"]');
    await p.click('#rEnd');
    await p.waitForFunction(() => !window.eurosim.store.get().session, null, { timeout: 15000 });
  } catch (e) {
    fail.push('izuzetak: ' + e.message);
  }
  await b.close();
  const ok = !fail.length && !errs.length;
  console.log(JSON.stringify({ ok, fail, errs }));
  process.exit(ok ? 0 : 1);
})();
