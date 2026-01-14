/**
 * Menu IPC Handlers
 *
 * Sets up the native Electron application menu and IPC handlers
 * for menu actions that need to communicate with the renderer.
 */

import { BrowserWindow, IpcMain, Menu, MenuItemConstructorOptions, dialog, shell, app } from 'electron';

type WindowGetter = () => BrowserWindow | null;

/**
 * Set up menu-related IPC handlers.
 */
export function setupMenuHandlers(ipcMain: IpcMain, getWindow: WindowGetter): void {
  // Handle menu action from renderer
  ipcMain.handle('menu:trigger', async (_event, action: string) => {
    const win = getWindow();
    if (!win) return;

    switch (action) {
      case 'new-file':
        win.webContents.send('menu:new-file');
        break;
      case 'open-file':
        await handleOpenFile(win);
        break;
      case 'open-folder':
        await handleOpenFolder(win);
        break;
      case 'save':
        win.webContents.send('menu:save');
        break;
      case 'save-as':
        win.webContents.send('menu:save-as');
        break;
      case 'undo':
        win.webContents.send('menu:undo');
        break;
      case 'redo':
        win.webContents.send('menu:redo');
        break;
      case 'cut':
        win.webContents.send('menu:cut');
        break;
      case 'copy':
        win.webContents.send('menu:copy');
        break;
      case 'paste':
        win.webContents.send('menu:paste');
        break;
      case 'find':
        win.webContents.send('menu:find');
        break;
      case 'toggle-sidebar':
        win.webContents.send('menu:toggle-sidebar');
        break;
      case 'toggle-agent-panel':
        win.webContents.send('menu:toggle-agent-panel');
        break;
      case 'toggle-terminal':
        win.webContents.send('menu:toggle-terminal');
        break;
      case 'toggle-devtools':
        win.webContents.toggleDevTools();
        break;
      case 'reload':
        win.reload();
        break;
      case 'settings':
        win.webContents.send('menu:settings');
        break;
    }
  });
}

/**
 * Handle opening a file via dialog.
 */
async function handleOpenFile(win: BrowserWindow): Promise<void> {
  const result = await dialog.showOpenDialog(win, {
    properties: ['openFile'],
    filters: [
      { name: 'All Files', extensions: ['*'] },
      { name: 'Structured Text', extensions: ['st'] },
      { name: 'TypeScript', extensions: ['ts', 'tsx'] },
      { name: 'JavaScript', extensions: ['js', 'jsx'] },
      { name: 'Python', extensions: ['py'] },
      { name: 'JSON', extensions: ['json'] },
    ],
  });

  if (!result.canceled && result.filePaths.length > 0) {
    win.webContents.send('menu:file-opened', result.filePaths[0]);
  }
}

/**
 * Handle opening a folder via dialog.
 */
async function handleOpenFolder(win: BrowserWindow): Promise<void> {
  const result = await dialog.showOpenDialog(win, {
    properties: ['openDirectory'],
  });

  if (!result.canceled && result.filePaths.length > 0) {
    win.webContents.send('menu:folder-opened', result.filePaths[0]);
  }
}

/**
 * Create the application menu.
 */
