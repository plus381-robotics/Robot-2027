// Sve što editor (web/editor.js) koristi iz CodeMirror 6, u jednom fajlu.
export { EditorView, basicSetup } from 'codemirror';
export { EditorState, StateField, StateEffect, RangeSetBuilder } from '@codemirror/state';
export { keymap, Decoration, hoverTooltip, gutter, GutterMarker, ViewPlugin } from '@codemirror/view';
export { python, pythonLanguage } from '@codemirror/lang-python';
export { autocompletion, completeFromList, snippetCompletion } from '@codemirror/autocomplete';
export { setDiagnostics, lintGutter } from '@codemirror/lint';
export { indentUnit, syntaxTree } from '@codemirror/language';
export { oneDark } from '@codemirror/theme-one-dark';
