/**
 * Terminal IPC Handlers
 *
 * Provides PTY-based terminal functionality using node-pty.
 * Creates real interactive shell sessions (PowerShell/bash).
 */

import { IpcMain, IpcMainEvent, BrowserWindow } from 'electron';
import * as os from 'os';

// Dynamic import for node-pty (native module)
let pty: typeof import('node-pty') | null = null;

interface PtyProcess {
  id: number;
  process: import('node-pty').IPty;
  cwd: string;
}

// Active PTY processes
const ptyProcesses: Map<number, PtyProcess> = new Map();
let nextPtyId = 1;

/**
 * Get the default shell for the current platform.
 */
function getDefaultShell(): string {
  if (process.platform === 'win32') {
    // Prefer PowerShell Core, then Windows PowerShell, then cmd
    return process.env.COMSPEC || 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe';
  } else if (process.platform === 'darwin') {
    return process.env.SHELL || '/bin/zsh';
  } else {
    return process.env.SHELL || '/bin/bash';
  }
}

/**
 * Get shell arguments for the current platform.
 */
function getShellArgs(): string[] {
  if (process.platform === 'win32') {
    // PowerShell arguments for better experience
    return ['-NoLogo'];
  }
  return [];
}

/**
 * Initialize node-pty dynamically.
 * This handles the native module loading which can fail in some environments.
 */
async function initializePty(): Promise<boolean> {
  if (pty) return true;

  try {
    pty = await import('node-pty');
    console.log('[Terminal] node-pty loaded successfully');
    return true;
  } catch (error) {
    console.error('[Terminal] Failed to load node-pty:', error);
    return false;
  }
}

/**
 * Set up terminal IPC handlers.
 */
export function setupTerminalHandlers(
  ipcMain: IpcMain,
  getMainWindow: () => BrowserWindow | null
): void {
  /**
   * Spawn a new PTY process.
   */
  ipcMain.handle('pty:spawn', async (_event, options: {
    cwd?: string;
    shell?: string;
    cols?: number;
    rows?: number;
  }) => {
    // Initialize node-pty if not already done
    if (!await initializePty() || !pty) {
      throw new Error('Terminal not available: node-pty failed to load');
    }

    const shell = options.shell || getDefaultShell();
    const shellArgs = getShellArgs();
    const cwd = options.cwd || os.homedir();
    const cols = options.cols || 80;
    const rows = options.rows || 24;

    try {
      const ptyProcess = pty.spawn(shell, shellArgs, {
        name: 'xterm-256color',
        cols,
        rows,
        cwd,
        env: {
          ...process.env,
          // Ensure proper terminal colors
          TERM: 'xterm-256color',
          COLORTERM: 'truecolor',
        } as Record<string, string>,
      });

      const id = nextPtyId++;

      // Store the process
      ptyProcesses.set(id, {
        id,
        process: ptyProcess,
        cwd,
      });

      // Forward PTY output to renderer
      const mainWindow = getMainWindow();
      ptyProcess.onData((data: string) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('pty:data', id, data);
        }
      });

      // Handle PTY exit
      ptyProcess.onExit(({ exitCode, signal }) => {
        console.log(`[Terminal] PTY ${id} exited with code ${exitCode}, signal ${signal}`);
        ptyProcesses.delete(id);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('pty:exit', id, exitCode);
        }
      });

      console.log(`[Terminal] Spawned PTY ${id}: ${shell} in ${cwd}`);
      return { id, shell, cwd };
    } catch (error) {
      console.error('[Terminal] Failed to spawn PTY:', error);
      throw error;
    }
  });

  /**
   * Write data to a PTY process.
   */
  ipcMain.on('pty:write', (_event: IpcMainEvent, id: number, data: string) => {
    const ptyInfo = ptyProcesses.get(id);
    if (ptyInfo) {
      ptyInfo.process.write(data);
    } else {
      console.warn(`[Terminal] Attempted to write to non-existent PTY ${id}`);
    }
  });

  /**
   * Resize a PTY process.
   */
  ipcMain.on('pty:resize', (_event: IpcMainEvent, id: number, cols: number, rows: number) => {
    const ptyInfo = ptyProcesses.get(id);
    if (ptyInfo) {
      try {
        ptyInfo.process.resize(cols, rows);
      } catch (error) {
        console.error(`[Terminal] Failed to resize PTY ${id}:`, error);
      }
    }
  });

  /**
   * Kill a PTY process.
   */
  ipcMain.handle('pty:kill', async (_event, id: number) => {
    const ptyInfo = ptyProcesses.get(id);
    if (ptyInfo) {
      try {
        ptyInfo.process.kill();
        ptyProcesses.delete(id);
        console.log(`[Terminal] Killed PTY ${id}`);
        return true;
      } catch (error) {
        console.error(`[Terminal] Failed to kill PTY ${id}:`, error);
        return false;
      }
    }
    return false;
  });

  /**
   * Kill all PTY processes (called on app quit).
   */
  ipcMain.handle('pty:killAll', async () => {
    for (const [id, ptyInfo] of ptyProcesses) {
      try {
        ptyInfo.process.kill();
        console.log(`[Terminal] Killed PTY ${id}`);
      } catch (error) {
        console.error(`[Terminal] Failed to kill PTY ${id}:`, error);
      }
    }
    ptyProcesses.clear();
  });

  /**
   * Get all active PTY IDs.
   */
  ipcMain.handle('pty:list', async () => {
    return Array.from(ptyProcesses.keys());
  });

  /**
   * Change working directory of a PTY (sends cd command).
   */
  ipcMain.handle('pty:setCwd', async (_event, id: number, cwd: string) => {
    const ptyInfo = ptyProcesses.get(id);
    if (ptyInfo) {
      // Send cd command to the shell
      const cdCommand = process.platform === 'win32'
        ? `cd /d "${cwd}"\r`
        : `cd "${cwd}"\n`;
      ptyInfo.process.write(cdCommand);
      ptyInfo.cwd = cwd;
      return true;
    }
    return false;
  });
}

/**
 * Cleanup all PTY processes.
 * Should be called before app quits.
 */
export function cleanupTerminals(): void {
  for (const [id, ptyInfo] of ptyProcesses) {
    try {
      ptyInfo.process.kill();
      console.log(`[Terminal] Cleanup: killed PTY ${id}`);
    } catch (error) {
      // Ignore errors during cleanup
    }
  }
  ptyProcesses.clear();
}