export function createApplicationMenu(getWindow: WindowGetter): Menu {
  const isMac = process.platform === 'darwin';

  const template: MenuItemConstructorOptions[] = [
    // File Menu
    {
      label: 'File',
      submenu: [
        {
          label: 'New File',
          accelerator: 'CmdOrCtrl+N',
          click: () => triggerMenuAction(getWindow, 'new-file'),
        },
        { type: 'separator' },
        {
          label: 'Open File...',
          accelerator: 'CmdOrCtrl+O',
          click: () => triggerMenuAction(getWindow, 'open-file'),
        },
        {
          label: 'Open Folder...',
          accelerator: 'CmdOrCtrl+K CmdOrCtrl+O',
          click: () => triggerMenuAction(getWindow, 'open-folder'),
        },
        { type: 'separator' },
        {
          label: 'Save',
          accelerator: 'CmdOrCtrl+S',
          click: () => triggerMenuAction(getWindow, 'save'),
        },
        {
          label: 'Save As...',
          accelerator: 'CmdOrCtrl+Shift+S',
          click: () => triggerMenuAction(getWindow, 'save-as'),
        },
        { type: 'separator' },
        // Settings for Windows/Linux (macOS has it in App menu)
        ...(!isMac ? [
          {
            label: 'Settings',
            accelerator: 'Ctrl+,',
            click: () => triggerMenuAction(getWindow, 'settings'),
          },
          { type: 'separator' as const },
        ] : []),
        isMac ? { role: 'close' } : { role: 'quit' },
      ],
    },

    // Edit Menu
    {
      label: 'Edit',
      submenu: [
        {
          label: 'Undo',
          accelerator: 'CmdOrCtrl+Z',
          click: () => triggerMenuAction(getWindow, 'undo'),
        },
        {
          label: 'Redo',
          accelerator: 'CmdOrCtrl+Shift+Z',
          click: () => triggerMenuAction(getWindow, 'redo'),
        },
        { type: 'separator' },
        {
          label: 'Cut',
          accelerator: 'CmdOrCtrl+X',
          click: () => triggerMenuAction(getWindow, 'cut'),
        },
        {
          label: 'Copy',
          accelerator: 'CmdOrCtrl+C',
          click: () => triggerMenuAction(getWindow, 'copy'),
        },
        {
          label: 'Paste',
          accelerator: 'CmdOrCtrl+V',
          click: () => triggerMenuAction(getWindow, 'paste'),
        },
        { type: 'separator' },
        {
          label: 'Find',
          accelerator: 'CmdOrCtrl+F',
          click: () => triggerMenuAction(getWindow, 'find'),
        },
      ],
    },

    // View Menu
    {
      label: 'View',
      submenu: [
        {
          label: 'Toggle Sidebar',
          accelerator: 'CmdOrCtrl+B',
          click: () => triggerMenuAction(getWindow, 'toggle-sidebar'),
        },
        {
          label: 'Toggle Agent Panel',
          accelerator: 'CmdOrCtrl+J',
          click: () => triggerMenuAction(getWindow, 'toggle-agent-panel'),
        },
        {
          label: 'Toggle Terminal',
          accelerator: 'Ctrl+`',
          click: () => triggerMenuAction(getWindow, 'toggle-terminal'),
        },
        { type: 'separator' },
        {
          label: 'Toggle Developer Tools',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => triggerMenuAction(getWindow, 'toggle-devtools'),
        },
        { type: 'separator' },
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => triggerMenuAction(getWindow, 'reload'),
        },
      ],
    },

    // Help Menu
    {
      label: 'Help',
      submenu: [
        {
          label: 'Documentation',
          click: () => shell.openExternal('https://github.com/your-repo/pulse-ide'),
        },
        {
          label: 'Report Issue',
          click: () => shell.openExternal('https://github.com/your-repo/pulse-ide/issues'),
        },
        { type: 'separator' },
        {
          label: 'About Pulse IDE',
          click: () => {
            const win = getWindow();
            if (win) {
              dialog.showMessageBox(win, {
                type: 'info',
                title: 'About Pulse IDE',
                message: 'Pulse IDE',
                detail: `Version: 2.6.0\nAgentic AI IDE for PLC Coding\n\nBuilt with Electron, React, and LangGraph.`,
              });
            }
          },
        },
      ],
    },
  ];

  // Add macOS-specific app menu
  if (isMac) {
    template.unshift({
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        {
          label: 'Settings',
          accelerator: 'Cmd+,',
          click: () => triggerMenuAction(getWindow, 'settings'),
        },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    });
  }

  return Menu.buildFromTemplate(template);
}

/**
 * Helper to trigger menu actions by sending to renderer.
 */
function triggerMenuAction(getWindow: WindowGetter, action: string): void {
  const win = getWindow();
  if (win) {
    win.webContents.send('menu:action', action);
  }
}
