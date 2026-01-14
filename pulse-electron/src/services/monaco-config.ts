/**
 * Monaco Editor Configuration
 *
 * Theme definition and language configurations for Monaco editor.
 */

import type { editor } from 'monaco-editor';

/**
 * Pulse Dark Theme for Monaco Editor
 *
 * Based on VS Code Dark+ theme with Pulse accent colors.
 */
export const pulseMonacoTheme: editor.IStandaloneThemeData = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    // Comments
    { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },

    // Keywords
    { token: 'keyword', foreground: '569CD6' },
    { token: 'keyword.control', foreground: 'C586C0' },

    // Types
    { token: 'type', foreground: '4EC9B0' },
    { token: 'type.identifier', foreground: '4EC9B0' },

    // Strings
    { token: 'string', foreground: 'CE9178' },
    { token: 'string.escape', foreground: 'D7BA7D' },

    // Numbers
    { token: 'number', foreground: 'B5CEA8' },

    // Operators
    { token: 'operator', foreground: 'D4D4D4' },

    // Variables
    { token: 'variable', foreground: '9CDCFE' },
    { token: 'variable.predefined', foreground: '4FC1FF' },

    // Functions
    { token: 'function', foreground: 'DCDCAA' },

    // Constants
    { token: 'constant', foreground: '4FC1FF' },

    // Tags (HTML/XML)
    { token: 'tag', foreground: '569CD6' },
    { token: 'attribute.name', foreground: '9CDCFE' },
    { token: 'attribute.value', foreground: 'CE9178' },

    // Structured Text specific
    { token: 'keyword.st', foreground: '569CD6' },
    { token: 'type.st', foreground: '4EC9B0' },
    { token: 'function.st', foreground: 'DCDCAA' },
  ],
  colors: {
    // Editor
    'editor.background': '#1E1E1E',
    'editor.foreground': '#D4D4D4',
    'editor.lineHighlightBackground': '#282828',
    'editor.selectionBackground': '#264F78',
    'editor.inactiveSelectionBackground': '#3A3D41',

    // Gutter
    'editorLineNumber.foreground': '#858585',
    'editorLineNumber.activeForeground': '#C6C6C6',
    'editorGutter.background': '#1E1E1E',

    // Cursor
    'editorCursor.foreground': '#AEAFAD',

    // Whitespace
    'editorWhitespace.foreground': '#3B3B3B',

    // Indent guides
    'editorIndentGuide.background': '#404040',
    'editorIndentGuide.activeBackground': '#707070',

    // Minimap
    'minimap.background': '#1E1E1E',

    // Scrollbar
    'scrollbarSlider.background': '#79797966',
    'scrollbarSlider.hoverBackground': '#79797999',
    'scrollbarSlider.activeBackground': '#BFBFBF66',

    // Widget (autocomplete, hover)
    'editorWidget.background': '#252526',
    'editorWidget.border': '#454545',

    // Diff editor
    'diffEditor.insertedTextBackground': '#89D18533',
    'diffEditor.removedTextBackground': '#F4877133',
    'diffEditor.insertedLineBackground': '#89D18522',
    'diffEditor.removedLineBackground': '#F4877122',
  },
};

/**
 * Register Structured Text language with Monaco.
 *
 * Call this during app initialization.
 */
