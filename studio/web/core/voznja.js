// Vožnja (Zadatak 4.4) bez DOM-a, da ga uveze i `node --test`: šta red komandi Vožnja pokazuje i kada se vide
// kartice ESP i Postavka stola. Sve zavisi samo od stanja u store-u (piše ga app.js):
//   drive      'sim' | 'robot'                        izbor u bočnoj traci (ispod Vožnje)
//   session    null | {kind: 'sim'|'robot', edText}   sesija radi; edText = pokrenuta sa nesačuvanim tekstom editora
//   caps       null | [cap] | Set                      mogućnosti sesije iz poruke hello (/ws/session); null bez sesije
//   edUnsaved  bool                                   editor (Taktike) je otvoren i tekst nije sačuvan
//
//   voznjaTools(st) -> {kind, izvori, start, arm, cord, test, speed, pause, push, run, follow, end, endLabel, note}
//     bez sesije: „Izvori ▾“ (blok Izvori, Zadatak 5.1; zamenio izbor „Lidar:“) i „▶ Pokreni sesiju“ (SIM: Live;
//     ROBOT: prozorčić „Poveži robota“: Poveži, Virtuelni robot);
//     sesija radi: svaka komanda samo ako je sesija ima u caps (pre poruke hello: nijedna), Prati i Završi /
//     Prekini vezu uvek; note = „koristi se tekst iz editora (nesačuvan)“ kad Live / Pošalji koriste tekst editora
//   espShown(st)          ESP ekran: sesija sa esp_screen (pre hello: SIM da, ROBOT ne); bez sesije samo uz SIM
//                         (snimljen ekran tekućeg snimka, tasteri ugašeni)
//   stoShown(st, ws)      Postavka stola: u Taktikama uvek, u Vožnji samo za SIM (sesija ili izbor)
//   TOOL_IDS              ključ iz voznjaTools -> id elementa u redu komandi (panels/voznja-alati.js)

export const TOOL_IDS = {
  izvori: 'izvoriBtn', start: 'sessStart', arm: 'armBtn', cord: 'cordBtn', test: 'testBtn', speed: 'paceWrap',
  pause: 'pauseBtn', push: 'rPush', run: 'rRun', follow: 'followBtn', end: 'endBtn', note: 'edNote',
};

export function hasCap(caps, c) {
  if (!caps) return false;
  return caps instanceof Set ? caps.has(c) : Array.isArray(caps) && caps.includes(c);
}

export const driveKind = st => (st.session ? (st.session.kind === 'robot' ? 'robot' : 'sim') : (st.drive === 'robot' ? 'robot' : 'sim'));

export function voznjaTools(st = {}) {
  const kind = driveKind(st), on = !!st.session, has = c => on && hasCap(st.caps, c);
  let note = false;
  if (!on) note = !!st.edUnsaved;                                  // SIM: Live uzima tekst editora; ROBOT: Pošalji posle
  else if (kind === 'robot') note = !!st.edUnsaved && has('push');
  else note = !!st.session.edText;                                 // Live je pokrenut sa tim tekstom
  return {
    kind,
    izvori: !on,
    start: !on,
    arm: has('arm'), cord: has('cord'), test: has('test'),
    speed: has('speed'), pause: has('pause'),
    push: has('push'), run: has('run'),
    follow: on, end: on,
    endLabel: kind === 'robot' ? 'Prekini vezu' : 'Završi',
    note,
  };
}

export function espShown(st = {}) {              // pre poruke hello (caps null) po vrsti sesije, da kartica ne treperi
  if (st.session && st.caps) return hasCap(st.caps, 'esp_screen');
  return driveKind(st) !== 'robot';
}

export function stoShown(st = {}, ws = st.ws) {
  return ws !== 'voznja' || driveKind(st) === 'sim';
}
