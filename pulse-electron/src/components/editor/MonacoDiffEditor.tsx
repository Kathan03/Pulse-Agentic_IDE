/**
 * MonacoDiffEditor - Side-by-Side Diff View
 *
 * Shows original vs modified content for patch approval.
 */

import { useCallback, useRef } from 'react';
import { DiffEditor, DiffOnMount } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { pulseMonacoTheme } from '@/services/monaco-config';
import { getLanguageFromPath } from '@/types/editor';

interface MonacoDiffEditorProps {
  filePath: string;
  originalContent: string;
  modifiedContent: string;
}

export function MonacoDiffEditor({
  filePath,
  originalContent,
  modifiedContent,
}: MonacoDiffEditorProps) {
  const editorRef = useRef<editor.IStandaloneDiffEditor | null>(null);
  const language = getLanguageFromPath(filePath);

  // Handle editor mount
  const handleEditorMount: DiffOnMount = useCallback((editor, monaco) => {
    editorRef.current = editor;

    // Define Pulse theme
    monaco.editor.defineTheme('pulse-dark', pulseMonacoTheme);
    monaco.editor.setTheme('pulse-dark');

    // Focus editor
    editor.focus();
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <DiffHeader filePath={filePath} />

      {/* Diff Editor */}
      <div className="flex-1">
        <DiffEditor
          height="100%"
          language={language}
          original={originalContent}
          modified={modifiedContent}
          theme="pulse-dark"
          onMount={handleEditorMount}
          options={{
            fontSize: 14,
            fontFamily: "'Cascadia Code', Consolas, 'Courier New', monospace",
            fontLigatures: true,
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            smoothScrolling: true,
            automaticLayout: true,
            padding: { top: 8 },
            scrollbar: {
              verticalScrollbarSize: 10,
              horizontalScrollbarSize: 10,
            },
            // Diff-specific options
            enableSplitViewResizing: true,
            renderIndicators: true,
            renderMarginRevertIcon: false,
          }}
          loading={<DiffLoading />}
        />
      </div>
    </div>
  );
}

// ============================================================================
// Header
// ============================================================================

function DiffHeader({ filePath }: { filePath: string }) {
  const fileName = filePath.split(/[\\/]/).pop() || filePath;

  return (
    <div className="h-8 bg-pulse-bg-tertiary border-b border-pulse-border flex items-center px-4">
      <div className="flex items-center space-x-4 text-xs">
        <div className="flex items-center text-pulse-error">
          <MinusIcon />
          <span className="ml-1">Original</span>
        </div>
        <div className="flex items-center text-pulse-success">
          <PlusIcon />
          <span className="ml-1">Modified</span>
        </div>
        <span className="text-pulse-fg-muted">|</span>
        <span className="text-pulse-fg">{fileName}</span>
      </div>
    </div>
  );
}

// ============================================================================
// Loading State
// ============================================================================

function DiffLoading() {
  return (
    <div className="h-full flex items-center justify-center bg-pulse-bg">
      <div className="flex items-center space-x-2 text-pulse-fg-muted">
        <LoadingSpinner />
        <span>Loading diff view...</span>
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

// ============================================================================
// Icons
// ============================================================================

function MinusIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3">
      <rect x="3" y="7" width="10" height="2" rx="1" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3">
      <path d="M7 3v4H3v2h4v4h2V9h4V7H9V3H7z" />
    </svg>
  );
}
