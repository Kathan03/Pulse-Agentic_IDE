/**
 * Type declarations for the Electron preload API.
 *
 * These types define the bridge between main and renderer processes.
 */

export interface FileEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  isFile: boolean;
  size: number;
  modified: number;
}

export interface FileStat {
  size: number;
  modified: number;
  created: number;
  isDirectory: boolean;
  isFile: boolean;
}

export interface FileFilter {
  name: string;
  extensions: string[];
}

export interface FileSystemAPI {
  readFile: (filePath: string) => Promise<string>;
  writeFile: (filePath: string, content: string) => Promise<void>;
  exists: (filePath: string) => Promise<boolean>;
  readDir: (dirPath: string) => Promise<FileEntry[]>;
  mkdir: (dirPath: string) => Promise<void>;
  remove: (targetPath: string) => Promise<void>;
  rename: (oldPath: string, newPath: string) => Promise<void>;
  stat: (filePath: string) => Promise<FileStat>;
  watch: (dirPath: string) => void;
  unwatch: (dirPath: string) => void;
  onFileChange: (callback: (event: string, path: string) => void) => () => void;
}

export interface WorkspaceAPI {
  openFolder: () => Promise<string | null>;
  openFile: (filters?: FileFilter[]) => Promise<string | null>;
  getRecentWorkspaces: () => Promise<string[]>;
  addRecentWorkspace: (workspacePath: string) => Promise<void>;
  clearRecentWorkspaces: () => Promise<void>;
  revealInExplorer: (filePath: string) => void;
}

export interface WindowAPI {
  minimize: () => void;
  maximize: () => void;
  close: () => void;
  isMaximized: () => Promise<boolean>;
  onMaximizeChange: (callback: (isMaximized: boolean) => void) => () => void;
}

export interface ShellAPI {
  openExternal: (url: string) => Promise<void>;
}

export interface MenuAPI {
  trigger: (action: string) => Promise<void>;
  onAction: (callback: (action: string) => void) => () => void;
  onFileOpened: (callback: (filePath: string) => void) => () => void;
  onFolderOpened: (callback: (folderPath: string) => void) => () => void;
}

export interface BackendAPI {
  getPort: () => Promise<number>;
}

export interface TerminalAPI {
  execute: (command: string) => Promise<string>;
}

export interface PtyAPI {
  spawn: (options?: {
    cwd?: string;
    shell?: string;
    cols?: number;
    rows?: number;
  }) => Promise<{ id: number; shell: string; cwd: string }>;
  write: (id: number, data: string) => void;
  resize: (id: number, cols: number, rows: number) => void;
  kill: (id: number) => Promise<boolean>;
  setCwd: (id: number, cwd: string) => Promise<boolean>;
  onData: (callback: (id: number, data: string) => void) => () => void;
  onExit: (callback: (id: number, exitCode: number) => void) => () => void;
}

export interface PulseAPI {
  fs: FileSystemAPI;
  workspace: WorkspaceAPI;
  window: WindowAPI;
  shell: ShellAPI;
  menu: MenuAPI;
  backend: BackendAPI;
  terminal: TerminalAPI;
  pty: PtyAPI;
  platform: NodeJS.Platform;
}

declare global {
  interface Window {
    pulseAPI: PulseAPI;
  }
}

export { };
