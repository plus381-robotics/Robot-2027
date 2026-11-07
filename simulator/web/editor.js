// Tactic editor (CodeMirror 6): Python highlighting, completion and hover help for the tac API (generated
// from ESP32/lib/tac.py by the server), live checks (syntax, MicroPython, names, tac arguments...),
// problems list, and highlighting of the line that is running at the current playback time.
import {
  EditorView, basicSetup, EditorState, StateField, StateEffect, keymap, Decoration, hoverTooltip,
  python, autocompletion, snippetCompletion, setDiagnostics, lintGutter, indentUnit, oneDark,
} from './vendor/codemirror.bundle.js';

const setMarks = StateEffect.define();
const marksField = StateField.define({
  create: () => Decoration.none,
  update(deco, tr) {
    deco = deco.map(tr.changes);
    for (const e of tr.effects) if (e.is(setMarks)) deco = e.value;
    return deco;
  },
  provide: f => EditorView.decorations.from(f),
});

function escapeHtml(s) { return s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]); }

export class TacticEditor {
  constructor(root, opts) {
    this.root = root;
    this.opts = opts;                    // {api, onChange(text), onRun(), onSave(), onStepLine(line)}
    this.api = opts.api;
    this.diags = [];
    const self = this;
    const funcs = this.api.funcs;

    const completion = ctx => {
      const line = ctx.state.doc.lineAt(ctx.pos);
      const before = line.text.slice(0, ctx.pos - line.from);
      // actuator("...  -> actuator names
      const am = /actuator\(\s*["']([\w]*)$/.exec(before);
      if (am) {
        return { from: ctx.pos - am[1].length, options: this.api.actuators.map(a => ({ label: a, type: 'constant', detail: 'config.ACTUATORS' })) };
      }
      const w = ctx.matchBefore(/\w*/);
      if (!w || (w.from === w.to && !ctx.explicit)) return null;
      const opts = [];
      // keyword arguments of the call we are in
      const cm = /(\w+)\(([^()]*)$/.exec(before);
      if (cm && funcs[cm[1]]) {
        for (const [p, d] of funcs[cm[1]].params) {
          if (d !== null) opts.push({ label: p + '=', type: 'property', detail: `default ${d}`, boost: 10 });
        }
      }
      for (const [name, f] of Object.entries(funcs)) {
        const req = f.params.filter(([, d]) => d === null).map(([p]) => p);
        const info = () => { const el = document.createElement('div'); el.className = 'cm-api-info';
          el.innerHTML = `<b>${escapeHtml(f.sig)}</b><pre>${escapeHtml(f.doc || '')}</pre>`; return el; };
        if (f.kind === 'function') {
          opts.push(snippetCompletion(`${name}(${req.map(p => '${' + p + '}').join(', ')})`,
            { label: name, type: 'function', detail: f.sig.slice(name.length), info, boost: 5 }));
        } else {
          opts.push({ label: name, type: 'class', info });
        }
      }
      for (const k of ['START', 'TOTAL']) opts.push({ label: k, type: 'variable', detail: k === 'START' ? '= (x, y, angle)' : '= steps' });
      return { from: w.from, options: opts, validFor: /^\w*$/ };
    };

    const hover = hoverTooltip((view, pos) => {
      const { from, to, text } = view.state.doc.lineAt(pos);
      let s = pos, e = pos;
      while (s > from && /\w/.test(text[s - from - 1])) s--;
      while (e < to && /\w/.test(text[e - from])) e++;
      const word = text.slice(s - from, e - from);
      const f = funcs[word];
      if (!f) return null;
      return { pos: s, end: e, above: true, create() {
        const dom = document.createElement('div'); dom.className = 'cm-api-info';
        dom.innerHTML = `<b>${escapeHtml(f.sig)}</b><pre>${escapeHtml(f.doc || '')}</pre>`; return { dom };
      } };
    });

    let timer = null;
    const changed = EditorView.updateListener.of(u => {
      if (!u.docChanged || this.silent) return;
      clearTimeout(timer);
      timer = setTimeout(() => self.opts.onChange(self.text()), 600);
    });

    this.view = new EditorView({
      parent: root,
      state: EditorState.create({
        doc: '',
        extensions: [
          basicSetup, python(), oneDark, indentUnit.of('    '), EditorState.tabSize.of(4), lintGutter(),
          autocompletion({ override: [completion], icons: true }), hover, marksField, changed,
          keymap.of([
            { key: 'Mod-s', preventDefault: true, run: () => { self.opts.onSave(); return true; } },
            { key: 'Mod-Enter', preventDefault: true, run: () => { self.opts.onRun(); return true; } },
          ]),
          EditorView.theme({ '&': { height: '100%', fontSize: '13px' }, '.cm-scroller': { fontFamily: 'ui-monospace, "JetBrains Mono", Consolas, monospace' } }),
        ],
      }),
    });
  }

  text() { return this.view.state.doc.toString(); }

  setText(t) {
    this.silent = true;
    this.view.dispatch({ changes: { from: 0, to: this.view.state.doc.length, insert: t } });
    this.silent = false;
    this.setMarks({});
  }

  setDiagnostics(list) {
    this.diags = list;
    const doc = this.view.state.doc;
    const out = [];
    for (const d of list) {
      const ln = Math.min(Math.max(1, d.line), doc.lines);
      const line = doc.line(ln);
      let from = line.from + Math.min(d.col || 0, line.length);
      let to = line.to;
      if (d.end_line && d.end_line <= doc.lines && d.end_col != null) {
        to = Math.max(from, doc.line(d.end_line).from + d.end_col);
      }
      if (to <= from) { from = line.from; to = line.to; }
      out.push({ from, to, severity: d.severity === 'info' ? 'info' : d.severity, message: d.msg, source: d.source });
    }
    this.view.dispatch(setDiagnostics(this.view.state, out));
  }

  // marks: {cur: line, ok: [lines], fail: [lines], err: [lines]}
  setMarks(m) {
    const doc = this.view.state.doc;
    const ranges = [];
    const add = (ln, cls) => { if (ln >= 1 && ln <= doc.lines) ranges.push(Decoration.line({ class: cls }).range(doc.line(ln).from)); };
    for (const l of m.fail || []) add(l, 'cm-step-fail');
    for (const l of m.err || []) add(l, 'cm-step-err');
    if (m.cur) add(m.cur, 'cm-step-cur');
    ranges.sort((a, b) => a.from - b.from);
    this.view.dispatch({ effects: setMarks.of(Decoration.set(ranges, true)) });
    if (m.cur && m.scroll) this.reveal(m.cur, false);
  }

  reveal(line, focus = true) {
    const doc = this.view.state.doc;
    if (line < 1 || line > doc.lines) return;
    const l = doc.line(line);
    this.view.dispatch({ selection: focus ? { anchor: l.from } : undefined, effects: EditorView.scrollIntoView(l.from, { y: 'center' }) });
    if (focus) this.view.focus();
  }
}
