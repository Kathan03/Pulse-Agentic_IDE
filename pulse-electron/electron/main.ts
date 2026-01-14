/**
 * Pulse IDE - Electron Main Process
 *
 * Entry point for the Electron application.
 * Handles window creation, IPC setup, native integrations, and Python backend.
 */

import { app, BrowserWindow, ipcMain, shell, Menu, dialog } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { setupFileSystemHandlers } from './ipc/file-system';
import { setupWorkspaceHandlers } from './ipc/workspace';
import { setupWindowHandlers } from './ipc/window';
import { setupMenuHandlers, createApplicationMenu } from './ipc/menu';
import { setupTerminalHandlers, cleanupTerminals } from './ipc/terminal';

// Disable GPU hardware acceleration if needed for stability
// app.disableHardwareAcceleration();

// Path to preload script
const PRELOAD_PATH = path.join(__dirname, 'preload.js');

// Path to app icon
const ICON_PATH = path.join(__dirname, '../../assets/pulse_icon_bg_020321.ico');

// Development vs production paths
const isDev = !app.isPackaged;
const DEV_URL = 'http://localhost:5173';

// Default backend port (used in dev mode)
const DEFAULT_BACKEND_PORT = 8765;

// Python backend process (only used in production)
let pythonProcess: ChildProcess | null = null;
let backendPort: number = DEFAULT_BACKEND_PORT;

let mainWindow: BrowserWindow | null = null;

/**
 * Create the main application window.
 */
function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    frame: false, // Custom frameless window
    titleBarStyle: 'hidden',
    backgroundColor: '#1E1E1E',
    show: false, // Wait until ready-to-show
    icon: ICON_PATH, // App icon for Windows taskbar and title
    webPreferences: {
      preload: PRELOAD_PATH,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false, // Required for file system access
      webSecurity: true,
    },
  });

  // Load the app
  if (isDev) {
    mainWindow.loadURL(DEV_URL);
    // Open DevTools in development
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Show window when ready (prevents white flash)
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
    mainWindow?.focus();
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Clean up on close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * Set up all IPC handlers.
 */
function setupIPC(): void {
  // Window control handlers
  setupWindowHandlers(ipcMain, () => mainWindow);

  // File system handlers
  setupFileSystemHandlers(ipcMain);

  // Workspace handlers
  setupWorkspaceHandlers(ipcMain);

  // Menu handlers
  setupMenuHandlers(ipcMain, () => mainWindow);

  // Terminal handlers (PTY-based)
  setupTerminalHandlers(ipcMain, () => mainWindow);

  // Fallback simple terminal handler (for quick commands)
  ipcMain.handle('terminal:execute', async (_event, command: string) => {
    return new Promise<string>((resolve) => {
      const isWin = process.platform === 'win32';
      const shellCmd = isWin ? 'cmd.exe' : '/bin/bash';
      const args = isWin ? ['/c', command] : ['-c', command];

      // Use the project root if available, otherwise home directory
      const cwd = mainWindow?.webContents?.getURL()?.includes('localhost')
        ? process.cwd()
        : app.getPath('home');

      const child = spawn(shellCmd, args, {
        cwd,
        env: process.env,
        shell: false,
      });

      let output = '';
      let errorOutput = '';

      child.stdout?.on('data', (data) => {
        output += data.toString();
      });

      child.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });

      child.on('close', (code) => {
        if (code !== 0 && errorOutput) {
          resolve(errorOutput.trim() || output.trim());
        } else {
          resolve(output.trim());
        }
      });

      child.on('error', (err) => {
        resolve(`Error: ${err.message}`);
      });

      // Kill process after 30 seconds
      setTimeout(() => {
        if (!child.killed) {
          child.kill('SIGTERM');
          resolve('Command timed out after 30 seconds');
        }
      }, 30000);
    });
  });
}

// ============================================================================
// Python Backend Management
// ============================================================================

/**
 * Get the path to the Python backend.
 * In production, it's bundled in the extraResources directory.
 * In development, we don't spawn it (user runs it manually).
 */
function getPythonBackendPath(): string {
  if (isDev) {
    // In dev mode, user runs Python server manually
    return '';
  }

  // In production, look for bundled Python engine
  // The Python backend should be packaged as a PyInstaller executable
  const resourcesPath = process.resourcesPath;
  const backendName = process.platform === 'win32' ? 'pulse-server.exe' : 'pulse-server';
  return path.join(resourcesPath, 'backend', backendName);
}

