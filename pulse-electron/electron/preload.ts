/**
 * Pulse IDE - Preload Script
 *
 * Bridges the main and renderer processes with secure IPC.
 * Exposes a typed API to the renderer via contextBridge.
 */

import { contextBridge, ipcRenderer, IpcRendererEvent } from 'electron';

/**
 * File system API exposed to renderer.
 */
const fileSystemAPI = {
  /**
   * Read a file's contents.
   */
  readFile: (filePath: string): Promise<string> => {
    return ipcRenderer.invoke('fs:readFile', filePath);
  },

  /**
   * Write content to a file.
   */
  writeFile: (filePath: string, content: string): Promise<void> => {
    return ipcRenderer.invoke('fs:writeFile', filePath, content);
  },

  /**
   * Check if a file exists.
   */
  exists: (filePath: string): Promise<boolean> => {
    return ipcRenderer.invoke('fs:exists', filePath);
  },

  /**
   * Read directory contents.
   */
  readDir: (dirPath: string): Promise<Array<{
    name: string;
    path: string;
    isDirectory: boolean;
    isFile: boolean;
    size: number;
    modified: number;
  }>> => {
    return ipcRenderer.invoke('fs:readDir', dirPath);
  },

  /**
   * Create a directory.
   */
  mkdir: (dirPath: string): Promise<void> => {
    return ipcRenderer.invoke('fs:mkdir', dirPath);
  },

  /**
   * Delete a file or directory.
   */
  remove: (targetPath: string): Promise<void> => {
    return ipcRenderer.invoke('fs:remove', targetPath);
  },

  /**
   * Rename/move a file or directory.
   */
  rename: (oldPath: string, newPath: string): Promise<void> => {
    return ipcRenderer.invoke('fs:rename', oldPath, newPath);
  },

  /**
   * Get file stats.
   */
  stat: (filePath: string): Promise<{
    size: number;
    modified: number;
    created: number;
    isDirectory: boolean;
    isFile: boolean;
  }> => {
    return ipcRenderer.invoke('fs:stat', filePath);
  },

  /**
   * Watch a directory for changes.
   */
  watch: (dirPath: string): void => {
    ipcRenderer.send('fs:watch', dirPath);
  },

  /**
   * Stop watching a directory.
   */
  unwatch: (dirPath: string): void => {
    ipcRenderer.send('fs:unwatch', dirPath);
  },

  /**
   * Subscribe to file system change events.
   */
  onFileChange: (callback: (event: string, path: string) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, fsEvent: string, fsPath: string) => {
      callback(fsEvent, fsPath);
    };
    ipcRenderer.on('fs:change', handler);
    return () => {
      ipcRenderer.removeListener('fs:change', handler);
    };
  },
};

/**
 * Workspace API exposed to renderer.
 */
const workspaceAPI = {
  /**
   * Open a folder picker dialog.
   */
  openFolder: (): Promise<string | null> => {
    return ipcRenderer.invoke('workspace:openFolder');
  },

  /**
   * Open a file picker dialog.
   */
  openFile: (filters?: Array<{ name: string; extensions: string[] }>): Promise<string | null> => {
    return ipcRenderer.invoke('workspace:openFile', filters);
  },

  /**
   * Get recent workspaces from storage.
   */
  getRecentWorkspaces: (): Promise<string[]> => {
    return ipcRenderer.invoke('workspace:getRecent');
  },

  /**
   * Add a workspace to recent list.
   */
  addRecentWorkspace: (workspacePath: string): Promise<void> => {
    return ipcRenderer.invoke('workspace:addRecent', workspacePath);
  },

  /**
   * Clear recent workspaces.
   */
  clearRecentWorkspaces: (): Promise<void> => {
    return ipcRenderer.invoke('workspace:clearRecent');
  },

  /**
   * Reveal a file in the native file explorer.
   */
  revealInExplorer: (filePath: string): void => {
    ipcRenderer.send('workspace:reveal', filePath);
  },
};

/**
 * Window control API exposed to renderer.
 */
const windowAPI = {
  /**
   * Minimize the window.
   */
  minimize: (): void => {
    ipcRenderer.send('window:minimize');
  },

  /**
   * Maximize or restore the window.
   */
  maximize: (): void => {
    ipcRenderer.send('window:maximize');
  },

  /**
   * Close the window.
   */
  close: (): void => {
    ipcRenderer.send('window:close');
  },

  /**
   * Check if window is maximized.
   */
  isMaximized: (): Promise<boolean> => {
    return ipcRenderer.invoke('window:isMaximized');
  },

  /**
   * Subscribe to maximize state changes.
   */
  onMaximizeChange: (callback: (isMaximized: boolean) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, maximized: boolean) => {
      callback(maximized);
    };
    ipcRenderer.on('window:maximizeChange', handler);
    return () => {
      ipcRenderer.removeListener('window:maximizeChange', handler);
    };
  },
};

