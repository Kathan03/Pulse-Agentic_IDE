/**
 * Pulse IDE - Window Control IPC Handlers
 *
 * Handles window control operations for the custom frameless window.
 */

import { IpcMain, BrowserWindow, shell } from 'electron';

/**
 * Set up window control IPC handlers.
 *
 * @param ipcMain - The IPC main instance.
 * @param getMainWindow - Function to get the main BrowserWindow instance.
 */
export function setupWindowHandlers(
  ipcMain: IpcMain,
  getMainWindow: () => BrowserWindow | null
): void {
  // ========================================================================
  // Minimize window
  // ========================================================================
  ipcMain.on('window:minimize', () => {
    const win = getMainWindow();
    win?.minimize();
  });

  // ========================================================================
  // Maximize or restore window
  // ========================================================================
  ipcMain.on('window:maximize', () => {
    const win = getMainWindow();
    if (!win) return;

    if (win.isMaximized()) {
      win.unmaximize();
    } else {
      win.maximize();
    }
  });

  // ========================================================================
  // Close window
  // ========================================================================
  ipcMain.on('window:close', () => {
    const win = getMainWindow();
    win?.close();
  });

  // ========================================================================
  // Check if window is maximized
  // ========================================================================
  ipcMain.handle('window:isMaximized', () => {
    const win = getMainWindow();
    return win?.isMaximized() ?? false;
  });

  // ========================================================================
  // Open external URL
  // ========================================================================
  ipcMain.handle('shell:openExternal', async (_event, url: string) => {
    await shell.openExternal(url);
  });

  // ========================================================================
  // Emit maximize state changes to renderer
  // ========================================================================
  const win = getMainWindow();
  if (win) {
    const emitMaximizeChange = () => {
      win.webContents.send('window:maximizeChange', win.isMaximized());
    };

    win.on('maximize', emitMaximizeChange);
    win.on('unmaximize', emitMaximizeChange);
  }
}
