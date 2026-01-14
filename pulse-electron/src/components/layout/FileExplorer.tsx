/**
 * FileExplorer - File Tree View
 *
 * Displays the workspace file tree with expand/collapse functionality.
 */

import React, { useCallback, useState, useRef, useEffect } from 'react';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { useEditorStore } from '@/stores/editorStore';
import { useUIStore } from '@/stores/uiStore';
import type { FileTreeNode } from '@/types/editor';

// ============================================================================
// Context Menu Types
// ============================================================================

interface ContextMenuState {
  isOpen: boolean;
  x: number;
  y: number;
  node: FileTreeNode | null;
}

interface ContextMenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  divider?: boolean;
  disabled?: boolean;
  destructive?: boolean;
}

export function FileExplorer() {
  const {
    projectRoot,
    workspaceName,
    fileTree,
    isLoadingTree,
    expandedFolders,
    selectedPath,
    toggleFolder,
    selectPath,
    refreshTree,
    collapseAllFolders,
  } = useWorkspaceStore();

  const { openFile } = useEditorStore();

  // Context menu state
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    isOpen: false,
    x: 0,
    y: 0,
    node: null,
  });

  // Rename state
  const [renamingPath, setRenamingPath] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const handleOpenWorkspace = useCallback(async () => {
    const path = await window.pulseAPI.workspace.openFolder();
    if (path) {
      useWorkspaceStore.getState().openWorkspace(path);
    }
  }, []);

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      if (contextMenu.isOpen) {
        setContextMenu(prev => ({ ...prev, isOpen: false }));
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [contextMenu.isOpen]);

  // Context menu handler
  const handleContextMenu = useCallback((e: React.MouseEvent, node: FileTreeNode) => {
    e.preventDefault();
    e.stopPropagation();
    selectPath(node.path);
    setContextMenu({
      isOpen: true,
      x: e.clientX,
      y: e.clientY,
      node,
    });
  }, [selectPath]);

  // Context menu actions
  const handleNewFile = useCallback(async (parentPath: string) => {
    const name = prompt('Enter file name:');
    if (!name?.trim()) return;

    const sep = window.pulseAPI.platform === 'win32' ? '\\' : '/';
    const newPath = `${parentPath}${sep}${name}`;

    try {
      await window.pulseAPI.fs.writeFile(newPath, '');
      refreshTree();
      // Open the new file
      setTimeout(async () => {
        const content = await window.pulseAPI.fs.readFile(newPath);
        useEditorStore.getState().openFile(newPath, content, { isPreview: false });
      }, 100);
    } catch (error) {
      useUIStore.getState().addNotification({
        type: 'error',
        title: 'Failed to create file',
        message: (error as Error).message,
      });
    }
  }, [refreshTree]);

  const handleNewFolder = useCallback(async (parentPath: string) => {
    const name = prompt('Enter folder name:');
    if (!name?.trim()) return;

    const sep = window.pulseAPI.platform === 'win32' ? '\\' : '/';
    const newPath = `${parentPath}${sep}${name}`;

    try {
      await window.pulseAPI.fs.mkdir(newPath);
      refreshTree();
    } catch (error) {
      useUIStore.getState().addNotification({
        type: 'error',
        title: 'Failed to create folder',
        message: (error as Error).message,
      });
    }
  }, [refreshTree]);

  const handleRename = useCallback((path: string, currentName: string) => {
    setRenamingPath(path);
    setRenameValue(currentName);
  }, []);

  const handleRenameSubmit = useCallback(async (oldPath: string, newName: string) => {
    if (!newName.trim() || newName === oldPath.split(/[\\/]/).pop()) {
      setRenamingPath(null);
      setRenameValue('');
      return;
    }

    const parts = oldPath.split(/[\\/]/);
    parts.pop();
    const sep = window.pulseAPI.platform === 'win32' ? '\\' : '/';
    const newPath = parts.join(sep) + sep + newName;

    try {
      await window.pulseAPI.fs.rename(oldPath, newPath);
      refreshTree();
    } catch (error) {
      useUIStore.getState().addNotification({
        type: 'error',
        title: 'Failed to rename',
        message: (error as Error).message,
      });
    }

    setRenamingPath(null);
    setRenameValue('');
  }, [refreshTree]);

  const handleDelete = useCallback(async (path: string, isDirectory: boolean) => {
    const name = path.split(/[\\/]/).pop();
    const confirmed = confirm(
      `Are you sure you want to delete "${name}"?${isDirectory ? ' This will delete all contents.' : ''}`
    );
    if (!confirmed) return;

    try {
      await window.pulseAPI.fs.remove(path);
      refreshTree();
      // Close the file if it's open
      useEditorStore.getState().closeFile(path);
    } catch (error) {
      useUIStore.getState().addNotification({
        type: 'error',
        title: 'Failed to delete',
        message: (error as Error).message,
      });
    }
  }, [refreshTree]);

  const handleCopyPath = useCallback((path: string) => {
    navigator.clipboard.writeText(path);
    useUIStore.getState().addNotification({
      type: 'success',
      title: 'Path copied',
      message: 'Path copied to clipboard',
    });
  }, []);

  const handleRevealInExplorer = useCallback((path: string) => {
    window.pulseAPI.workspace.revealInExplorer(path);
  }, []);

  const handleFileClick = useCallback(
    async (node: FileTreeNode) => {
      selectPath(node.path);

      if (node.isDirectory) {
        toggleFolder(node.path);
      } else {
        // Open file in editor
        try {
          const content = await window.pulseAPI.fs.readFile(node.path);
          openFile(node.path, content);
        } catch (error) {
          console.error('Failed to open file:', error);
          // Show error notification to user
          useUIStore.getState().addNotification({
            type: 'error',
            title: 'Failed to open file',
            message: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      }
    },
    [selectPath, toggleFolder, openFile]
  );

  const handleFileDoubleClick = useCallback(
    async (node: FileTreeNode) => {
      if (!node.isDirectory) {
        // Open as permanent tab (or promote if already open)
        try {
          const content = await window.pulseAPI.fs.readFile(node.path);
          openFile(node.path, content, { isPreview: false });
        } catch (error) {
          console.error('Failed to open file:', error);
        }
      }
    },
    [openFile]
  );

  // No workspace open
  if (!projectRoot) {
    return (
      <div className="p-4 flex flex-col items-center justify-center h-full">
        <p className="text-sm text-pulse-fg-muted mb-4 text-center">
          No folder opened
        </p>
        <button
          onClick={handleOpenWorkspace}
          className="px-4 py-2 bg-pulse-primary text-white rounded text-sm hover:bg-pulse-primary-hover transition-colors"
        >
          Open Folder
        </button>
      </div>
    );
  }

  // Loading
  if (isLoadingTree) {
    return (
      <div className="p-4 flex items-center justify-center">
        <span className="text-sm text-pulse-fg-muted">Loading...</span>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Workspace Header with Toolbar */}
      <div className="flex-shrink-0">
        <div className="px-2 py-1 flex items-center justify-between hover:bg-pulse-bg-tertiary">
          <div className="flex items-center cursor-pointer">
            <ChevronIcon isExpanded={true} />
            <span className="ml-1 text-xs font-semibold uppercase tracking-wide truncate">
              {workspaceName}
            </span>
          </div>
          {/* Toolbar Buttons */}
          <FileExplorerToolbar
            projectRoot={projectRoot}
            selectedPath={selectedPath}
            onRefresh={refreshTree}
            onCollapseAll={collapseAllFolders}
          />
        </div>
      </div>

      {/* File Tree */}
      <div className="flex-1 overflow-auto px-1">
        {fileTree.map((node) => (
          <FileTreeItem
            key={node.path}
            node={node}
            depth={0}
            selectedPath={selectedPath}
            expandedFolders={expandedFolders}
            onClick={handleFileClick}
            onDoubleClick={handleFileDoubleClick}
            onContextMenu={handleContextMenu}
          />
        ))}
      </div>

      {/* Context Menu Portal */}
      {contextMenu.isOpen && contextMenu.node && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          node={contextMenu.node}
          onNewFile={() => handleNewFile(contextMenu.node!.isDirectory ? contextMenu.node!.path : contextMenu.node!.path.split(/[\\\/]/).slice(0, -1).join(window.pulseAPI.platform === 'win32' ? '\\' : '/'))}
          onNewFolder={() => handleNewFolder(contextMenu.node!.isDirectory ? contextMenu.node!.path : contextMenu.node!.path.split(/[\\\/]/).slice(0, -1).join(window.pulseAPI.platform === 'win32' ? '\\' : '/'))}
          onRename={() => handleRename(contextMenu.node!.path, contextMenu.node!.name)}
          onDelete={() => handleDelete(contextMenu.node!.path, contextMenu.node!.isDirectory)}
          onCopyPath={() => handleCopyPath(contextMenu.node!.path)}
          onRevealInExplorer={() => handleRevealInExplorer(contextMenu.node!.path)}
          onClose={() => setContextMenu(prev => ({ ...prev, isOpen: false }))}
        />
      )}
    </div>
  );
}

// ============================================================================
// File Explorer Toolbar
// ============================================================================

interface FileExplorerToolbarProps {
  projectRoot: string | null;
  selectedPath: string | null;
  onRefresh: () => void;
  onCollapseAll: () => void;
}

function FileExplorerToolbar({
  projectRoot,
  selectedPath,
  onRefresh,
  onCollapseAll,
}: FileExplorerToolbarProps) {
  const [isCreating, setIsCreating] = useState<'file' | 'folder' | null>(null);
  const [newName, setNewName] = useState('');
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Focus input when creating mode changes
  React.useEffect(() => {
    if (isCreating && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isCreating]);

  const getTargetDirectory = async () => {
    if (!projectRoot) return null;
    if (!selectedPath) return projectRoot;

    // Check if selected path is a directory
    try {
      const stat = await window.pulseAPI.fs.stat(selectedPath);
      if (stat.isDirectory) {
        return selectedPath;
      } else {
        // Get parent directory
        const parts = selectedPath.split(/[\\/]/);
        parts.pop();
        return parts.join(window.pulseAPI.platform === 'win32' ? '\\' : '/') || projectRoot;
      }
    } catch {
      return projectRoot;
    }
  };

  const handleCreateFile = async () => {
    if (!newName.trim()) {
      setIsCreating(null);
      setNewName('');
      return;
    }

    const targetDir = await getTargetDirectory();
    if (!targetDir) return;

    // Use proper path separator
    const sep = window.pulseAPI.platform === 'win32' ? '\\' : '/';
    const newPath = `${targetDir}${sep}${newName}`;

    console.log('[FileExplorer] Creating file:', newPath);

    try {
      await window.pulseAPI.fs.writeFile(newPath, '');
      console.log('[FileExplorer] File created successfully');
      onRefresh();
      // Open the new file
      setTimeout(async () => {
        try {
          const content = await window.pulseAPI.fs.readFile(newPath);
          useEditorStore.getState().openFile(newPath, content, { isPreview: false });
        } catch (e) {
          console.error('[FileExplorer] Failed to open new file:', e);
        }
      }, 100);
    } catch (error) {
      console.error('[FileExplorer] Failed to create file:', error);
      useUIStore.getState().addNotification({
        type: 'error',
        title: 'Failed to create file',
        message: (error as Error).message,
      });
    }

    setNewName('');
    setIsCreating(null);
  };

  const handleCreateFolder = async () => {
    if (!newName.trim()) {
      setIsCreating(null);
      setNewName('');
      return;
    }

    const targetDir = await getTargetDirectory();
    if (!targetDir) return;

    // Use proper path separator
    const sep = window.pulseAPI.platform === 'win32' ? '\\' : '/';
    const newPath = `${targetDir}${sep}${newName}`;

    console.log('[FileExplorer] Creating folder:', newPath);

    try {
      await window.pulseAPI.fs.mkdir(newPath);
      console.log('[FileExplorer] Folder created successfully');
      onRefresh();
    } catch (error) {
      console.error('[FileExplorer] Failed to create folder:', error);
      useUIStore.getState().addNotification({
        type: 'error',
        title: 'Failed to create folder',
        message: (error as Error).message,
      });
    }

    setNewName('');
    setIsCreating(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    e.stopPropagation();
    if (e.key === 'Enter') {
      e.preventDefault();
      if (isCreating === 'file') handleCreateFile();
      else if (isCreating === 'folder') handleCreateFolder();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setNewName('');
      setIsCreating(null);
    }
  };

  const handleBlur = () => {
    // Delay to allow click events to fire first
    setTimeout(() => {
      if (!newName.trim()) {
        setIsCreating(null);
        setNewName('');
      }
    }, 150);
  };

  return (
    <div className="relative flex items-center gap-0.5">
      <ToolbarButton
        icon={<NewFileIcon />}
        title="New File"
        onClick={() => {
          setIsCreating('file');
          setNewName('');
        }}
      />
      <ToolbarButton
        icon={<NewFolderIcon />}
        title="New Folder"
        onClick={() => {
          setIsCreating('folder');
          setNewName('');
        }}
      />
      <ToolbarButton
        icon={<RefreshIcon />}
        title="Refresh Explorer"
        onClick={onRefresh}
      />
      <ToolbarButton
        icon={<CollapseAllIcon />}
        title="Collapse Folders"
        onClick={onCollapseAll}
      />

      {/* Inline input for new file/folder name - positioned below the header */}
      {isCreating && (
        <div className="fixed left-0 right-0 z-50 px-2" style={{ top: 'calc(var(--titlebar-height, 36px) + 36px + 26px)' }}>
          <div className="bg-pulse-bg-secondary border border-pulse-primary rounded shadow-lg p-2">
            <div className="text-xs text-pulse-fg-muted mb-1">
              {isCreating === 'file' ? 'New File' : 'New Folder'}
            </div>
            <input
              ref={inputRef}
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleBlur}
              placeholder={isCreating === 'file' ? 'filename.ext' : 'folder name'}
              className="w-full px-2 py-1 text-sm bg-pulse-input border border-pulse-border rounded focus:outline-none focus:border-pulse-primary"
            />
            <div className="flex justify-end gap-2 mt-2">
              <button
                onClick={() => {
                  setNewName('');
                  setIsCreating(null);
                }}
                className="px-2 py-1 text-xs text-pulse-fg-muted hover:text-pulse-fg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (isCreating === 'file') handleCreateFile();
                  else handleCreateFolder();
                }}
                disabled={!newName.trim()}
                className="px-2 py-1 text-xs bg-pulse-primary text-white rounded hover:bg-pulse-primary-hover disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ToolbarButton({
  icon,
  title,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="p-1 rounded hover:bg-pulse-bg-tertiary text-pulse-fg-muted hover:text-pulse-fg transition-colors"
    >
      <div className="w-4 h-4">{icon}</div>
    </button>
  );
}

function NewFileIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M9.5 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V4.5L9.5 1zM9 2l3 3H9V2zM4 14V2h4v4h4v8H4z" />
      <path d="M7 7h2v2h2v1H9v2H8v-2H6V9h2V7z" />
    </svg>
  );
}

function NewFolderIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M14 4H9l-1-1H3a1 1 0 00-1 1v9a1 1 0 001 1h11a1 1 0 001-1V5a1 1 0 00-1-1zm-4 6H8v2H7v-2H5V9h2V7h1v2h2v1z" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M13.5 2v4h-4l1.5-1.5a4.5 4.5 0 10.6 5.8l.9.6a5.5 5.5 0 11-.8-7.4L13.5 2z" />
    </svg>
  );
}

function CollapseAllIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M9 9H4v1h5V9z" />
      <path d="M9 5H4v1h5V5z" />
      <path d="M14 1H3L2 2v12l1 1h11l1-1V2l-1-1zM3 14V2h11v12H3z" />
    </svg>
  );
}

// ============================================================================
// FileTreeItem
// ============================================================================

interface FileTreeItemProps {
  node: FileTreeNode;
  depth: number;
  selectedPath: string | null;
  expandedFolders: Set<string>;
  onClick: (node: FileTreeNode) => void;
  onDoubleClick: (node: FileTreeNode) => void;
  onContextMenu?: (e: React.MouseEvent, node: FileTreeNode) => void;
}

function FileTreeItem({
  node,
  depth,
  selectedPath,
  expandedFolders,
  onClick,
  onDoubleClick,
  onContextMenu,
}: FileTreeItemProps) {
  const isExpanded = expandedFolders.has(node.path);
  const isSelected = selectedPath === node.path;
  const paddingLeft = 8 + depth * 12;

  return (
    <>
      <div
        className={`
          flex items-center py-0.5 px-1 cursor-pointer rounded-sm
          ${isSelected ? 'bg-pulse-selection' : 'hover:bg-pulse-bg-tertiary'}
        `}
        style={{ paddingLeft }}
        onClick={() => onClick(node)}
        onDoubleClick={() => onDoubleClick(node)}
        onContextMenu={(e) => onContextMenu?.(e, node)}
      >
        {/* Expand/Collapse or Spacer */}
        {node.isDirectory ? (
          <ChevronIcon isExpanded={isExpanded} />
        ) : (
          <div className="w-4" />
        )}

        {/* Icon */}
        <div className="w-4 h-4 mr-1.5 flex-shrink-0">
          {node.isDirectory ? (
            <FolderIcon isOpen={isExpanded} name={node.name} />
          ) : (
            <FileIcon filename={node.name} />
          )}
        </div>

        {/* Name */}
        <span className="text-sm truncate">{node.name}</span>
      </div>

      {/* Children */}
      {node.isDirectory && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              expandedFolders={expandedFolders}
              onClick={onClick}
              onDoubleClick={onDoubleClick}
              onContextMenu={onContextMenu}
            />
          ))}
        </div>
      )}
    </>
  );
}