/**
 * Shell API for opening external resources.
 */
const shellAPI = {
  /**
   * Open a URL in the default browser.
   */
  openExternal: (url: string): Promise<void> => {
    return ipcRenderer.invoke('shell:openExternal', url);
  },
};

/**
 * Backend API for getting backend connection info.
 */
const backendAPI = {
  /**
   * Get the backend server port.
   */
  getPort: (): Promise<number> => {
    return ipcRenderer.invoke('backend:getPort');
  },
};

/**
 * Terminal API for executing shell commands.
 */
const terminalAPI = {
  /**
   * Execute a command in the shell (simple one-shot execution).
   */
  execute: (command: string): Promise<string> => {
    return ipcRenderer.invoke('terminal:execute', command);
  },
};

/**
 * PTY API for interactive terminal sessions.
 */
const ptyAPI = {
  /**
   * Spawn a new PTY process.
   */
  spawn: (options?: {
    cwd?: string;
    shell?: string;
    cols?: number;
    rows?: number;
  }): Promise<{ id: number; shell: string; cwd: string }> => {
    return ipcRenderer.invoke('pty:spawn', options || {});
  },

  /**
   * Write data to a PTY process.
   */
  write: (id: number, data: string): void => {
    ipcRenderer.send('pty:write', id, data);
  },

  /**
   * Resize a PTY process.
   */
  resize: (id: number, cols: number, rows: number): void => {
    ipcRenderer.send('pty:resize', id, cols, rows);
  },

  /**
   * Kill a PTY process.
   */
  kill: (id: number): Promise<boolean> => {
    return ipcRenderer.invoke('pty:kill', id);
  },

  /**
   * Set the working directory of a PTY.
   */
  setCwd: (id: number, cwd: string): Promise<boolean> => {
    return ipcRenderer.invoke('pty:setCwd', id, cwd);
  },

  /**
   * Subscribe to PTY data events.
   */
  onData: (callback: (id: number, data: string) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, id: number, data: string) => {
      callback(id, data);
    };
    ipcRenderer.on('pty:data', handler);
    return () => {
      ipcRenderer.removeListener('pty:data', handler);
    };
  },

  /**
   * Subscribe to PTY exit events.
   */
  onExit: (callback: (id: number, exitCode: number) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, id: number, exitCode: number) => {
      callback(id, exitCode);
    };
    ipcRenderer.on('pty:exit', handler);
    return () => {
      ipcRenderer.removeListener('pty:exit', handler);
    };
  },
};

/**
 * Menu API for handling menu actions.
 */
const menuAPI = {
  /**
   * Trigger a menu action.
   */
  trigger: (action: string): Promise<void> => {
    return ipcRenderer.invoke('menu:trigger', action);
  },

  /**
   * Subscribe to menu action events from main process.
   */
  onAction: (callback: (action: string) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, action: string) => {
      callback(action);
    };
    ipcRenderer.on('menu:action', handler);
    return () => {
      ipcRenderer.removeListener('menu:action', handler);
    };
  },

  /**
   * Subscribe to file opened events.
   */
  onFileOpened: (callback: (filePath: string) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, filePath: string) => {
      callback(filePath);
    };
    ipcRenderer.on('menu:file-opened', handler);
    return () => {
      ipcRenderer.removeListener('menu:file-opened', handler);
    };
  },

  /**
   * Subscribe to folder opened events.
   */
  onFolderOpened: (callback: (folderPath: string) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, folderPath: string) => {
      callback(folderPath);
    };
    ipcRenderer.on('menu:folder-opened', handler);
    return () => {
      ipcRenderer.removeListener('menu:folder-opened', handler);
    };
  },
};

// ============================================================================
// Expose APIs to Renderer
// ============================================================================

contextBridge.exposeInMainWorld('pulseAPI', {
  fs: fileSystemAPI,
  workspace: workspaceAPI,
  window: windowAPI,
  shell: shellAPI,
  menu: menuAPI,
  backend: backendAPI,
  terminal: terminalAPI,
  pty: ptyAPI,
  platform: process.platform,
});

// Type declarations for renderer
export type PulseAPI = {
  fs: typeof fileSystemAPI;
  workspace: typeof workspaceAPI;
  window: typeof windowAPI;
  shell: typeof shellAPI;
  menu: typeof menuAPI;
  backend: typeof backendAPI;
  terminal: typeof terminalAPI;
  pty: typeof ptyAPI;
  platform: NodeJS.Platform;
};
