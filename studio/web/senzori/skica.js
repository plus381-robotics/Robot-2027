// Senzori: skica robota SPREDA i POZADI (blok „Robot · IR“) i IR lampice (i u uglovima bloka „Odozgo · lidar“). Bez DOM-a:
// raspored se računa ovde (testira ga `node --test`), a crta se u blokovi/robot.js; lamp() crta jednu lampicu na dato platno.
//   IR_NAMES                        FLD FLU FRD FRU BLD BLU BRD BRU: redosled bitova `ir` / `irm` (plant.sensor_layout)
//   sketchGeometry(profile)         {w, len, h, irLow, irHigh, driveTrack, odoTrack, wheelD, wheelW} u mm iz Profila: [body]
//                                   width/length/height, [ir] low_z/high_z, [drive] wheel_track/wheel_diameter/wheel_width,
//                                   [odometry] encoder_track. Šta fali (ili nema Profila): mere robota 2027.
//   screenSide(robotLeft, view)     +1 = desno na ekranu, -1 = levo. 'spreda' = stojiš ispred robota (levo robota je tebi
//                                   desno), 'pozadi' = stojiš iza robota (levo robota je tebi levo)
//   irAt(name)                      {front, left, upper} iz imena (F/B napred-nazad, L/R levo-desno, D/U donji-gornji)
//   irSensors(profile)              [{name, bit, front, left, upper}]: bit = mesto u profile.ir_sensors. Imena su fizička
//                                   (kao na robotu); na plavoj strani ih taktika zove sa zamenjenim L i R (tac._ir_bits)
//   cornerOn(sensors, ir, front, left)  ugao vidi (D ili U); ir null -> null (nema podataka)
//   elevation(geo, sensors, box, view, big)  raspored jedne skice u pravougaoniku box {x, y, w, h} (px):
//       k (px po mm), cx, gy (pod), X(mm bočno, + = levo robota) i Z(mm visine) -> px,
//       body [x0, y0, x1, y1]; lidar {mount, box, scanY, scanX: [x0, x1], labelY}: lidar je UVEK na vrhu tela (činjenica
//       sa robota; [lidar] z iz Profila je ravan simuliranog lidara i ovde se ne koristi);
//       drive [{left, x, rect}] pogonski točkovi (±wheel_track/2); odo [{name: 'L'|'D', left, x, rect, text: {x, y, align}}]
//       pasivni odometrijski točkovi (±encoder_track/2), mm se pišu iznad, od spoljne ivice ka sredini;
//       lamps [{name, bit, upper, left, x, y, r, label: {x, align}}] IR te strane (D na low_z, U na high_z, uz ivicu tela);
//       title ['SPREDA', '(stojiš ispred robota)'] | ['POZADI', '(stojiš iza robota)'], sides {left, right}: koja strana
//       robota je levo / desno na ekranu ('desno r.' / 'levo r.'), font (px) za natpise
//   lamp(g, x, y, r, on, txt)       lampica: on true zeleno (svetli), false prazno, null isprekidano (nema podataka)

export const IR_NAMES = ['FLD', 'FLU', 'FRD', 'FRU', 'BLD', 'BLU', 'BRD', 'BRU'];

const DEF = { width: 300, length: 165, height: 350, low_z: 40, high_z: 340, wheel_track: 166, wheel_diameter: 65,
  wheel_width: 40, encoder_track: 286 };
const BODY_CLEAR = 18;                  // skica: telo malo iznad poda (nije iz Profila)
const LIDAR_MOUNT = 8, LIDAR_H = 34, LIDAR_W = 76, MOUNT_W = 56;   // nosač i lidar (RPLIDAR A2) na vrhu tela, mm
const ODO_W = 12, ODO_D = 40;           // pasivni odometrijski točak na skici (mere nisu u Profilu)

const size = (v, d) => (typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : d);
const height = (v, d) => (typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : d);

export function sketchGeometry(profile) {
  const p = profile || {}, b = p.body || {}, ir = p.ir || {}, dr = p.drive || {}, od = p.odometry || {};
  return {
    w: size(b.width, DEF.width), len: size(b.length, DEF.length), h: size(b.height, DEF.height),
    irLow: height(ir.low_z, DEF.low_z), irHigh: height(ir.high_z, DEF.high_z),
    driveTrack: size(dr.wheel_track, DEF.wheel_track), odoTrack: size(od.encoder_track, DEF.encoder_track),
    wheelD: size(dr.wheel_diameter, DEF.wheel_diameter), wheelW: size(dr.wheel_width, DEF.wheel_width),
  };
}

export const screenSide = (robotLeft, view) => ((view === 'spreda') === !!robotLeft ? 1 : -1);

