/**
 * useKeyboardShortcuts Hook
 *
 * Global keyboard shortcut handler for the IDE.
 */

import { useEffect, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { useEditorStore } from '@/stores/editorStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';

export function useKeyboardShortcuts() {
  const { toggleSidebar, toggleAgentPanel, toggleTerminal } = useUIStore();
  const { activeFilePath, saveFile, closeFile } = useEditorStore();
  const { openWorkspace } = useWorkspaceStore();

  const handleKeyDown = useCallback(
    async (e: KeyboardEvent) => {
      const isMod = e.ctrlKey || e.metaKey;
      const isShift = e.shiftKey;

      // Ctrl+S - Save file
      if (isMod && e.key === 's' && !isShift) {
        e.preventDefault();
        if (activeFilePath) {
          saveFile(activeFilePath);
        }
        return;
      }

      // Ctrl+Shift+S - Save all (not implemented)
      if (isMod && e.key === 's' && isShift) {
        e.preventDefault();
        // TODO: Save all dirty files
        return;
      }

      // Ctrl+W - Close active tab
      if (isMod && e.key === 'w' && !isShift) {
        e.preventDefault();
        if (activeFilePath) {
          closeFile(activeFilePath);
        }
        return;
      }

      // Ctrl+B - Toggle sidebar
      if (isMod && e.key === 'b' && !isShift) {
        e.preventDefault();
        toggleSidebar();
        return;
      }

      // Ctrl+J - Toggle agent panel
      if (isMod && e.key === 'j' && !isShift) {
        e.preventDefault();
        toggleAgentPanel();
        return;
      }

      // Ctrl+Shift+A - Toggle agent panel (alternative)
      if (isMod && e.key.toLowerCase() === 'a' && isShift) {
        e.preventDefault();
        toggleAgentPanel();
        return;
      }

      // Ctrl+Shift+P - Command palette
      if (isMod && e.key.toLowerCase() === 'p' && isShift) {
        e.preventDefault();
        useUIStore.getState().showCommandPalette();
        return;
      }

      // Ctrl+K - Open folder (simplified from Ctrl+K Ctrl+O)
      if (isMod && e.key === 'k' && !isShift) {
        e.preventDefault();
        const path = await window.pulseAPI.workspace.openFolder();
        if (path) {
          openWorkspace(path);
        }
        return;
      }

      // Ctrl+O - Open file (permanent tab since user explicitly opened)
      if (isMod && e.key === 'o' && !isShift) {
        e.preventDefault();
        const path = await window.pulseAPI.workspace.openFile();
        if (path) {
          try {
            const content = await window.pulseAPI.fs.readFile(path);
            useEditorStore.getState().openFile(path, content, { isPreview: false });
          } catch (error) {
            console.error('Failed to open file:', error);
          }
        }
        return;
      }

      // Ctrl+` - Toggle terminal
      if (isMod && e.key === '`') {
        e.preventDefault();
        toggleTerminal();
        return;
      }

      // F1 - Command palette
      if (e.key === 'F1') {
        e.preventDefault();
        useUIStore.getState().showCommandPalette();
        return;
      }

      // Delete - Delete selected file/folder
      if (e.key === 'Delete' && !isMod && !isShift) {
        const { selectedPath } = useWorkspaceStore.getState();
        if (selectedPath) {
          e.preventDefault();
          // Show confirmation before deleting
          const fileName = selectedPath.split(/[\\/]/).pop() || selectedPath;
          if (confirm(`Are you sure you want to delete "${fileName}"?`)) {
            window.pulseAPI.fs.remove(selectedPath)
              .then(() => {
                useWorkspaceStore.getState().refreshTree();
                // Close file if it was open
                if (useEditorStore.getState().files.has(selectedPath)) {
                  useEditorStore.getState().closeFile(selectedPath);
                }
              })
              .catch((error: Error) => {
                console.error('Failed to delete:', error);
                alert(`Failed to delete: ${error.message}`);
              });
          }
        }
        return;
      }
    },
    [activeFilePath, saveFile, closeFile, toggleSidebar, toggleAgentPanel, toggleTerminal, openWorkspace]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
