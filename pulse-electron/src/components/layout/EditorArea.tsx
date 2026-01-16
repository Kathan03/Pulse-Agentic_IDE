/**
 * EditorArea - Central Editor Region
 *
 * Contains editor tabs and the Monaco editor or diff view.
 */

import { EditorTabs } from '../editor/EditorTabs';
import { EditorContent } from '../editor/EditorContent';
import { useEditorStore } from '@/stores/editorStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { PulseLogo } from '@/components/common/PulseLogo';


export function EditorArea() {
  const { tabs, activeFilePath } = useEditorStore();
  const { projectRoot } = useWorkspaceStore();

  // No files open - show welcome
  if (tabs.length === 0) {
    return <WelcomeView hasWorkspace={!!projectRoot} />;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Editor Tabs */}
      <EditorTabs />

      {/* Editor Content - min-h-0 fixes flexbox min-height: auto default */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <EditorContent />
      </div>
    </div>
  );
}

// ============================================================================
// Welcome View
// ============================================================================

function WelcomeView({ hasWorkspace }: { hasWorkspace: boolean }) {
  const handleOpenFolder = async () => {
    const path = await window.pulseAPI.workspace.openFolder();
    if (path) {
      useWorkspaceStore.getState().openWorkspace(path);
    }
  };

  const handleOpenFile = async () => {
    const path = await window.pulseAPI.workspace.openFile();
    if (path) {
      try {
        const content = await window.pulseAPI.fs.readFile(path);
        useEditorStore.getState().openFile(path, content);
      } catch (error) {
        console.error('Failed to open file:', error);
      }
    }
  };

  // When workspace is open, show minimal view (just logo and "Pulse")
  if (hasWorkspace) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8">
        <div className="w-32 h-32 mb-8 opacity-30 flex items-center justify-center">
          <PulseLogo size={280} />
        </div>
        <h1 className="text-2xl font-light text-pulse-fg">Pulse</h1>
      </div>
    );
  }

  // When no workspace is open, show full welcome UI
  return (
    <div className="h-full flex flex-col items-center justify-center text-center p-8">
      <div className="w-32 h-32 mb-8 opacity-30 flex items-center justify-center">
        <PulseLogo size={280} />
      </div>

      {/* Title */}
      <h1 className="text-2xl font-light text-pulse-fg mb-8">Pulse</h1>

      {/* Actions */}
      <div className="space-y-3">
        <WelcomeAction
          icon={<FolderIcon />}
          label="Open Folder"
          shortcut="Ctrl+K"
          onClick={handleOpenFolder}
        />
        <WelcomeAction
          icon={<FileIcon />}
          label="Open File"
          shortcut="Ctrl+O"
          onClick={handleOpenFile}
        />
      </div>

      {/* Recent Workspaces */}
      <RecentWorkspaces />
    </div>
  );
}

function WelcomeAction({
  icon,
  label,
  shortcut,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  shortcut: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-64 flex items-center px-4 py-2 bg-pulse-bg-tertiary hover:bg-pulse-input rounded transition-colors"
    >
      <div className="w-5 h-5 mr-3 text-pulse-primary">{icon}</div>
      <span className="flex-1 text-left text-sm">{label}</span>
      <span className="text-xs text-pulse-fg-muted">{shortcut}</span>
    </button>
  );
}

function RecentWorkspaces() {
  const { recentWorkspaces, openWorkspace } = useWorkspaceStore();

  if (recentWorkspaces.length === 0) return null;

  return (
    <div className="mt-8">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-pulse-fg-muted mb-3">
        Recent
      </h2>
      <div className="space-y-1">
        {recentWorkspaces.slice(0, 5).map((path) => {
          const name = path.split(/[\\/]/).pop() || path;
          return (
            <button
              key={path}
              onClick={() => openWorkspace(path)}
              className="w-64 text-left px-4 py-1.5 text-sm text-pulse-primary hover:underline truncate"
              title={path}
            >
              {name}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Icons
// ============================================================================

function FolderIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M1 4a1 1 0 011-1h4l1 1h6a1 1 0 011 1v8a1 1 0 01-1 1H2a1 1 0 01-1-1V4z" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M3 1h7l3 3v11a1 1 0 01-1 1H3a1 1 0 01-1-1V2a1 1 0 011-1zm7 0v3h3" />
    </svg>
  );
}