export function irAt(name) {
  const n = String(name || '').toUpperCase();
  return { front: n[0] === 'F', left: n[1] === 'L', upper: n[2] === 'U' };
}

export function irSensors(profile) {
  const list = profile && Array.isArray(profile.ir_sensors) && profile.ir_sensors.length
    ? profile.ir_sensors.map(s => String(s.name)) : IR_NAMES;
  return list.map((name, bit) => ({ name, bit, ...irAt(name) }));
}

export function cornerOn(sensors, ir, front, left) {
  if (ir == null) return null;
  return sensors.some(s => s.front === front && s.left === left && (ir >> s.bit) & 1);
}

const rect = (xa, ya, xb, yb) => [Math.min(xa, xb), Math.min(ya, yb), Math.max(xa, xb), Math.max(ya, yb)];

export function elevation(geo, sensors, box, view, big = false) {
  const m = big ? { side: 200, below: 46, above: 22, r: 12, font: 14 } : { side: 120, below: 32, above: 16, r: 8, font: 11 };
  const top = geo.h + LIDAR_MOUNT + LIDAR_H;                       // najviša tačka robota (vrh lidara), mm
  const k = Math.max(0.01, Math.min((box.w - m.side) / geo.w, (box.h - m.below - m.above) / top));
  const cx = box.x + box.w / 2, gy = box.y + box.h - m.below, s = screenSide(true, view);
  const X = mm => cx + s * mm * k, Z = mm => gy - mm * k;
  const body = rect(X(-geo.w / 2), Z(geo.h), X(geo.w / 2), Z(BODY_CLEAR));
  const lbox = rect(X(-LIDAR_W / 2), Z(top), X(LIDAR_W / 2), Z(geo.h + LIDAR_MOUNT));
  const reach = big ? 30 : 22;
  const lidar = { mount: rect(X(-MOUNT_W / 2), Z(geo.h + LIDAR_MOUNT), X(MOUNT_W / 2), Z(geo.h)), box: lbox,
    scanY: Z(geo.h + LIDAR_MOUNT + LIDAR_H / 2), scanX: [body[0] - reach, body[2] + reach], labelY: lbox[1] - 4 };
  const wheel = (lat, w, d) => { const x = X(lat); return { x, rect: rect(x - w / 2 * k, Z(d), x + w / 2 * k, Z(0)) }; };
  const drive = [true, false].map(left => ({ left, ...wheel((left ? 1 : -1) * geo.driveTrack / 2, geo.wheelW, geo.wheelD) }));
  const odo = [true, false].map(left => {
    const w = wheel((left ? 1 : -1) * geo.odoTrack / 2, ODO_W, ODO_D), dir = screenSide(left, view);
    return { name: left ? 'L' : 'D', left, ...w,
      text: { x: w.x + dir * ODO_W / 2 * k, y: Z(Math.max(geo.wheelD, ODO_D)) - 4, align: dir > 0 ? 'right' : 'left' } };
  });
  const front = view === 'spreda', gap = m.r + 5;
  const lamps = sensors.filter(q => q.front === front).map(q => {
    const dir = screenSide(q.left, view), x = X((q.left ? 1 : -1) * geo.w / 2) + dir * gap;
    return { name: q.name, bit: q.bit, upper: q.upper, left: q.left, x, y: Z(q.upper ? geo.irHigh : geo.irLow), r: m.r,
      label: { x: x + dir * (m.r + 5), align: dir > 0 ? 'left' : 'right' } };
  });
  return { k, cx, gy, X, Z, body, lidar, drive, odo, lamps, font: m.font,
    title: front ? ['SPREDA', '(stojiš ispred robota)'] : ['POZADI', '(stojiš iza robota)'],
    sides: front ? { left: 'desno r.', right: 'levo r.' } : { left: 'levo r.', right: 'desno r.' } };
}

const LAMP = { on: '#3ecf8e', off: '#20262e', edge: '#556070', txtOn: '#07121f', txtOff: '#97a3b3' };

export function lamp(g, x, y, r, on, txt) {
  g.save();
  g.beginPath(); g.arc(x, y, r, 0, 2 * Math.PI);
  g.fillStyle = on ? LAMP.on : LAMP.off; g.fill();
  if (on) { g.shadowColor = LAMP.on; g.shadowBlur = 12; g.fill(); g.shadowBlur = 0; }
  else { g.setLineDash(on == null ? [3, 3] : []); g.strokeStyle = LAMP.edge; g.lineWidth = 1; g.stroke(); g.setLineDash([]); }
  if (txt) {
    g.fillStyle = on ? LAMP.txtOn : LAMP.txtOff; g.font = `bold ${Math.max(8, Math.round(r))}px system-ui, sans-serif`;
    g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(txt, x, y + 0.5);
  }
  g.restore();
}
