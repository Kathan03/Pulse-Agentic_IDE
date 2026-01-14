/**
 * EditorTabs - Tab Bar for Open Files
 *
 * Displays tabs for all open files with close buttons and dirty indicators.
 */

import { useCallback } from 'react';
import { useEditorStore } from '@/stores/editorStore';
import type { EditorTab } from '@/types/editor';

export function EditorTabs() {
  const { tabs, activeFilePath, setActiveFile, closeFile, promotePreviewTab } =
    useEditorStore();

  const handleTabClick = useCallback(
    (tab: EditorTab) => {
      setActiveFile(tab.path);
    },
    [setActiveFile]
  );

  const handleTabDoubleClick = useCallback(
    (tab: EditorTab) => {
      if (tab.isPreview) {
        promotePreviewTab(tab.path);
      }
    },
    [promotePreviewTab]
  );

  const handleCloseTab = useCallback(
    (e: React.MouseEvent, tab: EditorTab) => {
      e.stopPropagation();
      closeFile(tab.path);
    },
    [closeFile]
  );

  const handleMiddleClick = useCallback(
    (e: React.MouseEvent, tab: EditorTab) => {
      if (e.button === 1) {
        e.preventDefault();
        closeFile(tab.path);
      }
    },
    [closeFile]
  );

  if (tabs.length === 0) return null;

  return (
    <div className="h-9 bg-pulse-bg-secondary flex items-end border-b border-pulse-border overflow-x-auto scrollbar-thin">
      {tabs.map((tab) => (
        <Tab
          key={tab.path}
          tab={tab}
          isActive={tab.path === activeFilePath}
          onClick={() => handleTabClick(tab)}
          onDoubleClick={() => handleTabDoubleClick(tab)}
          onClose={(e) => handleCloseTab(e, tab)}
          onMouseDown={(e) => handleMiddleClick(e, tab)}
        />
      ))}
    </div>
  );
}

// ============================================================================
// Tab Component
// ============================================================================

interface TabProps {
  tab: EditorTab;
  isActive: boolean;
  onClick: () => void;
  onDoubleClick: () => void;
  onClose: (e: React.MouseEvent) => void;
  onMouseDown: (e: React.MouseEvent) => void;
}

function Tab({
  tab,
  isActive,
  onClick,
  onDoubleClick,
  onClose,
  onMouseDown,
}: TabProps) {
  // Special handling for settings tab
  const isSettings = tab.path === '__settings__';
  const displayName = isSettings ? 'Settings' : tab.name;

  return (
    <div
      className={`
        group relative flex items-center h-9 px-3 cursor-pointer
        border-r border-pulse-border min-w-0 max-w-48
        ${isActive ? 'bg-pulse-bg border-t-2 border-t-pulse-primary' : 'bg-pulse-bg-secondary hover:bg-pulse-bg-tertiary'}
        ${tab.isPreview ? 'italic' : ''}
      `}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      onMouseDown={onMouseDown}
    >
      {/* File Icon */}
      <div className="w-4 h-4 mr-2 flex-shrink-0">
        {isSettings ? <SettingsIcon /> : <FileIcon filename={tab.name} />}
      </div>

      {/* File Name */}
      <span className="text-sm truncate">
        {displayName}
      </span>

      {/* Dirty Indicator or Close Button */}
      <div className="ml-2 w-4 h-4 flex-shrink-0 flex items-center justify-center">
        {tab.isDirty ? (
          <DirtyIndicator />
        ) : (
          <CloseButton
            onClick={onClose}
            className="opacity-0 group-hover:opacity-100"
          />
        )}
      </div>

      {/* Active indicator line at bottom */}
      {isActive && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-pulse-bg" />
      )}
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function DirtyIndicator() {
  return (
    <div className="w-2 h-2 rounded-full bg-pulse-fg-muted" />
  );
}

function CloseButton({
  onClick,
  className,
}: {
  onClick: (e: React.MouseEvent) => void;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`p-0.5 rounded hover:bg-pulse-bg-tertiary transition-opacity ${className}`}
    >
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3">
        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" fill="none" />
      </svg>
    </button>
  );
}

function FileIcon({ filename }: { filename: string }) {
  const ext = filename.split('.').pop()?.toLowerCase() || '';

  let color = 'text-pulse-fg-muted';

  switch (ext) {
    case 'st':
      color = 'text-purple-400';
      break;
    case 'ts':
    case 'tsx':
      color = 'text-blue-400';
      break;
    case 'js':
    case 'jsx':
      color = 'text-yellow-400';
      break;
    case 'py':
      color = 'text-green-400';
      break;
    case 'json':
      color = 'text-yellow-300';
      break;
    case 'md':
      color = 'text-blue-300';
      break;
  }

  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className={`w-full h-full ${color}`}>
      <path d="M3 1h7l3 3v11a1 1 0 01-1 1H3a1 1 0 01-1-1V2a1 1 0 011-1zm7 0v3h3" />
    </svg>
  );
}

function SettingsIcon() {
  // Using Font Awesome gear icon (Issue 4)
  return (
    <i className="fa-solid fa-gear w-full h-full text-pulse-fg-muted flex items-center justify-center text-sm" />
  );
}