// ============================================================================
// Icons
// ============================================================================

function ChevronIcon({ isExpanded }: { isExpanded: boolean }) {
  return (
    <svg
      className={`w-4 h-4 text-pulse-fg-muted transition-transform ${isExpanded ? 'rotate-90' : ''
        }`}
      viewBox="0 0 16 16"
      fill="currentColor"
    >
      <path d="M6 4l4 4-4 4z" />
    </svg>
  );
}

function FolderIcon({ isOpen, name }: { isOpen: boolean; name?: string }) {
  // Special folder colors
  const folderColors: Record<string, string> = {
    src: '#42A5F5',
    assets: '#7E57C2',
    components: '#26A69A',
    hooks: '#42A5F5',
    stores: '#EF5350',
    styles: '#EC407A',
    types: '#5C6BC0',
    utils: '#FFA726',
    lib: '#AB47BC',
    tests: '#66BB6A',
    __tests__: '#66BB6A',
    node_modules: '#78909C',
    dist: '#78909C',
    build: '#78909C',
    public: '#29B6F6',
    config: '#8D6E63',
    docs: '#26A69A',
    scripts: '#FFA726',
  };

  const color = name ? folderColors[name.toLowerCase()] || '#FFA000' : '#FFA000';

  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      {isOpen ? (
        <>
          <path
            d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z"
            fill={color}
            opacity="0.3"
          />
          <path
            d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V6h5.17l2 2H20v10z"
            fill={color}
          />
        </>
      ) : (
        <path
          d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"
          fill={color}
        />
      )}
    </svg>
  );
}

