/**
 * MonacoEditor - Standard Code Editor
 *
 * Wrapper around @monaco-editor/react with Pulse theme and configuration.
 */

import { useCallback, useRef, useEffect } from 'react';
import Editor, { OnMount, OnChange } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useEditorStore } from '@/stores/editorStore';
import { pulseMonacoTheme } from '@/services/monaco-config';

interface MonacoEditorProps {
  filePath: string;
}

export function MonacoEditor({ filePath }: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const { files, updateFileContent, saveFile, getScrollPosition, setScrollPosition } =
    useEditorStore();

  const file = files.get(filePath);

  // Handle editor mount
  const handleEditorMount: OnMount = useCallback(
    (editor, monaco) => {
      editorRef.current = editor;

      // Define Pulse theme
      monaco.editor.defineTheme('pulse-dark', pulseMonacoTheme);
      monaco.editor.setTheme('pulse-dark');

      // Restore scroll position
      const scrollPos = getScrollPosition(filePath);
      if (scrollPos) {
        editor.setScrollTop(scrollPos.top);
        editor.setScrollLeft(scrollPos.left);
      }

      // Add save command
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        saveFile(filePath);
      });

      // Focus editor
      editor.focus();
    },
    [filePath, getScrollPosition, saveFile]
  );

  // Handle content changes
  const handleChange: OnChange = useCallback(
    (value) => {
      if (value !== undefined) {
        updateFileContent(filePath, value);
      }
    },
    [filePath, updateFileContent]
  );

  // Save scroll position on unmount
  useEffect(() => {
    return () => {
      if (editorRef.current) {
        setScrollPosition(
          filePath,
          editorRef.current.getScrollTop(),
          editorRef.current.getScrollLeft()
        );
      }
    };
  }, [filePath, setScrollPosition]);

  if (!file) {
    return (
      <div className="h-full flex items-center justify-center text-pulse-fg-muted">
        File not found
      </div>
    );
  }

  return (
    <Editor
      height="100%"
      language={file.language}
      value={file.content}
      theme="pulse-dark"
      onChange={handleChange}
      onMount={handleEditorMount}
      options={{
        fontSize: 14,
        fontFamily: "'Cascadia Code', Consolas, 'Courier New', monospace",
        fontLigatures: true,
        // Line numbers configuration
        lineNumbers: 'on',
        lineNumbersMinChars: 3, // Minimum characters for line number column (reduces width)
        lineDecorationsWidth: 10, // Width for decorations like breakpoints
        glyphMarginWidth: 5, // Glyph margin width
        folding: true,
        foldingHighlight: true,
        // Minimap
        minimap: { enabled: true, scale: 1 },
        // Scrolling
        scrollBeyondLastLine: false,
        smoothScrolling: true,
        // Cursor
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: 'on',
        // Rendering
        renderWhitespace: 'selection',
        bracketPairColorization: { enabled: true },
        automaticLayout: true,
        wordWrap: 'off',
        tabSize: 4,
        insertSpaces: true,
        padding: { top: 8, bottom: 8 },
        // Scrollbar
        scrollbar: {
          verticalScrollbarSize: 10,
          horizontalScrollbarSize: 10,
        },
        // Ensure proper rendering
        fixedOverflowWidgets: true,
        renderLineHighlight: 'all',
        renderLineHighlightOnlyWhenFocus: false,
      }}
      loading={<EditorLoading />}
    />
  );
}

// ============================================================================
// Loading State
// ============================================================================

function EditorLoading() {
  return (
    <div className="h-full flex items-center justify-center bg-pulse-bg">
      <div className="flex items-center space-x-2 text-pulse-fg-muted">
        <LoadingSpinner />
        <span>Loading editor...</span>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
