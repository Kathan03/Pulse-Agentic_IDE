/**
 * AppShell - Main Application Layout
 *
 * The root layout component that orchestrates all panels and areas.
 * VS Code-style layout with titlebar, activity bar, sidebar, editor, and agent panel.
 * Issue 3: Added resizable panels with drag handles.
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { TitleBar } from './TitleBar';
import { ActivityBar } from './ActivityBar';
import { Sidebar } from './Sidebar';
import { EditorArea } from './EditorArea';
import { AgentPanel } from './AgentPanel';
import { StatusBar } from './StatusBar';
import { TerminalPanel } from '@/components/terminal/TerminalPanel';
import { useUIStore } from '@/stores/uiStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';

export function AppShell() {
  const {
    sidebarVisible,
    agentPanelVisible,
    sidebarWidth,
    agentPanelWidth,
    setSidebarWidth,
    setAgentPanelWidth,
    setMaximized,
  } = useUIStore();

  const { loadRecentWorkspaces } = useWorkspaceStore();

  // Resize state
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);
  const [isResizingAgentPanel, setIsResizingAgentPanel] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Initialize on mount
  useEffect(() => {
    // Load recent workspaces
    loadRecentWorkspaces();

    // Listen for maximize state changes
    const unsubscribe = window.pulseAPI.window.onMaximizeChange((isMaximized) => {
      setMaximized(isMaximized);
    });

    // Check initial maximize state
    window.pulseAPI.window.isMaximized().then(setMaximized);

    return unsubscribe;
  }, [loadRecentWorkspaces, setMaximized]);

  // Sidebar resize handlers
  const handleSidebarResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingSidebar(true);
  }, []);

  // Agent panel resize handlers
  const handleAgentPanelResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingAgentPanel(true);
  }, []);

  // Global mouse move and up handlers for resizing
  useEffect(() => {
    if (!isResizingSidebar && !isResizingAgentPanel) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const containerRect = containerRef.current.getBoundingClientRect();
      const activityBarWidth = 48; // w-activitybar

      if (isResizingSidebar) {
        const newWidth = e.clientX - containerRect.left - activityBarWidth;
        setSidebarWidth(newWidth);
      }

      if (isResizingAgentPanel) {
        const newWidth = containerRect.right - e.clientX;
        setAgentPanelWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizingSidebar(false);
      setIsResizingAgentPanel(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    // Prevent selection during resize
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isResizingSidebar, isResizingAgentPanel, setSidebarWidth, setAgentPanelWidth]);

  return (
    <div className="flex flex-col h-screen w-screen bg-pulse-bg text-pulse-fg overflow-hidden">
      {/* Title Bar (custom frameless) */}
      <TitleBar />

      {/* Main Content Area */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden">
        {/* Activity Bar (left icon strip) */}
        <ActivityBar />

        {/* Sidebar (file explorer, search, etc.) */}
        {sidebarVisible && (
          <>
            <div
              className="flex-shrink-0 bg-pulse-bg-secondary"
              style={{ width: sidebarWidth }}
            >
              <Sidebar />
            </div>
            {/* Sidebar Resize Handle */}
            <ResizeHandle onMouseDown={handleSidebarResizeStart} />
          </>
        )}

        {/* Editor Area (center) + Terminal */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-pulse-bg">
          <div className="flex-1 min-h-0 overflow-hidden">
            <EditorArea />
          </div>
          <TerminalPanel />
        </div>

        {/* Agent Panel (right) */}
        {agentPanelVisible && (
          <>
            {/* Agent Panel Resize Handle */}
            <ResizeHandle onMouseDown={handleAgentPanelResizeStart} />
            <div
              className="flex-shrink-0 bg-pulse-bg-secondary"
              style={{ width: agentPanelWidth }}
            >
              <AgentPanel />
            </div>
          </>
        )}
      </div>

      {/* Status Bar (bottom) */}
      <StatusBar />
    </div>
  );
}

// ============================================================================
// Resize Handle Component
// ============================================================================

interface ResizeHandleProps {
  onMouseDown: (e: React.MouseEvent) => void;
}

function ResizeHandle({ onMouseDown }: ResizeHandleProps) {
  return (
    <div
      onMouseDown={onMouseDown}
      className="w-1 bg-pulse-border hover:bg-pulse-primary cursor-col-resize flex-shrink-0 transition-colors"
      title="Drag to resize"
    />
  );
}