function FileIcon({ filename }: { filename: string }) {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const name = filename.toLowerCase();

  // Special file icons
  if (name === 'package.json') return <PackageJsonIcon />;
  if (name === 'tsconfig.json') return <TsConfigIcon />;
  if (name === '.gitignore') return <GitIcon />;
  if (name === '.env' || name.startsWith('.env.')) return <EnvIcon />;
  if (name === 'readme.md') return <ReadmeIcon />;
  if (name === 'dockerfile') return <DockerIcon />;

  // Extension-based icons
  switch (ext) {
    case 'ts':
      return <TypeScriptIcon />;
    case 'tsx':
      return <TypeScriptReactIcon />;
    case 'js':
      return <JavaScriptIcon />;
    case 'jsx':
      return <JavaScriptReactIcon />;
    case 'py':
      return <PythonIcon />;
    case 'st':
      return <StructuredTextIcon />;
    case 'json':
      return <JsonIcon />;
    case 'css':
      return <CssIcon />;
    case 'scss':
    case 'sass':
      return <SassIcon />;
    case 'html':
      return <HtmlIcon />;
    case 'md':
    case 'mdx':
      return <MarkdownIcon />;
    case 'svg':
      return <SvgIcon />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'webp':
      return <ImageIcon />;
    case 'yaml':
    case 'yml':
      return <YamlIcon />;
    default:
      return <DefaultFileIcon />;
  }
}

