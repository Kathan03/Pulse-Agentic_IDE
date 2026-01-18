/**
 * useMenuActions Hook
 *
 * Handles menu actions from the Electron main process.
 * Routes actions to appropriate handlers in the React app.
 */

import { useEffect } from 'react';
import { useEditorStore } from '@/stores/editorStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { useUIStore } from '@/stores/uiStore';

export function useMenuActions(): void {
  const { openFile, saveFile, activeFilePath } = useEditorStore();
  const { openWorkspace } = useWorkspaceStore();
  const { toggleSidebar, toggleAgentPanel, toggleTerminal } = useUIStore();

  useEffect(() => {
    // Helper functions
    function handleNewFile(): void {
      // Create a new untitled file
      const untitledPath = `untitled-${Date.now()}`;
      openFile(untitledPath, '');
    }

    function handleSave(): void {
      if (activeFilePath) {
        saveFile(activeFilePath);
      }
    }
    // Handle menu actions from main process
    const unsubscribeAction = window.pulseAPI.menu.onAction((action) => {
      console.log('[Menu] Action received:', action);

      switch (action) {
        case 'new-file':
          handleNewFile();
          break;
        case 'save':
          handleSave();
          break;
        case 'toggle-sidebar':
          toggleSidebar();
          break;
        case 'toggle-agent-panel':
          toggleAgentPanel();
          break;
        case 'toggle-terminal':
          toggleTerminal();
          break;
        case 'settings':
          // Open settings as an editor tab (not activity bar item)
          openFile('__settings__', '');
          break;
        case 'find':
          // Trigger find dialog in Monaco editor
          // TODO: Send command to Monaco
          break;
        default:
          console.log('[Menu] Unhandled action:', action);
      }
    });

    // Handle file opened from menu
    const unsubscribeFile = window.pulseAPI.menu.onFileOpened(async (filePath) => {
      console.log('[Menu] File opened:', filePath);
      try {
        const content = await window.pulseAPI.fs.readFile(filePath);
        openFile(filePath, content);
      } catch (error) {
        console.error('[Menu] Failed to open file:', error);
      }
    });

    // Handle folder opened from menu
    const unsubscribeFolder = window.pulseAPI.menu.onFolderOpened((folderPath) => {
      console.log('[Menu] Folder opened:', folderPath);
      openWorkspace(folderPath);
    });

    return () => {
      unsubscribeAction();
      unsubscribeFile();
      unsubscribeFolder();
    };
  }, [openFile, openWorkspace, toggleSidebar, toggleAgentPanel, toggleTerminal]);


}
