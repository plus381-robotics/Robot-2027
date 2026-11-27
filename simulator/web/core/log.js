// Dnevnik bez DOM-a (da ga uveze i `node --test`): koji redovi se prikazuju i koliko je grešaka.
//   isErrorLine(e)                      red greške = red sa klasom `err` (core/run.js: GRESKA…, PREKID…), isto što
//                                       broji ⚠ n na traci; redovi [sim]/[buzzer] imaju klasu `sim` i nisu greške
//   logLines(log, {proto, errorsOnly})  redovi za prikaz: ESP↔STM32 (proto) samo ako je uključeno; „samo greške“
//   errorCount(log)                     broj redova grešaka u celom dnevniku (broj na kartici Dnevnik)

export const isErrorLine = e => !!e && String(e.cls || '').split(/\s+/).includes('err');

export function logLines(log, { proto = false, errorsOnly = false } = {}) {
  return (log || []).filter(e => (proto || !e.proto) && (!errorsOnly || isErrorLine(e)));
}

export function errorCount(log) {
  let n = 0;
  for (const e of log || []) if (isErrorLine(e)) n++;
  return n;
}
