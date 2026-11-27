// UI test za okvir varijante A (Playwright, Node, 1366×768): bočna traka, statusna traka, STOP, Esc = STOP svuda,
// stanje veze robota; od 4.6 bez starog reda: poruka u svakom prostoru, Repo/Profil samo u bočnoj traci, Alt+1..4,
// „?“ prečice, Prikaz ▾ u dve grupe.   python simulator/sim.py serve --no-browser &   pa:   node simulator/tests/ui_shell.js [url]
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
    // Test dela (Zadatak 5.2): podkartice (radi samo Lidar), sto + radar, kartica Lidar sa „izračunao laptop“
    const tabs = await p.$$eval('#tdTabs button', l => l.map(b => [b.textContent.trim(), b.disabled]));
    if (JSON.stringify(tabs) !== JSON.stringify([['Lidar', false], ['Pogon', true], ['Mehanizmi', true], ['IR', true]]))
      fail.push('Test dela: podkartice ' + JSON.stringify(tabs));
    if (!(await p.isVisible('#liTable')) || !(await p.isVisible('#liRadar'))) fail.push('Test dela → Lidar: nema stola ili radara');
    if (!/izračunao laptop/.test(await p.textContent('#ws-lidar-info'))) fail.push('Test dela → Lidar: nema „izračunao laptop“');
    if (!(await p.isDisabled('#liOn'))) fail.push('Test dela → Lidar: Upali lidar bez ROBOT sesije nije siv');
    if (await p.$('#bar, #ws-stari-alati, #repoBtn, #profBtn, .brand')) fail.push('stari red (#bar, Repo/Profile dugmad) još postoji');
    if (!(await p.$('#ws-tool:not([hidden]) #ws-poruka #msg'))) fail.push('Test dela: nema poruke u redu komandi');
    await p.click('#rail [data-act=profile]').catch(() => {});               // Profil se vidi i u Test dela (Zadatak 4.1)
    if (!(await p.isVisible('#profDialog'))) fail.push('Test dela: Profil se ne vidi');
    await p.click('#profClose').catch(() => {});
    // Repo: stavka bočne trake samo u timskom repou (4.6); dijalog se otvara iz svakog prostora
    const repoMode = await p.evaluate(() => fetch('/api/info').then(r => r.json()).then(i => (i.where || {}).mode === 'repo'));
    if (await p.isVisible('#rail [data-act=repo]') !== repoMode) fail.push('stavka Repo: vidljiva = ' + !repoMode + ', a repo = ' + repoMode);
    if (repoMode) {
      await p.click('#rail [data-act=repo]');
      if (!(await p.isVisible('#repoDialog'))) fail.push('Test dela: Repo se ne vidi');
      await p.click('#repoClose');
    }
    // Alt+1..4 = prostori, „?“ = prečice (Esc ih zatvara)
    for (const [k, ws] of [['4', 'snimci'], ['3', 'voznja'], ['1', 'taktike'], ['2', 'test']]) {
      await p.keyboard.press('Alt+' + k);
      if (await p.evaluate(() => window.eurosim.store.get().ws) !== ws) fail.push('Alt+' + k + ' nije ' + ws);
      if (!(await p.$(`#rail [data-ws=${ws}].on`))) fail.push('bočna traka ne prati Alt+' + k);
    }
    await p.keyboard.press('Shift+Slash');
    if (!(await p.isVisible('#railHelp'))) fail.push('„?“ ne otvara prečice');
    if (!/Alt\+1/.test(await p.textContent('#railHelp'))) fail.push('prečice: nema Alt+1..4');
    await p.keyboard.press('Escape');
    if (await p.isVisible('#railHelp')) fail.push('Esc ne zatvara prečice');

    // --- regioni (Zadatak 4.1): teren u glavnom delu, vreme + grafici dole, grafici sklopivi i zapamćeni ---
    await p.click('#rail [data-ws=taktike]');
    await p.waitForSelector('#ws-editor:not(.ed-closed)', { timeout: 10000 }).catch(() => fail.push('Taktike: editor se nije otvorio'));
    for (const id of ['#ws-teren #viewwrap', '#ws-editor #editorPane', '#ws-vreme #timeline', '#ws-grafici #charts', '#ws-tool #ws-poruka #msg',
      '#ws-side #card-koraci #steps', '#ws-side #card-dnevnik #log', '#ws-side #card-dnevnik #showProto', '#ws-side #card-dnevnik #logErrOnly'])
      if (!(await p.$(id))) fail.push('region: nema ' + id);
    if (await p.$('#side-panel, #card-stari-paneli')) fail.push('stari-paneli još postoji');
    // Red komandi Taktika (Zadatak 4.3): Taktika, Strana, meč | test, ▶ Pokreni; Komande kao kartica u editoru
    for (const id of ['#ws-tool #ws-taktike-alati #tactic', '#ws-taktike-alati #sideSeg', '#ws-taktike-alati #modeSeg',
      '#ws-taktike-alati #run', '#ws-editor #edCommands #apiList', '#ws-editor #edClose'])
      if (!(await p.$(id))) fail.push('Taktike alati: nema ' + id);
    if (await p.$('#edBtn, #rowSim, #apiDrawer, #edCmdBtn')) fail.push('stari ✎ Editor / Simulate red / fioka Commands još postoje');
    // Prikaz ▾ (4.6): dve grupe, „Šta crtam“ i „Kako izgleda“
    await p.click('#viewMenuBtn');
    const groups = await p.$$eval('#viewMenu .vm-g', l => l.map(g => [g.querySelector('.vm-h').textContent, g.querySelectorAll('label').length]));
    if (JSON.stringify(groups) !== JSON.stringify([['Šta crtam', 7], ['Kako izgleda', 3]])) fail.push('Prikaz ▾ grupe: ' + JSON.stringify(groups));
    await p.click('#viewMenuBtn');
    await p.click('#edClose');                                       // × zatvara editor, sto dobija celu širinu
    await p.waitForSelector('#ws-editor.ed-closed');
    if (!(await p.isVisible('#edOpen'))) fail.push('„✎ Editor“ se ne vidi kad je editor zatvoren');
    await p.click('#edOpen');
    await p.waitForSelector('#ws-editor:not(.ed-closed) .cm-content');
    // Taktike: Koraci otvoreni, Dnevnik sklopljen, Korak sada i Stanje i IR nisu u ovom prostoru (Zadatak 4.2)
    const tkCards = await p.$$eval('#ws-side > .ws-card:not(.ws-off)', l => l.map(c => c.id + (c.classList.contains('closed') ? '-' : '+')));
    if (tkCards.join() !== 'card-koraci+,card-sto-,card-dnevnik-') fail.push('Taktike kartice: ' + tkCards);   // + Postavka stola (4.4)
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
    // Red komandi Vožnja (Zadatak 4.4/5.1): bez sesije „Izvori ▾“ + „▶ Pokreni sesiju“; stari redovi Live/Robot, STOP-ovi,
    // izbor „Lidar:“ i dijalog Poveži obrisani
    const shownIds = () => p.$$eval('#ws-voznja-alati > [id], #ws-voznja-alati .tool-item', l => l.filter(e => e.offsetParent).map(e => e.id));
    if ((await shownIds()).join() !== 'ti-taktika,ti-strana,izvoriBtn,sessStart') fail.push('Vožnja SIM bez sesije: ' + await shownIds());
    if (await p.$('#lidarSrc, #lidarWrap, #robotConnect, #rCancel')) fail.push('stari izbor Lidar ili dijalog Poveži još postoji');
    // Izvori (Zadatak 5.1): a/b/c/d, c sivo sa razlogom; b -> HIBRID; a nazad
    await p.click('#izvoriBtn');
    if (!(await p.isVisible('#izvori'))) fail.push('Izvori ▾ ne otvara blok Izvori');
    if (!(await p.$eval('#izvPresets [data-p=c]', b => b.disabled && /Fazom 6/.test(b.title)))) fail.push('Izvori: c nije sivo sa razlogom');
    if (!(await p.$eval('#izvParts tr[data-part=mehanizmi] .izv-why', e => /Fazom 6/.test(e.textContent)))) fail.push('Izvori: nema razloga za lažiran');
    if (!(await p.$('#izvori #rHost')) || !(await p.$('#izvori #rVirtual'))) fail.push('Izvori: nema veze sa robotom');
    await p.click('#izvPresets [data-p=b]');
    if (await p.textContent('#izvoriBtn') !== 'Izvori: hibrid, pravi lidar ▾') fail.push('Izvori b: ' + await p.textContent('#izvoriBtn'));
    await p.click('#izvPresets [data-p=a]');
    await p.click('#izvClose');
    if (await p.$('#tabSim, #tabLive, #tabRobot, #rowLive, #rowRobot, #liveGroup, #robotGroup, #liveBtn, #robotBtn, #stopBtn, #rStop, #rFollow, #rEnd, #robotStatus'))
      fail.push('stari Live/Robot redovi ili dugmad još postoje');
    if (!(await p.$('#ws-voznja-alati #tactic'))) fail.push('Vožnja: Taktika nije u redu komandi');
    if (!(await p.$eval('#ws-editor', e => e.classList.contains('ws-off')))) fail.push('Vožnja: editor nije skriven (samo Taktike)');
    if ((await p.$eval('#ws-tool', e => e.getBoundingClientRect().height)) > 56) fail.push('red komandi Vožnja viši od 56 px');
    await p.click('#sessStart');
    await p.waitForFunction(() => window.eurosim.run && window.eurosim.run.live, null, { timeout: 15000 });
    await p.waitForFunction(() => (window.eurosim.store.get().caps || []).includes('arm'), null, { timeout: 15000 });   // hello
    if ((await shownIds()).join() !== 'ti-taktika,ti-strana,armBtn,cordBtn,testBtn,paceWrap,pauseBtn,followBtn,endBtn')
      fail.push('Vožnja SIM sesija: ' + await shownIds());
    if (await p.textContent('#endBtn') !== 'Završi') fail.push('SIM: nema „Završi“');
    // Vožnja SIM: ESP, Korak sada, Koraci otvoreni (najviše tri), Postavka stola, Dnevnik, Stanje i IR sklopljeni
    const vzCards = await p.$$eval('#ws-side > .ws-card:not(.ws-off)', l => l.map(c => c.id + (c.classList.contains('closed') ? '-' : '+')));
    if (vzCards.join() !== 'card-esp+,card-korak+,card-koraci+,card-sto-,card-dnevnik-,card-stanje-') fail.push('Vožnja kartice: ' + vzCards);
    if (!(await p.$('#card-esp #espPanel canvas'))) fail.push('ESP nije u kartici ESP');
    await p.click('#card-sto .ws-card-h');                         // Postavka stola: + Protivnik šalje obstacles u sesiju
    await p.click('#addOpp');
    await p.waitForTimeout(300);
    if (!(await p.isVisible('#card-sto #oppEdit'))) fail.push('uređivač protivnika nije u kartici Postavka stola');
    if (!(await p.evaluate(() => window.__sent.some(s => /^\["obstacles"/.test(s))))) fail.push('+ Protivnik nije poslao obstacles');
    await p.click('#card-sto .ws-card-h');
    await p.click('#rail [data-drive=robot]');                     // SIM -> ROBOT dok sesija radi: odbijeno
    if (!/Sesija radi: prvo je završi/.test(await p.textContent('#stripNotice'))) fail.push('SIM -> ROBOT tokom sesije: nema poruke');
    if (await p.evaluate(() => window.eurosim.store.get().drive) !== 'sim') fail.push('SIM -> ROBOT tokom sesije nije odbijen');
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
    await p.click('#rail [data-ws=taktike]');                     // editor vidljiv; bez starog setTab dok Live radi (4.3)
    await p.waitForSelector('#ws-editor:not(.ws-off) .cm-content');
    await p.waitForFunction(() => /from tac import/.test(document.querySelector('.cm-content').textContent));
    if (!(await p.evaluate(() => !!window.eurosim.store.get().session))) fail.push('prelaz u Taktike ugasio sesiju');
    if (/end Live first/.test(await p.textContent('#msg'))) fail.push('Taktike tokom Live: „end Live first“');
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
    // editor u Taktikama ima nesačuvan tekst (gore je otkucano „wai“): Pošalji bi slao taj tekst -> napomena edNote
    if ((await shownIds()).join() !== 'ti-taktika,ti-strana,izvoriBtn,sessStart,edNote') fail.push('Vožnja ROBOT bez sesije: ' + await shownIds());
    if (await p.$('#card-esp:not(.ws-off), #card-sto:not(.ws-off)')) fail.push('ROBOT: ESP ili Postavka stola se vidi');
    await p.click('#sessStart');                                   // ROBOT: otvara Izvori (veza sa robotom)
    await p.click('#rVirtual');
    await p.waitForFunction(() => /ROBOT/.test(document.getElementById('stripSrc').textContent), null, { timeout: 15000 });
    await p.waitForFunction(() => document.getElementById('stripLink').textContent === 'povezan', null, { timeout: 20000 });
    if ((await shownIds()).join() !== 'ti-taktika,ti-strana,rPush,rRun,followBtn,endBtn,edNote') fail.push('Vožnja ROBOT sesija: ' + await shownIds());
    if (await p.textContent('#endBtn') !== 'Prekini vezu') fail.push('ROBOT: nema „Prekini vezu“');
    await p.click('#rPush');
    await p.waitForFunction(() => /^push: OK/.test(document.getElementById('msg').textContent), null, { timeout: 10000 })
      .catch(() => fail.push('Pošalji: nema „push: OK“'));
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
    await p.click('#endBtn');                                      // Prekini vezu
    await p.waitForFunction(() => !window.eurosim.store.get().session, null, { timeout: 15000 });
  } catch (e) {
    fail.push('izuzetak: ' + e.message);
  }
  await b.close();
  const ok = !fail.length && !errs.length;
  console.log(JSON.stringify({ ok, fail, errs }));
  process.exit(ok ? 0 : 1);
})();
