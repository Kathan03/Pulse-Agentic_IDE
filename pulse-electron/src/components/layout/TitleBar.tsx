/**
 * TitleBar - Custom Frameless Window Title Bar
 *
 * Provides window controls (minimize, maximize, close) and app title.
 * Uses -webkit-app-region for drag behavior.
 * Issue 5: Added functional dropdown menus with Settings option.
 */

import { useState, useRef, useEffect } from 'react';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { useUIStore } from '@/stores/uiStore';
import { useEditorStore } from '@/stores/editorStore';
import { PulseLogo } from '@/components/common/PulseLogo';

export function TitleBar() {
  const { workspaceName } = useWorkspaceStore();
  const { isMaximized } = useUIStore();
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const handleMinimize = () => {
    window.pulseAPI.window.minimize();
  };

  const handleMaximize = () => {
    window.pulseAPI.window.maximize();
  };

  const handleClose = () => {
    window.pulseAPI.window.close();
  };

  const closeMenu = () => setOpenMenu(null);

  return (
    <div className="h-titlebar bg-pulse-bg-secondary border-b border-pulse-border flex items-center justify-between select-none">
      {/* Left: App Icon and Menu */}
      <div className="flex items-center h-full px-2 titlebar-drag">
        <div className="w-6 h-6 mr-2 titlebar-no-drag flex items-center justify-center">
          <PulseLogo size={60} />
        </div>

        {/* Menu Items - Issue 5: Functional dropdown menus */}
        <div className="hidden sm:flex items-center titlebar-no-drag">
          <MenuDropdown
            label="File"
            isOpen={openMenu === 'file'}
            onToggle={() => setOpenMenu(openMenu === 'file' ? null : 'file')}
            onClose={closeMenu}
          >
            <FileMenuItems onClose={closeMenu} />
          </MenuDropdown>
          <MenuDropdown
            label="Edit"
            isOpen={openMenu === 'edit'}
            onToggle={() => setOpenMenu(openMenu === 'edit' ? null : 'edit')}
            onClose={closeMenu}
          >
            <EditMenuItems onClose={closeMenu} />
          </MenuDropdown>
          <MenuDropdown
            label="View"
            isOpen={openMenu === 'view'}
            onToggle={() => setOpenMenu(openMenu === 'view' ? null : 'view')}
            onClose={closeMenu}
          >
            <ViewMenuItems onClose={closeMenu} />
          </MenuDropdown>
          {/* Settings - Direct click, no dropdown (Issue 3) */}
          <SettingsButton />
          <MenuDropdown
            label="Help"
            isOpen={openMenu === 'help'}
            onToggle={() => setOpenMenu(openMenu === 'help' ? null : 'help')}
            onClose={closeMenu}
          >
            <HelpMenuItems onClose={closeMenu} />
          </MenuDropdown>
        </div>
      </div>

      {/* Center: Window Title */}
      <div className="flex-1 flex items-center justify-center titlebar-drag">
        <span className="text-xs text-pulse-fg-muted truncate max-w-md">
          {workspaceName ? `${workspaceName} - Pulse IDE` : 'Pulse IDE'}
        </span>
      </div>

      {/* Right: Window Controls */}
      <div className="flex items-center h-full titlebar-no-drag">
        <WindowButton onClick={handleMinimize} title="Minimize">
          <MinimizeIcon />
        </WindowButton>
        <WindowButton onClick={handleMaximize} title={isMaximized ? 'Restore' : 'Maximize'}>
          {isMaximized ? <RestoreIcon /> : <MaximizeIcon />}
        </WindowButton>
        <WindowButton onClick={handleClose} title="Close" isClose>
          <CloseIcon />
        </WindowButton>
      </div>
    </div>
  );
}

// ============================================================================
// Menu Dropdown Component
// ============================================================================

interface MenuDropdownProps {
  label: string;
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
  children: React.ReactNode;
}

