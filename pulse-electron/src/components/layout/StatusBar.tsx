/**
 * StatusBar - Bottom Status Strip
 *
 * Displays file info, run status, cursor position, and model info.
 */

import { useState, useEffect } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import { useEditorStore, selectActiveFile } from '@/stores/editorStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { fetchSettings } from '@/services/settingsApi';

export function StatusBar() {
  const { mode, runStatus } = useAgentStore();
  const activeFile = useEditorStore(selectActiveFile);
  const cursorPosition = useEditorStore((s) => s.cursorPosition);
  const { projectRoot } = useWorkspaceStore();
  const [currentModel, setCurrentModel] = useState<string>('');

  // Load current model
  useEffect(() => {
    async function loadModel() {
      try {
        const settings = await fetchSettings();
        setCurrentModel(settings.models.master_agent || 'gpt-5');
      } catch (error) {
        console.error('Failed to load model:', error);
      }
    }
    loadModel();

    // Refresh periodically in case settings change
    const interval = setInterval(loadModel, 10000);
    return () => clearInterval(interval);
  }, []);

  // Format model name for display
  const formatModelName = (model: string) => {
    if (model.startsWith('gpt-5')) return model.replace('gpt-', 'GPT-');
    if (model.startsWith('claude')) return model.replace('claude-', '').replace('-4.5', ' 4.5');
    if (model.startsWith('gemini')) return model.replace('gemini-', 'Gemini ');
    return model;
  };

  return (
    <div className="h-statusbar bg-pulse-primary flex items-center justify-between px-2 text-white text-xs select-none">
      {/* Left Side */}
      <div className="flex items-center space-x-3">
        {/* Run Status */}
        {runStatus !== 'idle' && (
          <StatusItem
            icon={<RunIcon status={runStatus} />}
            label={getRunStatusLabel(runStatus)}
          />
        )}

        {/* Git Branch (placeholder) */}
        {projectRoot && (
          <StatusItem
            icon={<GitBranchIcon />}
            label="main"
          />
        )}
      </div>

      {/* Right Side */}
      <div className="flex items-center space-x-3">
        {/* Current Model */}
        {currentModel && (
          <StatusItem
            icon={<ModelIcon />}
            label={formatModelName(currentModel)}
            title={`Master Agent Model: ${currentModel}`}
          />
        )}

        {/* Agent Mode */}
        <StatusItem
          label={`Mode: ${mode.charAt(0).toUpperCase() + mode.slice(1)}`}
        />

        {/* File Info with live cursor position */}
        {activeFile && (
          <>
            <StatusItem label={`Ln ${cursorPosition.line}, Col ${cursorPosition.column}`} />
            <StatusItem label={activeFile.language} />
            <StatusItem label="UTF-8" />
          </>
        )}

        {/* Notifications */}
        <StatusItem
          icon={<BellIcon />}
        />
      </div>
    </div>
  );
}

// ============================================================================
// Status Item
// ============================================================================

function StatusItem({
  icon,
  label,
  title,
}: {
  icon?: React.ReactNode;
  label?: string;
  title?: string;
}) {
  return (
    <div
      className="flex items-center space-x-1 hover:bg-white/10 px-1.5 py-0.5 rounded cursor-pointer"
      title={title}
    >
      {icon && <div className="w-3.5 h-3.5">{icon}</div>}
      {label && <span>{label}</span>}
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function getRunStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    connecting: 'Connecting...',
    running: 'Running...',
    awaiting_approval: 'Awaiting Approval',
    completed: 'Completed',
    cancelled: 'Cancelled',
    error: 'Error',
  };
  return labels[status] || status;
}

// ============================================================================
// Icons
// ============================================================================

function RunIcon({ status }: { status: string }) {
  if (status === 'running') {
    return (
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full animate-spin">
        <path d="M8 1a7 7 0 11-7 7h2a5 5 0 105-5V1z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M4 2l10 6-10 6V2z" />
    </svg>
  );
}

function GitBranchIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M5 3a2 2 0 10-2 2v6a2 2 0 104 0V5a2 2 0 00-2-2zm6 0a2 2 0 00-2 2v1l-2 2h2a2 2 0 012 2v1a2 2 0 104 0v-1a2 2 0 00-2-2H9l2-2V5a2 2 0 00-2-2z" />
    </svg>
  );
}

function ModelIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 1a6 6 0 110 12A6 6 0 018 2zm0 2a4 4 0 100 8 4 4 0 000-8zm0 1a3 3 0 110 6 3 3 0 010-6z" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-full h-full">
      <path d="M8 1a1 1 0 011 1v1a4 4 0 014 4v3l1 2H2l1-2V7a4 4 0 014-4V2a1 1 0 011-1zm-1 13h2a1 1 0 11-2 0z" />
    </svg>
  );
}
