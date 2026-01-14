/**
 * Pulse IDE - File System IPC Handlers
 *
 * Provides secure file system access from the renderer process.
 * Uses chokidar for efficient file watching.
 */

import { IpcMain, BrowserWindow } from 'electron';
import * as fs from 'fs/promises';
import * as fsSync from 'fs';
import * as path from 'path';
import chokidar, { FSWatcher } from 'chokidar';

// Active file watchers by directory
const watchers = new Map<string, FSWatcher>();

/**
 * Set up file system IPC handlers.
 */
export function setupFileSystemHandlers(ipcMain: IpcMain): void {
  // ========================================================================
  // Read file contents
  // ========================================================================
  ipcMain.handle('fs:readFile', async (_event, filePath: string) => {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      return content;
    } catch (error) {
      throw new Error(`Failed to read file: ${(error as Error).message}`);
    }
  });

  // ========================================================================
  // Write file contents
  // ========================================================================
  ipcMain.handle('fs:writeFile', async (_event, filePath: string, content: string) => {
    try {
      // Ensure directory exists
      const dir = path.dirname(filePath);
      await fs.mkdir(dir, { recursive: true });

      // Write file
      await fs.writeFile(filePath, content, 'utf-8');
    } catch (error) {
      throw new Error(`Failed to write file: ${(error as Error).message}`);
    }
  });

  // ========================================================================
  // Check if file/directory exists
  // ========================================================================
  ipcMain.handle('fs:exists', async (_event, filePath: string) => {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  });

  // ========================================================================
  // Read directory contents
  // ========================================================================
  ipcMain.handle('fs:readDir', async (_event, dirPath: string) => {
    try {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });

      const results = await Promise.all(
        entries.map(async (entry) => {
          const entryPath = path.join(dirPath, entry.name);
          let stats = { size: 0, mtime: new Date() };

          try {
            stats = await fs.stat(entryPath);
          } catch {
            // Ignore stat errors for inaccessible files
          }

          return {
            name: entry.name,
            path: entryPath,
            isDirectory: entry.isDirectory(),
            isFile: entry.isFile(),
            size: stats.size,
            modified: stats.mtime.getTime(),
          };
        })
      );

      // Sort: directories first, then alphabetically
      results.sort((a, b) => {
        if (a.isDirectory && !b.isDirectory) return -1;
        if (!a.isDirectory && b.isDirectory) return 1;
        return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
      });

      return results;
    } catch (error) {
      throw new Error(`Failed to read directory: ${(error as Error).message}`);
    }
  });

  // ========================================================================
  // Create directory
  // ========================================================================
  ipcMain.handle('fs:mkdir', async (_event, dirPath: string) => {
    try {
      await fs.mkdir(dirPath, { recursive: true });
    } catch (error) {
      throw new Error(`Failed to create directory: ${(error as Error).message}`);
    }
  });

  // ========================================================================
  // Remove file or directory
  // ========================================================================
  ipcMain.handle('fs:remove', async (_event, targetPath: string) => {
    try {
      const stats = await fs.stat(targetPath);
      if (stats.isDirectory()) {
        await fs.rm(targetPath, { recursive: true });
      } else {
        await fs.unlink(targetPath);
      }
    } catch (error) {
      throw new Error(`Failed to remove: ${(error as Error).message}`);
    }
  });

  // ========================================================================
  // Rename/move file or directory
  // ========================================================================
  ipcMain.handle('fs:rename', async (_event, oldPath: string, newPath: string) => {
    try {
      await fs.rename(oldPath, newPath);
    } catch (error) {
      throw new Error(`Failed to rename: ${(error as Error).message}`);
    }
  });

  // ========================================================================
  // Get file stats
  // ========================================================================
  ipcMain.handle('fs:stat', async (_event, filePath: string) => {
    try {
      const stats = await fs.stat(filePath);
      return {
        size: stats.size,
        modified: stats.mtime.getTime(),
        created: stats.birthtime.getTime(),
        isDirectory: stats.isDirectory(),
        isFile: stats.isFile(),
      };
    } catch (error) {
      throw new Error(`Failed to get file stats: ${(error as Error).message}`);
    }
  });

  // ========================================================================
  // Watch directory for changes
  // ========================================================================
  ipcMain.on('fs:watch', (event, dirPath: string) => {
    // Don't create duplicate watchers
    if (watchers.has(dirPath)) {
      return;
    }

    const watcher = chokidar.watch(dirPath, {
      persistent: true,
      ignoreInitial: true,
      depth: 10, // Limit depth for performance
      ignored: [
        '**/node_modules/**',
        '**/.git/**',
        '**/dist/**',
        '**/build/**',
        '**/__pycache__/**',
        '**/*.pyc',
      ],
      awaitWriteFinish: {
        stabilityThreshold: 100,
        pollInterval: 50,
      },
    });

    // Notify renderer of changes
    const notify = (fsEvent: string, fsPath: string) => {
      const windows = BrowserWindow.getAllWindows();
      windows.forEach((win) => {
        win.webContents.send('fs:change', fsEvent, fsPath);
      });
    };

    watcher
      .on('add', (filePath) => notify('add', filePath))
      .on('change', (filePath) => notify('change', filePath))
      .on('unlink', (filePath) => notify('unlink', filePath))
      .on('addDir', (dirPath) => notify('addDir', dirPath))
      .on('unlinkDir', (dirPath) => notify('unlinkDir', dirPath));

    watchers.set(dirPath, watcher);
  });

  // ========================================================================
  // Stop watching directory
  // ========================================================================
  ipcMain.on('fs:unwatch', (_event, dirPath: string) => {
    const watcher = watchers.get(dirPath);
    if (watcher) {
      watcher.close();
      watchers.delete(dirPath);
    }
  });
}

/**
 * Clean up all file watchers.
 * Call this on app quit.
 */
export function cleanupFileWatchers(): void {
  for (const [, watcher] of watchers) {
    watcher.close();
  }
  watchers.clear();
}
