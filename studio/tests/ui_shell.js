// UI test za okvir varijante A (Playwright, Node, 1366×768): bočna traka, statusna traka, STOP, Esc = STOP svuda,
// stanje veze robota; od 4.6 bez starog reda: poruka u svakom prostoru, Repo/Profil samo u bočnoj traci, Alt+1..4,
// „?“ prečice, Prikaz ▾ u dve grupe; Senzori (Zadatak 7): mreža blokova, detalj, detalj lidara, oznake izvora.   python studio/sim.py serve --no-browser &   pa:   node studio/tests/ui_shell.js [url]
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
    await p.click('#rail [data-ws=senzori]');
    // Senzori (Zadatak 7): zaglavlje, mreža 10 blokova (maketa B) bez skrolovanja na 1366×768, oznake „nepovezano“
    await p.waitForSelector('#ws-senzori .sz-tile');
    if (await p.$('#tdTabs, #ws-test-dela')) fail.push('Senzori: podkartice Test dela još postoje');
    const tiles = await p.$$eval('#ws-senzori .sz-tile', l => l.map(t => [t.dataset.id, t.querySelector('.sz-badge').textContent.trim()]));
    const ids = ['lidar', 'robot', 'brzine', 'pid', 'napajanje', 'aktuatori', 'enkoderi', 'ulazi', 'mec', 'veza'];
    if (JSON.stringify(tiles.map(t => t[0]).sort()) !== JSON.stringify([...ids].sort())) fail.push('Senzori: blokovi ' + JSON.stringify(tiles));
    if (tiles.some(t => t[1] !== 'nepovezano')) fail.push('Senzori bez veze: oznake ' + JSON.stringify(tiles));
    if (!/Ništa nije povezano/.test(await p.textContent('#ws-senzori-alati .sz-showing'))) fail.push('Senzori: zaglavlje bez „Ništa nije povezano“');
    if (!/0 radi · 0 upozorenja · 10 bez podataka/.test((await p.textContent('#ws-senzori-alati .sz-count')).replace(/[●○]\s*/g, '')))
      fail.push('Senzori: brojač ' + await p.textContent('#ws-senzori-alati .sz-count'));
    const szBox = await p.$eval('#ws-senzori', e => { const r = e.getBoundingClientRect(); return { b: r.bottom, r: r.right, sh: e.scrollHeight, ch: e.clientHeight, sw: e.scrollWidth, cw: e.clientWidth }; });
    if (szBox.b > 768 || szBox.r > 1366 || szBox.sh > szBox.ch || szBox.sw > szBox.cw) fail.push('Senzori ne staju u 1366×768: ' + JSON.stringify(szBox));
    const tileOut = await p.$$eval('#ws-senzori .sz-tile', l => l.filter(t => { const r = t.getBoundingClientRect(); return r.bottom > 768 || r.right > 1366 || r.height < 60; }).map(t => t.dataset.id));
    if (tileOut.length) fail.push('Senzori: blokovi van prozora ili preniski: ' + tileOut);
    await p.click('#ws-senzori-alati .sz-connect');                      // „Poveži robota“ iz zaglavlja: isti prozorčić
    if (!(await p.isVisible('#vezaPop'))) fail.push('Senzori: „Poveži robota“ ne otvara #vezaPop');
    await p.click('#vezaClose');
    // klik na drugi blok: detalj (Vrednosti, Kako proveriti, Izvor, Šta fali), „← Svi senzori“ u zaglavlju; Esc ga ne zatvara
    await p.click('#ws-senzori .sz-tile[data-id=enkoderi]');
    await p.waitForSelector('#ws-senzori .sz-detail');
    const cards = await p.$$eval('#ws-senzori .sz-card h5', l => l.map(h => h.textContent.trim()));
    if (cards.join() !== 'Vrednosti,Šta fali,Kako proveriti,Izvor') fail.push('Senzori detalj: kartice ' + cards);
    if (!/Nuliraj/.test(await p.textContent('#ws-senzori .sz-detail'))) fail.push('Senzori detalj enkodera: nema „Nuliraj“ u Kako proveriti');
    if (!(await p.isVisible('#ws-senzori-alati .sz-back'))) fail.push('Senzori detalj: nema „← Svi senzori“');
    await p.keyboard.press('Escape');
    if (await p.evaluate(() => window.eurosim.store.get().sensOpen) !== 'enkoderi') fail.push('Esc zatvorio detalj (Esc = samo STOP)');
    await p.click('#ws-senzori-alati .sz-back');
    await p.waitForSelector('#ws-senzori .sz-grid');
    // klik na lidar: postojeći paneli (sto + radar, kartica Lidar sa „izračunao laptop“) i „← Svi senzori“
    await p.click('#ws-senzori .sz-tile[data-id=lidar]');
    await p.waitForSelector('#liTable', { state: 'visible' });
    if (!(await p.isVisible('#liTable')) || !(await p.isVisible('#liRadar'))) fail.push('Senzori → Lidar: nema stola ili radara');
    if (!/izračunao laptop/.test(await p.textContent('#ws-lidar-info'))) fail.push('Senzori → Lidar: nema „izračunao laptop“');
    if (!(await p.isDisabled('#liOn'))) fail.push('Senzori → Lidar: Upali lidar bez ROBOT sesije nije siv');
    if (!(await p.isVisible('#ws-senzori-alati .sz-back')) || await p.isVisible('#ws-senzori')) fail.push('detalj lidara: nema „← Svi senzori“ ili se vidi mreža');
    if (await p.$('#bar, #ws-stari-alati, #repoBtn, #profBtn, .brand')) fail.push('stari red (#bar, Repo/Profile dugmad) još postoji');
    if (!(await p.$('#ws-tool:not([hidden]) #ws-poruka #msg'))) fail.push('Senzori: nema poruke u redu komandi');
    await p.click('#rail [data-act=profile]').catch(() => {});               // Profil se vidi i u Senzori (Zadatak 4.1)
    if (!(await p.isVisible('#profDialog'))) fail.push('Senzori: Profil se ne vidi');
    await p.click('#profClose').catch(() => {});
    // Repo: stavka bočne trake samo u timskom repou (4.6); dijalog se otvara iz svakog prostora
    const repoMode = await p.evaluate(() => fetch('/api/info').then(r => r.json()).then(i => (i.where || {}).mode === 'repo'));
    if (await p.isVisible('#rail [data-act=repo]') !== repoMode) fail.push('stavka Repo: vidljiva = ' + !repoMode + ', a repo = ' + repoMode);
    if (repoMode) {
      await p.click('#rail [data-act=repo]');
      if (!(await p.isVisible('#repoDialog'))) fail.push('Senzori: Repo se ne vidi');
      await p.click('#repoClose');
    }
    // Alt+1..4 = prostori, „?“ = prečice (Esc ih zatvara)
    for (const [k, ws] of [['4', 'snimci'], ['3', 'voznja'], ['1', 'taktike'], ['2', 'senzori']]) {
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
    if (await p.$('#izvori #rHost, #izvori #rPass, #izvori #rConnect, #izvori #rVirtual')) fail.push('Izvori: polja veze nisu premeštena na traku');
    if (!(await p.$('#vezaPop #rHost')) || !(await p.$('#vezaPop #rPass')) || !(await p.$('#vezaPop #rConnect')) || !(await p.$('#vezaPop #rVirtual')))
      fail.push('#vezaPop nema host / lozinku / Poveži / Virtuelni robot');
    if (!/Veza ostaje dok ne klikneš Prekini/.test(await p.textContent('#vezaPop'))) fail.push('#vezaPop: nema rečenice o vezi');
    if (await p.isVisible('#stripDisc') || !(await p.isVisible('#stripConnect'))) fail.push('traka bez sesije: treba „Poveži robota“, bez „Prekini“');
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
    await p.click('#rail [data-ws=senzori]');                         // STOP iz trake radi i u Senzori
    await p.waitForFunction(() => /simulacija/.test(document.querySelector('#ws-senzori-alati .sz-showing').textContent), null, { timeout: 3000 })
      .catch(() => fail.push('Senzori u SIM sesiji: zaglavlje ne kaže „simulacija“'));
    if (await p.textContent('#ws-senzori .sz-tile[data-id=brzine] .sz-badge') !== 'SIM') fail.push('Senzori u SIM sesiji: Brzine nisu SIM');
    if (await p.textContent('#ws-senzori .sz-tile[data-id=napajanje] .sz-badge') !== 'nepovezano') fail.push('Senzori u SIM sesiji: Napajanje nije nepovezano');
    await p.click('#stripStop');
    await p.waitForTimeout(300);
    if (await stops() !== n + 1) fail.push('STOP iz trake (Senzori) nije poslao ["stop"]');
    await p.click('#rail [data-ws=voznja]');
    await p.click('#endBtn');
    await p.waitForFunction(() => !window.eurosim.store.get().session, null, { timeout: 15000 });

    // --- virtuelni robot: posle prekida telemetrije „podaci stari“, pa „veza izgubljena“ ---
    await p.click('#rail [data-drive=robot]');
    // editor u Taktikama ima nesačuvan tekst (gore je otkucano „wai“): Pošalji bi slao taj tekst -> napomena edNote
    if ((await shownIds()).join() !== 'ti-taktika,ti-strana,izvoriBtn,sessStart,edNote') fail.push('Vožnja ROBOT bez sesije: ' + await shownIds());
    if (await p.$('#card-esp:not(.ws-off), #card-sto:not(.ws-off)')) fail.push('ROBOT: ESP ili Postavka stola se vidi');
    await p.click('#sessStart');                                   // ROBOT: otvara #vezaPop (isti kao sa trake), ne Izvori
    if (!(await p.isVisible('#vezaPop')) || (await p.isVisible('#izvori'))) fail.push('ROBOT „▶ Pokreni sesiju“ ne otvara #vezaPop');
    await p.keyboard.press('Escape');                              // Esc zatvara prozorčić
    if (await p.isVisible('#vezaPop')) fail.push('Esc ne zatvara #vezaPop');
    await p.click('#stripConnect');                                // traka: isti prozorčić; ✕ ga zatvara
    if (!(await p.isVisible('#vezaPop'))) fail.push('„Poveži robota“ ne otvara #vezaPop');
    await p.click('#vezaClose');
    if (await p.isVisible('#vezaPop')) fail.push('✕ ne zatvara #vezaPop');
    await p.click('#stripConnect');
    await p.click('#ws-tool', { position: { x: 2, y: 2 } });       // klik van prozorčića ga zatvara
    if (await p.isVisible('#vezaPop')) fail.push('klik van ne zatvara #vezaPop');
    await p.click('#stripConnect');
    await p.click('#rVirtual');
    await p.waitForFunction(() => /ROBOT/.test(document.getElementById('stripSrc').textContent), null, { timeout: 15000 });
    await p.waitForFunction(() => document.getElementById('stripLink').textContent === 'povezan', null, { timeout: 20000 });
    if ((await shownIds()).join() !== 'ti-taktika,ti-strana,rPush,rRun,followBtn,endBtn,edNote') fail.push('Vožnja ROBOT sesija: ' + await shownIds());
    if (!(await p.isVisible('#stripDisc')) || await p.isVisible('#stripConnect')) fail.push('traka ROBOT: treba „Prekini“, bez „Poveži robota“');
    await p.click('#rail [data-ws=senzori]');                         // Senzori sa virtuelnim robotom: SIM (nije pravi), bez „Poveži robota“
    await p.waitForFunction(() => /virtuelni robot/.test(document.querySelector('#ws-senzori-alati .sz-showing').textContent), null, { timeout: 3000 })
      .catch(() => fail.push('Senzori uz virtuelnog robota: zaglavlje ne kaže „virtuelni robot“'));
    if (await p.isVisible('#ws-senzori-alati .sz-connect')) fail.push('Senzori uz robota: „Poveži robota“ se i dalje vidi');
    if (await p.textContent('#ws-senzori .sz-tile[data-id=veza] .sz-badge') !== 'SIM') fail.push('Senzori uz virtuelnog robota: Veza nije SIM');
    await p.click('#rail [data-ws=voznja]');
    if (await p.isVisible('#vezaPop')) fail.push('#vezaPop ostao otvoren posle povezivanja');
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
    await p.click('#stripDisc');                                    // Prekini sa trake (isto što i „Prekini vezu“ u Vožnji)
    await p.waitForFunction(() => !window.eurosim.store.get().session, null, { timeout: 15000 });
  } catch (e) {
    fail.push('izuzetak: ' + e.message);
  }
  await b.close();
  const ok = !fail.length && !errs.length;
  console.log(JSON.stringify({ ok, fail, errs }));
  process.exit(ok ? 0 : 1);
})();