function MenuDropdown({ label, isOpen, onToggle, onClose, children }: MenuDropdownProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={onToggle}
        className={`px-2 py-1 text-xs transition-colors rounded ${
          isOpen
            ? 'bg-pulse-bg-tertiary text-pulse-fg'
            : 'text-pulse-fg-muted hover:text-pulse-fg hover:bg-pulse-bg-tertiary'
        }`}
      >
        {label}
      </button>
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 min-w-[200px] bg-pulse-bg-secondary border border-pulse-border rounded-md shadow-lg z-50 py-1">
          {children}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Menu Items
// ============================================================================

interface MenuItemProps {
  label: string;
  shortcut?: string;
  onClick: () => void;
  disabled?: boolean;
}

function MenuItem({ label, shortcut, onClick, disabled }: MenuItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full px-3 py-1.5 text-xs flex items-center justify-between ${
        disabled
          ? 'text-pulse-fg-muted cursor-not-allowed'
          : 'text-pulse-fg hover:bg-pulse-bg-tertiary'
      }`}
    >
      <span>{label}</span>
      {shortcut && (
        <span className="text-pulse-fg-muted ml-4">{shortcut}</span>
      )}
    </button>
  );
}

function MenuDivider() {
  return <div className="my-1 border-t border-pulse-border" />;
}

// ============================================================================
// File Menu Items
// ============================================================================

function FileMenuItems({ onClose }: { onClose: () => void }) {
  const handleOpenFolder = async () => {
    try {
      await window.pulseAPI.workspace.openFolder();
    } catch (error) {
      console.error('Failed to open folder:', error);
    }
    onClose();
  };

  const handleOpenFile = async () => {
    try {
      await window.pulseAPI.workspace.openFile();
    } catch (error) {
      console.error('Failed to open file:', error);
    }
    onClose();
  };

  const handleSave = async () => {
    const { activeFilePath, saveFile } = useEditorStore.getState();
    if (activeFilePath && activeFilePath !== '__settings__') {
      try {
        await saveFile(activeFilePath);
      } catch (error) {
        console.error('Failed to save file:', error);
      }
    }
    onClose();
  };

  const handleExit = () => {
    window.pulseAPI.window.close();
    onClose();
  };

  return (
    <>
      <MenuItem label="Open Folder..." shortcut="Ctrl+K" onClick={handleOpenFolder} />
      <MenuItem label="Open File..." shortcut="Ctrl+O" onClick={handleOpenFile} />
      <MenuDivider />
      <MenuItem label="Save" shortcut="Ctrl+S" onClick={handleSave} />
      <MenuItem label="Save All" shortcut="Ctrl+Shift+S" onClick={handleSave} />
      <MenuDivider />
      <MenuItem label="Exit" shortcut="Alt+F4" onClick={handleExit} />
    </>
  );
}

// ============================================================================
// Edit Menu Items
// ============================================================================

function EditMenuItems({ onClose }: { onClose: () => void }) {
  const handleUndo = () => {
    document.execCommand('undo');
    onClose();
  };

  const handleRedo = () => {
    document.execCommand('redo');
    onClose();
  };

  const handleCut = () => {
    document.execCommand('cut');
    onClose();
  };

  const handleCopy = () => {
    document.execCommand('copy');
    onClose();
  };

  const handlePaste = () => {
    document.execCommand('paste');
    onClose();
  };

  return (
    <>
      <MenuItem label="Undo" shortcut="Ctrl+Z" onClick={handleUndo} />
      <MenuItem label="Redo" shortcut="Ctrl+Y" onClick={handleRedo} />
      <MenuDivider />
      <MenuItem label="Cut" shortcut="Ctrl+X" onClick={handleCut} />
      <MenuItem label="Copy" shortcut="Ctrl+C" onClick={handleCopy} />
      <MenuItem label="Paste" shortcut="Ctrl+V" onClick={handlePaste} />
    </>
  );
}

// ============================================================================
// View Menu Items
// ============================================================================

function ViewMenuItems({ onClose }: { onClose: () => void }) {
  const { toggleSidebar, toggleAgentPanel, toggleTerminal, sidebarVisible, agentPanelVisible, terminalVisible } = useUIStore();

  return (
    <>
      <MenuItem
        label={sidebarVisible ? '✓ Sidebar' : '  Sidebar'}
        shortcut="Ctrl+B"
        onClick={() => { toggleSidebar(); onClose(); }}
      />
      <MenuItem
        label={agentPanelVisible ? '✓ Agent Panel' : '  Agent Panel'}
        shortcut="Ctrl+Shift+A"
        onClick={() => { toggleAgentPanel(); onClose(); }}
      />
      <MenuItem
        label={terminalVisible ? '✓ Terminal' : '  Terminal'}
        shortcut="Ctrl+`"
        onClick={() => { toggleTerminal(); onClose(); }}
      />
    </>
  );
}

// ============================================================================
// Settings Button - Direct click, no dropdown (Issue 3)
// ============================================================================

function SettingsButton() {
  const handleOpenSettings = () => {
    const { openFile, setActiveFile, tabs } = useEditorStore.getState();
    // Check if settings tab exists
    const settingsTab = tabs.find(t => t.path === '__settings__');
    if (settingsTab) {
      setActiveFile('__settings__');
    } else {
      openFile('__settings__', '');
    }
  };

  return (
    <button
      onClick={handleOpenSettings}
      className="px-2 py-1 text-xs transition-colors rounded text-pulse-fg-muted hover:text-pulse-fg hover:bg-pulse-bg-tertiary"
    >
      Settings
    </button>
  );
}

// ============================================================================
// Help Menu Items
// ============================================================================

function HelpMenuItems({ onClose }: { onClose: () => void }) {
  const handleAbout = () => {
    // Show about dialog (could be a modal in future)
    alert('Pulse IDE v2.6.0\nAgentic AI IDE for PLC Coding');
    onClose();
  };

  const handleDocumentation = async () => {
    // Open documentation using shell API
    try {
      await window.pulseAPI.shell.openExternal('https://github.com/pulse-ide/docs');
    } catch (error) {
      console.error('Failed to open documentation:', error);
    }
    onClose();
  };

  return (
    <>
      <MenuItem label="Documentation" onClick={handleDocumentation} />
      <MenuDivider />
      <MenuItem label="About Pulse IDE" onClick={handleAbout} />
    </>
  );
}

// ============================================================================
// Window Buttons
// ============================================================================

interface WindowButtonProps {
  onClick: () => void;
  title: string;
  isClose?: boolean;
  children: React.ReactNode;
}

function WindowButton({ onClick, title, isClose, children }: WindowButtonProps) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`w-12 h-titlebar flex items-center justify-center transition-colors ${
        isClose
          ? 'hover:bg-red-600 hover:text-white'
          : 'hover:bg-pulse-bg-tertiary'
      }`}
    >
      {children}
    </button>
  );
}

// ============================================================================
// Icons
// ============================================================================

function MinimizeIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
      <rect x="0" y="4" width="10" height="1" />
    </svg>
  );
}

function MaximizeIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor">
      <rect x="0.5" y="0.5" width="9" height="9" strokeWidth="1" />
    </svg>
  );
}

function RestoreIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor">
      <rect x="2.5" y="0.5" width="7" height="7" strokeWidth="1" />
      <path d="M0.5 2.5v7h7" strokeWidth="1" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
      <path d="M1 1l8 8M9 1l-8 8" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}
