// Testovi za web/core/log.js: koji redovi dnevnika se prikazuju (ESP↔STM32, „samo greške“) i broj grešaka.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildRun } from '../../web/core/run.js';
import { isErrorLine, logLines, errorCount } from '../../web/core/log.js';

const LOG = [
  { t: 0, cls: '', text: 'start' },
  { t: 10, cls: 'proto', proto: true, text: 'ESP→STM GOTO #1' },
  { t: 20, cls: 'err', text: 'GRESKA: korak 2' },
  { t: 30, cls: 'sim', text: '[sim] sudar' },
  { t: 40, cls: 'err', text: 'PREKID: STOP' },
];
const texts = l => l.map(e => e.text);

test('isErrorLine: samo klasa err (kao ⚠ na traci); [sim] i proto nisu greške', () => {
  assert.equal(isErrorLine(LOG[2]), true);
  assert.equal(isErrorLine({ cls: 'sim err' }), true);
  assert.equal(isErrorLine(LOG[3]), false);
  assert.equal(isErrorLine(LOG[1]), false);
  assert.equal(isErrorLine({ text: 'x' }), false);
  assert.equal(isErrorLine(null), false);
});

test('logLines: bez ESP↔STM32 podrazumevano, sa njima kad je uključeno', () => {
  assert.deepEqual(texts(logLines(LOG)), ['start', 'GRESKA: korak 2', '[sim] sudar', 'PREKID: STOP']);
  assert.deepEqual(texts(logLines(LOG, { proto: true })), texts(LOG));
});

test('logLines: „samo greške“ ostavlja samo redove grešaka, i uz ESP↔STM32; redosled i objekti isti', () => {
  const only = logLines(LOG, { errorsOnly: true });
  assert.deepEqual(texts(only), ['GRESKA: korak 2', 'PREKID: STOP']);
  assert.equal(only[0], LOG[2]);
  assert.deepEqual(texts(logLines(LOG, { proto: true, errorsOnly: true })), ['GRESKA: korak 2', 'PREKID: STOP']);
  assert.deepEqual(logLines([], { errorsOnly: true }), []);
  assert.deepEqual(logLines(undefined), []);
});

test('errorCount: broj redova grešaka; isto što broji traka (klasa err) u celom snimku', () => {
  assert.equal(errorCount(LOG), 2);
  assert.equal(errorCount([]), 0);
  assert.equal(errorCount(null), 0);
  const run = buildRun(JSON.parse(readFileSync(new URL('./fixtures/run_sve_komande.json', import.meta.url), 'utf8')));
  assert.equal(errorCount(run.log), run.log.filter(e => e.cls === 'err').length);
  assert.equal(logLines(run.log, { proto: true, errorsOnly: true }).length, errorCount(run.log));
});
