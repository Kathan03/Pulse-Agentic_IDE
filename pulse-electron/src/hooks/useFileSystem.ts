/**
 * useFileSystem Hook
 *
 * Provides file system operations through the Electron IPC bridge.
 */

import { useCallback, useEffect } from 'react';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { useEditorStore } from '@/stores/editorStore';

export function useFileSystem() {
  const { projectRoot, refreshFileTree } = useWorkspaceStore();
  const { files, updateFileContent, openFile, closeFile } = useEditorStore();

  // Handle file changes from file watcher
  const handleFileChange = useCallback(
    async (event: string, path: string) => {
      console.log('File change:', event, path);

      switch (event) {
        case 'change': {
          // File modified externally - check if open in editor
          const file = files.get(path);
          if (file && !file.isDirty) {
            // Reload file content
            try {
              const content = await window.pulseAPI.fs.readFile(path);
              updateFileContent(path, content);
              // Mark as not dirty since it matches disk
              useEditorStore.getState().markFileSaved(path, content);
            } catch (error) {
              console.error('Failed to reload file:', error);
            }
          }
          break;
        }

        case 'unlink': {
          // File deleted - close if open
          if (files.has(path)) {
            closeFile(path);
          }
          refreshFileTree();
          break;
        }

        case 'add':
        case 'addDir':
        case 'unlinkDir': {
          // Refresh tree for structure changes
          refreshFileTree();
          break;
        }
      }
    },
    [files, updateFileContent, closeFile, refreshFileTree]
  );

  // Subscribe to file changes
  useEffect(() => {
    const unsubscribe = window.pulseAPI.fs.onFileChange(handleFileChange);
    return unsubscribe;
  }, [handleFileChange]);

  // File operations
  const readFile = useCallback(async (path: string): Promise<string> => {
    return window.pulseAPI.fs.readFile(path);
  }, []);

  const writeFile = useCallback(async (path: string, content: string): Promise<void> => {
    return window.pulseAPI.fs.writeFile(path, content);
  }, []);

  const exists = useCallback(async (path: string): Promise<boolean> => {
    return window.pulseAPI.fs.exists(path);
  }, []);

  const createDirectory = useCallback(async (path: string): Promise<void> => {
    return window.pulseAPI.fs.mkdir(path);
  }, []);

  const deleteFile = useCallback(async (path: string): Promise<void> => {
    return window.pulseAPI.fs.remove(path);
  }, []);

  const renameFile = useCallback(async (oldPath: string, newPath: string): Promise<void> => {
    return window.pulseAPI.fs.rename(oldPath, newPath);
  }, []);

  const revealInExplorer = useCallback((path: string): void => {
    window.pulseAPI.workspace.revealInExplorer(path);
  }, []);

  return {
    readFile,
    writeFile,
    exists,
    createDirectory,
    deleteFile,
    renameFile,
    revealInExplorer,
  };
}
