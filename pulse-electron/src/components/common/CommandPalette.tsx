/**
 * CommandPalette - VS Code-style Command Palette
 *
 * Provides quick access to all commands via fuzzy search.
 * Triggered by Ctrl+Shift+P or F1.
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { useEditorStore } from '@/stores/editorStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';

// ============================================================================
// Command Interface
// ============================================================================

interface Command {
  id: string;
  label: string;
  shortcut?: string;
  category: 'File' | 'Edit' | 'View' | 'Agent' | 'Search' | 'Terminal';
  handler: () => void | Promise<void>;
}

// ============================================================================
// Command Registry
// ============================================================================

function useCommands(): Command[] {
  const { toggleSidebar, toggleAgentPanel, toggleTerminal, setTheme, theme } = useUIStore();
  const { activeFilePath, saveFile, closeFile } = useEditorStore();
  const { openWorkspace, refreshTree } = useWorkspaceStore();

  return useMemo(() => [
    // File commands
    {
      id: 'file.openFolder',
      label: 'Open Folder',
      shortcut: 'Ctrl+K',
      category: 'File',
      handler: async () => {
        const path = await window.pulseAPI.workspace.openFolder();
        if (path) openWorkspace(path);
      },
    },
    {
      id: 'file.openFile',
      label: 'Open File',
      shortcut: 'Ctrl+O',
      category: 'File',
      handler: async () => {
        const path = await window.pulseAPI.workspace.openFile();
        if (path) {
          const content = await window.pulseAPI.fs.readFile(path);
          useEditorStore.getState().openFile(path, content, { isPreview: false });
        }
      },
    },
    {
      id: 'file.save',
      label: 'Save',
      shortcut: 'Ctrl+S',
      category: 'File',
      handler: () => {
        if (activeFilePath) saveFile(activeFilePath);
      },
    },
    {
      id: 'file.close',
      label: 'Close Editor',
      shortcut: 'Ctrl+W',
      category: 'File',
      handler: () => {
        if (activeFilePath) closeFile(activeFilePath);
      },
    },
    {
      id: 'file.refresh',
      label: 'Refresh Explorer',
      category: 'File',
      handler: () => refreshTree(),
    },

    // View commands
    {
      id: 'view.toggleSidebar',
      label: 'Toggle Sidebar',
      shortcut: 'Ctrl+B',
      category: 'View',
      handler: toggleSidebar,
    },
    {
      id: 'view.toggleAgentPanel',
      label: 'Toggle Agent Panel',
      shortcut: 'Ctrl+Shift+A',
      category: 'View',
      handler: toggleAgentPanel,
    },
    {
      id: 'view.toggleTerminal',
      label: 'Toggle Terminal',
      shortcut: 'Ctrl+`',
      category: 'View',
      handler: toggleTerminal,
    },
    {
      id: 'view.toggleTheme',
      label: theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme',
      category: 'View',
      handler: () => setTheme(theme === 'dark' ? 'light' : 'dark'),
    },

    // Agent commands
    {
      id: 'agent.focus',
      label: 'Focus Agent Input',
      shortcut: 'Ctrl+J',
      category: 'Agent',
      handler: () => {
        toggleAgentPanel();
        // Focus will be handled by the agent input component
      },
    },

    // Terminal commands
    {
      id: 'terminal.new',
      label: 'New Terminal',
      category: 'Terminal',
      handler: toggleTerminal,
    },
  ], [toggleSidebar, toggleAgentPanel, toggleTerminal, setTheme, theme, activeFilePath, saveFile, closeFile, openWorkspace, refreshTree]);
}

// ============================================================================
// Fuzzy Search
// ============================================================================

function fuzzyMatch(query: string, text: string): { match: boolean; score: number } {
  const queryLower = query.toLowerCase();
  const textLower = text.toLowerCase();

  if (queryLower.length === 0) return { match: true, score: 0 };

  // Check if query is a substring (highest score)
  if (textLower.includes(queryLower)) {
    return { match: true, score: 100 - textLower.indexOf(queryLower) };
  }

  // Fuzzy character matching
  let queryIndex = 0;
  let score = 0;

  for (let i = 0; i < textLower.length && queryIndex < queryLower.length; i++) {
    if (textLower[i] === queryLower[queryIndex]) {
      queryIndex++;
      score += 1;
    }
  }

  return {
    match: queryIndex === queryLower.length,
    score: score,
  };
}

// ============================================================================
// Command Palette Component
// ============================================================================

export function CommandPalette() {
  const { commandPaletteVisible, hideCommandPalette } = useUIStore();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const commands = useCommands();

  // Filter and sort commands based on query
  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands;

    return commands
      .map((cmd) => ({
        cmd,
        ...fuzzyMatch(query, `${cmd.category}: ${cmd.label}`),
      }))
      .filter((item) => item.match)
      .sort((a, b) => b.score - a.score)
      .map((item) => item.cmd);
  }, [commands, query]);

  // Reset state when palette opens
  useEffect(() => {
    if (commandPaletteVisible) {
      setQuery('');
      setSelectedIndex(0);
      inputRef.current?.focus();
    }
  }, [commandPaletteVisible]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            executeCommand(filteredCommands[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          hideCommandPalette();
          break;
      }
    },
    [filteredCommands, selectedIndex, hideCommandPalette]
  );

  // Execute command and close palette
  const executeCommand = useCallback(
    (command: Command) => {
      hideCommandPalette();
      command.handler();
    },
    [hideCommandPalette]
  );

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selectedElement = listRef.current.children[selectedIndex] as HTMLElement;
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  if (!commandPaletteVisible) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/50"
      onClick={hideCommandPalette}
    >
      <div
        className="w-[600px] max-w-[90vw] bg-pulse-bg-secondary border border-pulse-border rounded-lg shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="p-2 border-b border-pulse-border">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command..."
            className="w-full px-3 py-2 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
          />
        </div>

        {/* Command List */}
        <div ref={listRef} className="max-h-80 overflow-y-auto">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-8 text-center text-pulse-fg-muted text-sm">
              No commands found
            </div>
          ) : (
            filteredCommands.map((command, index) => (
              <CommandItem
                key={command.id}
                command={command}
                isSelected={index === selectedIndex}
                onClick={() => executeCommand(command)}
                onMouseEnter={() => setSelectedIndex(index)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Command Item
// ============================================================================

interface CommandItemProps {
  command: Command;
  isSelected: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
}

function CommandItem({ command, isSelected, onClick, onMouseEnter }: CommandItemProps) {
  return (
    <button
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      className={`w-full px-4 py-2 flex items-center justify-between text-left transition-colors ${
        isSelected ? 'bg-pulse-selection' : 'hover:bg-pulse-bg-tertiary'
      }`}
    >
      <div className="flex items-center gap-3">
        <span className="text-xs text-pulse-fg-muted w-16">{command.category}</span>
        <span className="text-sm text-pulse-fg">{command.label}</span>
      </div>
      {command.shortcut && (
        <kbd className="px-2 py-0.5 bg-pulse-bg rounded border border-pulse-border text-xs text-pulse-fg-muted">
          {command.shortcut}
        </kbd>
      )}
    </button>
  );
}

export default CommandPalette;