// ============================================================================
// Individual File Icons (Material Icon Theme Style)
// ============================================================================

function TypeScriptIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#3178C6" />
      <path
        d="M15.5 11v1.5h-2v6h-1.5v-6h-2V11h5.5zm2.5 0v7.5h-1.5v-3h-1v-1.5h1V11h1.5z"
        fill="white"
      />
    </svg>
  );
}

function TypeScriptReactIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#3178C6" />
      <circle cx="12" cy="12" r="2" fill="#61DAFB" />
      <ellipse cx="12" cy="12" rx="6" ry="2.5" fill="none" stroke="#61DAFB" strokeWidth="0.8" />
      <ellipse cx="12" cy="12" rx="6" ry="2.5" fill="none" stroke="#61DAFB" strokeWidth="0.8" transform="rotate(60 12 12)" />
      <ellipse cx="12" cy="12" rx="6" ry="2.5" fill="none" stroke="#61DAFB" strokeWidth="0.8" transform="rotate(120 12 12)" />
    </svg>
  );
}

function JavaScriptIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#F7DF1E" />
      <path
        d="M8 17.5v-5.7h1.3v4.7c0 .5.4.8.9.8s.9-.3.9-.8v-4.7h1.3v5.7c0 1.1-.9 1.8-2.2 1.8s-2.2-.7-2.2-1.8zm8.5-1.7c0 1.1-.8 2-2.4 2-1.3 0-2.1-.6-2.4-1.5l1.1-.5c.2.5.6.8 1.2.8.6 0 1-.3 1-.8s-.3-.7-1.2-1l-.4-.2c-1.1-.4-1.7-1-1.7-2.1 0-1.2.9-2 2.2-2 1 0 1.8.5 2.1 1.3l-1.1.5c-.2-.4-.5-.6-1-.6-.5 0-.8.3-.8.7 0 .5.3.7 1 .9l.4.2c1.3.5 2 1.1 2 2.3z"
        fill="black"
      />
    </svg>
  );
}

function JavaScriptReactIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#20232A" />
      <circle cx="12" cy="12" r="2" fill="#61DAFB" />
      <ellipse cx="12" cy="12" rx="6" ry="2.5" fill="none" stroke="#61DAFB" strokeWidth="0.8" />
      <ellipse cx="12" cy="12" rx="6" ry="2.5" fill="none" stroke="#61DAFB" strokeWidth="0.8" transform="rotate(60 12 12)" />
      <ellipse cx="12" cy="12" rx="6" ry="2.5" fill="none" stroke="#61DAFB" strokeWidth="0.8" transform="rotate(120 12 12)" />
    </svg>
  );
}

function PythonIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <path d="M12 2C6.48 2 6 4.48 6 7v2h6v1H5c-2.21 0-3 1.79-3 4s.79 4 3 4h1v-3c0-1.1.9-2 2-2h6c1.1 0 2-.9 2-2V7c0-2.52-.48-5-6-5z" fill="#3776AB" />
      <path d="M12 22c5.52 0 6-2.48 6-5v-2h-6v-1h7c2.21 0 3-1.79 3-4s-.79-4-3-4h-1v3c0 1.1-.9 2-2 2H8c-1.1 0-2 .9-2 2v5c0 2.52.48 5 6 5z" fill="#FFD43B" />
      <circle cx="8.5" cy="5" r="1" fill="#FFD43B" />
      <circle cx="15.5" cy="19" r="1" fill="#3776AB" />
    </svg>
  );
}

function StructuredTextIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#8E44AD" />
      <text x="12" y="16" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">ST</text>
    </svg>
  );
}

function JsonIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#FBC02D" />
      <text x="12" y="15" textAnchor="middle" fill="#333" fontSize="7" fontWeight="bold">{ }</text>
    </svg>
  );
}

function CssIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#42A5F5" />
      <path d="M5 5h14l-1.5 14L12 21l-5.5-2L5 5z" fill="#1565C0" />
      <text x="12" y="14" textAnchor="middle" fill="white" fontSize="6" fontWeight="bold">CSS</text>
    </svg>
  );
}

function SassIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#CD6799" />
      <text x="12" y="15" textAnchor="middle" fill="white" fontSize="6" fontWeight="bold">SCSS</text>
    </svg>
  );
}

function HtmlIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#E44D26" />
      <path d="M5 5h14l-1.5 14L12 21l-5.5-2L5 5z" fill="#F16529" />
      <text x="12" y="14" textAnchor="middle" fill="white" fontSize="5" fontWeight="bold">HTML</text>
    </svg>
  );
}

function MarkdownIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#42A5F5" />
      <path d="M5 8v8h2l2-3 2 3h2V8h-2v4l-2-2.5L7 12V8H5zm10 0v8h2v-4l2 4h2V8h-2v4l-2-4h-2z" fill="white" />
    </svg>
  );
}

function SvgIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#FFB300" />
      <text x="12" y="15" textAnchor="middle" fill="white" fontSize="6" fontWeight="bold">SVG</text>
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#4CAF50" />
      <circle cx="9" cy="9" r="2" fill="white" />
      <path d="M4 18l4-5 3 4 4-5 5 6H4z" fill="white" />
    </svg>
  );
}

function YamlIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#CB171E" />
      <text x="12" y="15" textAnchor="middle" fill="white" fontSize="5" fontWeight="bold">YAML</text>
    </svg>
  );
}

function PackageJsonIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#CB3837" />
      <text x="12" y="15" textAnchor="middle" fill="white" fontSize="5" fontWeight="bold">npm</text>
    </svg>
  );
}

function TsConfigIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#3178C6" />
      <path d="M7 8h10M7 12h8M7 16h6" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function GitIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#F05032" />
      <path d="M12 6v12M8 10h8" stroke="white" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function EnvIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#ECD53F" />
      <text x="12" y="15" textAnchor="middle" fill="#333" fontSize="5" fontWeight="bold">.env</text>
    </svg>
  );
}

function ReadmeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#42A5F5" />
      <path d="M7 7h10M7 11h10M7 15h6" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function DockerIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-full h-full">
      <rect x="2" y="2" width="20" height="20" rx="2" fill="#2496ED" />
      <path d="M4 12h3v3H4v-3zm4 0h3v3H8v-3zm4 0h3v3h-3v-3zm-4-4h3v3H8V8zm4 0h3v3h-3V8z" fill="white" />
    </svg>
  );
}

function DefaultFileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-full h-full text-pulse-fg-muted">
      <path d="M6 2c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6H6zm7 1.5L18.5 9H13V3.5z" />
    </svg>
  );
}

// ============================================================================
// Context Menu Component
// ============================================================================

interface ContextMenuProps {
  x: number;
  y: number;
  node: FileTreeNode;
  onNewFile: () => void;
  onNewFolder: () => void;
  onRename: () => void;
  onDelete: () => void;
  onCopyPath: () => void;
  onRevealInExplorer: () => void;
  onClose: () => void;
}

