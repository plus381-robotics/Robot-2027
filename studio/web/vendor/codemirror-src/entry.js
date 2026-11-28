// Sve što editor (web/editor.js) koristi iz CodeMirror 6, u jednom fajlu.
export { EditorView, basicSetup } from 'codemirror';
export { EditorState, StateField, StateEffect, RangeSetBuilder, Prec } from '@codemirror/state';
export { keymap, Decoration, hoverTooltip, gutter, GutterMarker, ViewPlugin, WidgetType } from '@codemirror/view';
export { python, pythonLanguage } from '@codemirror/lang-python';
export { autocompletion, completeFromList, snippetCompletion, acceptCompletion, completionStatus, startCompletion,
  nextSnippetField, hasNextSnippetField } from '@codemirror/autocomplete';
export { setDiagnostics, lintGutter } from '@codemirror/lint';
export { indentUnit, syntaxTree } from '@codemirror/language';
export { indentMore, indentLess } from '@codemirror/commands';
export { oneDark } from '@codemirror/theme-one-dark';
