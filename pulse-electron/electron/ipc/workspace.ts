/**
 * Pulse IDE - Workspace IPC Handlers
 *
 * Handles workspace-related operations like folder dialogs,
 * recent workspace management, and file explorer integration.
 */

import { IpcMain, dialog, shell } from 'electron';
import * as fs from 'fs/promises';
import * as path from 'path';
import { app } from 'electron';

// Path to store recent workspaces
const RECENT_FILE = path.join(app.getPath('userData'), 'recent-workspaces.json');
const MAX_RECENT = 10;

/**
 * Load recent workspaces from storage.
 */
async function loadRecentWorkspaces(): Promise<string[]> {
  try {
    const data = await fs.readFile(RECENT_FILE, 'utf-8');
    return JSON.parse(data);
  } catch {
    return [];
  }
}

/**
 * Save recent workspaces to storage.
 */
async function saveRecentWorkspaces(workspaces: string[]): Promise<void> {
  await fs.writeFile(RECENT_FILE, JSON.stringify(workspaces), 'utf-8');
}

/**
 * Set up workspace IPC handlers.
 */
export function setupWorkspaceHandlers(ipcMain: IpcMain): void {
  // ========================================================================
  // Open folder picker dialog
  // ========================================================================
  ipcMain.handle('workspace:openFolder', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
      title: 'Open Workspace Folder',
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  // ========================================================================
  // Open file picker dialog
  // ========================================================================
  ipcMain.handle(
    'workspace:openFile',
    async (_event, filters?: Array<{ name: string; extensions: string[] }>) => {
      const result = await dialog.showOpenDialog({
        properties: ['openFile'],
        title: 'Open File',
        filters: filters || [
          { name: 'Structured Text', extensions: ['st', 'ST'] },
          { name: 'All Files', extensions: ['*'] },
        ],
      });

      if (result.canceled || result.filePaths.length === 0) {
        return null;
      }

      return result.filePaths[0];
    }
  );

  // ========================================================================
  // Get recent workspaces
  // ========================================================================
  ipcMain.handle('workspace:getRecent', async () => {
    return loadRecentWorkspaces();
  });

  // ========================================================================
  // Add workspace to recent list
  // ========================================================================
  ipcMain.handle('workspace:addRecent', async (_event, workspacePath: string) => {
    const recent = await loadRecentWorkspaces();

    // Remove if already exists (will be re-added at top)
    const filtered = recent.filter((p) => p !== workspacePath);

    // Add to top
    filtered.unshift(workspacePath);

    // Limit size
    const limited = filtered.slice(0, MAX_RECENT);

    await saveRecentWorkspaces(limited);
  });

  // ========================================================================
  // Clear recent workspaces
  // ========================================================================
  ipcMain.handle('workspace:clearRecent', async () => {
    await saveRecentWorkspaces([]);
  });

  // ========================================================================
  // Reveal file in native explorer
  // ========================================================================
  ipcMain.on('workspace:reveal', (_event, filePath: string) => {
    shell.showItemInFolder(filePath);
  });
}