function ContextMenu({
  x,
  y,
  node,
  onNewFile,
  onNewFolder,
  onRename,
  onDelete,
  onCopyPath,
  onRevealInExplorer,
  onClose,
}: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Adjust position to keep menu within viewport
  const [adjustedPosition, setAdjustedPosition] = useState({ x, y });

  useEffect(() => {
    if (menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let newX = x;
      let newY = y;

      if (x + rect.width > viewportWidth) {
        newX = viewportWidth - rect.width - 8;
      }
      if (y + rect.height > viewportHeight) {
        newY = viewportHeight - rect.height - 8;
      }

      setAdjustedPosition({ x: newX, y: newY });
    }
  }, [x, y]);

  const handleAction = (action: () => void) => {
    action();
    onClose();
  };

  return (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-[180px] bg-pulse-bg-secondary border border-pulse-border rounded shadow-lg py-1"
      style={{ left: adjustedPosition.x, top: adjustedPosition.y }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* New File */}
      <ContextMenuButton
        icon={<NewFileMenuIcon />}
        label="New File"
        onClick={() => handleAction(onNewFile)}
      />
      {/* New Folder */}
      <ContextMenuButton
        icon={<NewFolderMenuIcon />}
        label="New Folder"
        onClick={() => handleAction(onNewFolder)}
      />

      <ContextMenuDivider />

      {/* Rename */}
      <ContextMenuButton
        icon={<RenameIcon />}
        label="Rename"
        shortcut="F2"
        onClick={() => handleAction(onRename)}
      />
      {/* Delete */}
      <ContextMenuButton
        icon={<DeleteIcon />}
        label="Delete"
        shortcut="Del"
        onClick={() => handleAction(onDelete)}
        destructive
      />

      <ContextMenuDivider />

      {/* Copy Path */}
      <ContextMenuButton
        icon={<CopyIcon />}
        label="Copy Path"
        onClick={() => handleAction(onCopyPath)}
      />
      {/* Reveal in Explorer */}
      <ContextMenuButton
        icon={<RevealIcon />}
        label="Reveal in Explorer"
        onClick={() => handleAction(onRevealInExplorer)}
      />
    </div>
  );
}

function ContextMenuButton({
  icon,
  label,
  shortcut,
  onClick,
  destructive,
}: {
  icon: React.ReactNode;
  label: string;
  shortcut?: string;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center px-3 py-1.5 text-sm hover:bg-pulse-selection ${destructive ? 'text-red-400 hover:text-red-300' : 'text-pulse-fg'
        }`}
    >
      <span className="w-4 h-4 mr-2">{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {shortcut && (
        <span className="text-xs text-pulse-fg-muted ml-4">{shortcut}</span>
      )}
    </button>
  );
}

function ContextMenuDivider() {
  return <div className="border-t border-pulse-border my-1" />;
}

// Context Menu Icons
function NewFileMenuIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M9.5 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V4.5L9.5 1zM9 2l3 3H9V2z" />
    </svg>
  );
}

function NewFolderMenuIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M14 4H9l-1-1H3a1 1 0 00-1 1v9a1 1 0 001 1h11a1 1 0 001-1V5a1 1 0 00-1-1z" />
    </svg>
  );
}

function RenameIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M13.23 1h-1.46L3.52 9.25l-.16.22L1 13.59 2.41 15l4.12-2.36.22-.16L15 4.23V2.77L13.23 1zM2.41 13.59l1.51-3 1.45 1.45-2.96 1.55z" />
    </svg>
  );
}

function DeleteIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M10 3h3v1h-1v9l-1 1H5l-1-1V4H3V3h3V2a1 1 0 011-1h2a1 1 0 011 1v1zM9 2H7v1h2V2zM5 4v9h6V4H5z" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M4 4h3v1H4v7h7v-3h1v4H3V4h1zm1-1V2h7v6h-1V4h-5V3h5V2H5v1z" />
    </svg>
  );
}

function RevealIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M14 4H9l-1-1H3a1 1 0 00-1 1v9a1 1 0 001 1h11a1 1 0 001-1V5a1 1 0 00-1-1zm0 9H3V5h5l1 1h5v7z" />
    </svg>
  );
}