/**
 * Start the Python backend server with dynamic port allocation.
 * Returns a promise that resolves with the port number.
 */
async function startPythonBackend(): Promise<number> {
  return new Promise((resolve, reject) => {
    if (isDev) {
      // In dev mode, assume backend is running on default port
      console.log('[Backend] Dev mode: Using default port', DEFAULT_BACKEND_PORT);
      resolve(DEFAULT_BACKEND_PORT);
      return;
    }

    const backendPath = getPythonBackendPath();

    if (!backendPath) {
      console.log('[Backend] No backend path configured');
      resolve(DEFAULT_BACKEND_PORT);
      return;
    }

    console.log('[Backend] Starting Python backend from:', backendPath);

    // Start Python server with port 0 for dynamic allocation
    pythonProcess = spawn(backendPath, [
      '--host', '127.0.0.1',
      '--port', '0', // Dynamic port allocation
    ], {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PULSE_ELECTRON_MODE: 'true',
      },
    });

    let portFound = false;
    let startupTimeout: NodeJS.Timeout;

    // Set a timeout for backend startup
    startupTimeout = setTimeout(() => {
      if (!portFound) {
        console.error('[Backend] Startup timeout - no port received');
        reject(new Error('Backend startup timeout'));
      }
    }, 30000); // 30 second timeout

    // Listen for the port announcement on stdout
    // The Python server should print: "PULSE_PORT:XXXXX"
    pythonProcess.stdout?.on('data', (data: Buffer) => {
      const output = data.toString();
      console.log('[Backend stdout]', output.trim());

      // Look for port announcement
      const portMatch = output.match(/PULSE_PORT:(\d+)/);
      if (portMatch && !portFound) {
        portFound = true;
        clearTimeout(startupTimeout);
        const port = parseInt(portMatch[1], 10);
        console.log('[Backend] Server started on port:', port);
        resolve(port);
      }
    });

    pythonProcess.stderr?.on('data', (data: Buffer) => {
      console.error('[Backend stderr]', data.toString().trim());
    });

    pythonProcess.on('error', (err) => {
      console.error('[Backend] Failed to start:', err);
      clearTimeout(startupTimeout);
      reject(err);
    });

    pythonProcess.on('exit', (code, signal) => {
      console.log('[Backend] Process exited:', { code, signal });
      pythonProcess = null;

      if (!portFound) {
        clearTimeout(startupTimeout);
        reject(new Error(`Backend exited with code ${code}`));
      }
    });
  });
}

/**
 * Stop the Python backend server.
 */
function stopPythonBackend(): void {
  if (pythonProcess) {
    console.log('[Backend] Stopping Python server...');
    pythonProcess.kill('SIGTERM');

    // Force kill after 5 seconds if still running
    setTimeout(() => {
      if (pythonProcess) {
        console.log('[Backend] Force killing Python server...');
        pythonProcess.kill('SIGKILL');
        pythonProcess = null;
      }
    }, 5000);
  }
}

// ============================================================================
// App Lifecycle
// ============================================================================

app.whenReady().then(async () => {
  setupIPC();

  // Start Python backend (or use default port in dev mode)
  try {
    backendPort = await startPythonBackend();
    console.log('[App] Backend available on port:', backendPort);

    // Expose the backend port to the renderer
    ipcMain.handle('backend:getPort', () => backendPort);
  } catch (error) {
    console.error('[App] Failed to start backend:', error);
    // In dev mode, continue anyway (user runs backend manually)
    if (!isDev) {
      dialog.showErrorBox(
        'Backend Error',
        'Failed to start the Python backend server. The application may not function correctly.'
      );
    }
  }

  createWindow();

  // Set up application menu (works with frameless windows too)
  const menu = createApplicationMenu(() => mainWindow);
  Menu.setApplicationMenu(menu);

  // macOS: re-create window when dock icon is clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Clean up backend and terminals on quit
app.on('before-quit', () => {
  cleanupTerminals();
  stopPythonBackend();
});

// Security: Prevent new window creation
app.on('web-contents-created', (_event, contents) => {
  contents.on('will-navigate', (event, _url) => {
    event.preventDefault();
  });
});