export function registerStructuredTextLanguage(monaco: typeof import('monaco-editor')): void {
  // Register language
  monaco.languages.register({
    id: 'structured-text',
    extensions: ['.st', '.ST'],
    aliases: ['Structured Text', 'ST', 'IEC 61131-3'],
  });

  // Define token provider
  monaco.languages.setMonarchTokensProvider('structured-text', {
    defaultToken: '',
    ignoreCase: true,

    keywords: [
      'PROGRAM', 'END_PROGRAM',
      'FUNCTION', 'END_FUNCTION',
      'FUNCTION_BLOCK', 'END_FUNCTION_BLOCK',
      'VAR', 'VAR_INPUT', 'VAR_OUTPUT', 'VAR_IN_OUT', 'VAR_GLOBAL', 'VAR_EXTERNAL', 'END_VAR',
      'CONSTANT', 'RETAIN', 'NON_RETAIN',
      'IF', 'THEN', 'ELSIF', 'ELSE', 'END_IF',
      'CASE', 'OF', 'END_CASE',
      'FOR', 'TO', 'BY', 'DO', 'END_FOR',
      'WHILE', 'END_WHILE',
      'REPEAT', 'UNTIL', 'END_REPEAT',
      'RETURN', 'EXIT', 'CONTINUE',
      'AND', 'OR', 'XOR', 'NOT', 'MOD',
      'TRUE', 'FALSE',
    ],

    typeKeywords: [
      'BOOL', 'BYTE', 'WORD', 'DWORD', 'LWORD',
      'SINT', 'INT', 'DINT', 'LINT',
      'USINT', 'UINT', 'UDINT', 'ULINT',
      'REAL', 'LREAL',
      'TIME', 'DATE', 'TIME_OF_DAY', 'DATE_AND_TIME',
      'STRING', 'WSTRING',
      'ARRAY', 'STRUCT', 'END_STRUCT',
    ],

    operators: [
      ':=', '=', '<>', '<', '>', '<=', '>=',
      '+', '-', '*', '/', '**',
      '&', '(', ')', '[', ']', ',', ';', ':',
    ],

    tokenizer: {
      root: [
        // Comments
        [/\(\*/, 'comment', '@comment'],
        [/\/\/.*$/, 'comment'],

        // Strings
        [/'[^']*'/, 'string'],
        [/"[^"]*"/, 'string'],

        // Numbers
        [/\d+\.\d+/, 'number.float'],
        [/\d+/, 'number'],
        [/16#[0-9A-Fa-f]+/, 'number.hex'],
        [/2#[01]+/, 'number.binary'],

        // Keywords
        [
          /[a-zA-Z_]\w*/,
          {
            cases: {
              '@keywords': 'keyword',
              '@typeKeywords': 'type',
              '@default': 'identifier',
            },
          },
        ],

        // Operators
        [/:=/, 'operator'],
        [/[<>=!]+/, 'operator'],
        [/[+\-*\/]/, 'operator'],

        // Delimiters
        [/[;,.]/, 'delimiter'],
        [/[()[\]]/, '@brackets'],
      ],

      comment: [
        [/[^(*]+/, 'comment'],
        [/\*\)/, 'comment', '@pop'],
        [/[(*]/, 'comment'],
      ],
    },
  });

  // Language configuration
  monaco.languages.setLanguageConfiguration('structured-text', {
    comments: {
      lineComment: '//',
      blockComment: ['(*', '*)'],
    },
    brackets: [
      ['{', '}'],
      ['[', ']'],
      ['(', ')'],
    ],
    autoClosingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: "'", close: "'", notIn: ['string', 'comment'] },
      { open: '"', close: '"', notIn: ['string'] },
      { open: '(*', close: '*)' },
    ],
    surroundingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: "'", close: "'" },
      { open: '"', close: '"' },
    ],
    folding: {
      markers: {
        start: /^\s*(PROGRAM|FUNCTION|FUNCTION_BLOCK|IF|CASE|FOR|WHILE|REPEAT|VAR)/i,
        end: /^\s*(END_PROGRAM|END_FUNCTION|END_FUNCTION_BLOCK|END_IF|END_CASE|END_FOR|END_WHILE|END_REPEAT|END_VAR)/i,
      },
    },
    indentationRules: {
      increaseIndentPattern: /^\s*(PROGRAM|FUNCTION|FUNCTION_BLOCK|IF|ELSE|ELSIF|CASE|FOR|WHILE|REPEAT|VAR)/i,
      decreaseIndentPattern: /^\s*(END_PROGRAM|END_FUNCTION|END_FUNCTION_BLOCK|END_IF|END_CASE|END_FOR|END_WHILE|END_REPEAT|END_VAR|ELSE|ELSIF)/i,
    },
  });
}
