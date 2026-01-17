/**
 * TerminalPanel - Interactive Terminal with PTY (Multi-Session)
 *
 * VS Code-style terminal panel using xterm.js with node-pty backend.
 * Supports multiple terminal sessions with tabs and kill functionality.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { useUIStore } from '@/stores/uiStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { useTheme } from '@/contexts/ThemeContext';

interface TerminalSession {
  id: number;
  name: string;
  terminal: Terminal;
  fitAddon: FitAddon;
  containerEl: HTMLDivElement;
  isConnected: boolean;
}

export function TerminalPanel() {
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const sessionsRef = useRef<Map<number, TerminalSession>>(new Map());
  const [sessions, setSessions] = useState<{ id: number; name: string }[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const sessionCounterRef = useRef(0);
  const listenersRegistered = useRef(false);

  // Register PTY IPC listeners ONCE at component mount
  useEffect(() => {
    // In React Strict Mode, effects run twice. We need to handle this properly.
    // The ref prevents double-registration during the same mount cycle,
    // but we must reset it in cleanup to allow registration on subsequent mounts.
    if (listenersRegistered.current) return;
    listenersRegistered.current = true;

    console.log('[TerminalPanel] Registering PTY IPC listeners');

    // Subscribe to PTY output for ALL sessions
    const cleanupData = window.pulseAPI.pty.onData((ptyId: number, data: string) => {
      const session = sessionsRef.current.get(ptyId);
      if (session) {
        session.terminal.write(data);
      }
    });

    // Subscribe to PTY exit for ALL sessions
    const cleanupExit = window.pulseAPI.pty.onExit((ptyId: number, exitCode: number) => {
      const session = sessionsRef.current.get(ptyId);
      if (session) {
        session.terminal.writeln(`\r\n\x1b[33mProcess exited with code ${exitCode}\x1b[0m`);
        session.isConnected = false;
      }
    });

    return () => {
      console.log('[TerminalPanel] Cleaning up PTY IPC listeners');
      cleanupData();
      cleanupExit();
      // Reset the ref so listeners can be registered again if component remounts
      listenersRegistered.current = false;
    };
  }, []);

  const { terminalHeight, setTerminalHeight, terminalVisible } = useUIStore();
  const { projectRoot } = useWorkspaceStore();
  const { theme } = useTheme();
  const [isResizing, setIsResizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get terminal theme colors
  const getTerminalTheme = useCallback(() => ({
    background: theme.colors.bg,
    foreground: theme.colors.fg,
    cursor: theme.colors.primary,
    cursorAccent: theme.colors.bg,
    selectionBackground: theme.colors.selection,
    black: '#1e1e1e',
    red: '#f48771',
    green: '#89d185',
    yellow: '#cca700',
    blue: '#3794ff',
    magenta: '#bc89bd',
    cyan: '#89d9e9',
    white: '#e5e5e5',
    brightBlack: '#666666',
    brightRed: '#f48771',
    brightGreen: '#89d185',
    brightYellow: '#cca700',
    brightBlue: '#3794ff',
    brightMagenta: '#bc89bd',
    brightCyan: '#89d9e9',
    brightWhite: '#ffffff',
  }), [theme]);

  // Create a new terminal session
  const createSession = useCallback(async () => {
    if (!mainContainerRef.current || !window.pulseAPI?.pty) {
      setError('Terminal API not available');
      return;
    }

    sessionCounterRef.current += 1;
    const sessionNum = sessionCounterRef.current;
    const sessionName = `Terminal ${sessionNum}`;

    // Create container for this terminal
    const containerEl = document.createElement('div');
    containerEl.className = 'w-full h-full';
    containerEl.style.display = 'none'; // Hidden by default

    mainContainerRef.current.appendChild(containerEl);

    // Create xterm.js terminal
    const terminal = new Terminal({
      fontFamily: '"Cascadia Code", Consolas, "Courier New", monospace',
      fontSize: 13,
      theme: getTerminalTheme(),
      cursorBlink: true,
      cursorStyle: 'bar',
      scrollback: 5000,
      allowTransparency: false,
    });

    // Load addons
    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);

    // Open terminal in container
    terminal.open(containerEl);

    // Delay fit to ensure container is sized
    await new Promise(resolve => setTimeout(resolve, 50));

    // Spawn PTY process
    try {
      const { id } = await window.pulseAPI.pty.spawn({
        cwd: projectRoot || undefined,
        cols: terminal.cols || 80,
        rows: terminal.rows || 24,
      });

      // Store session
      const session: TerminalSession = {
        id,
        name: sessionName,
        terminal,
        fitAddon,
        containerEl,
        isConnected: true,
      };
      sessionsRef.current.set(id, session);

      // Forward terminal input to PTY
      terminal.onData((data) => {
        window.pulseAPI.pty.write(id, data);
      });

      // Handle terminal resize
      terminal.onResize(({ cols, rows }) => {
        window.pulseAPI.pty.resize(id, cols, rows);
      });

      // Subscribe to PTY output - MOVED TO GLOBAL LISTENER
      // window.pulseAPI.pty.onData((ptyId: number, data: string) => { ... });

      // Subscribe to PTY exit - MOVED TO GLOBAL LISTENER
      // window.pulseAPI.pty.onExit((ptyId: number, exitCode: number) => { ... });

      // Update state
      setSessions(prev => [...prev, { id, name: sessionName }]);
      setActiveSessionId(id);
      setError(null);

      // Show and focus this terminal
      containerEl.style.display = 'block';
      fitAddon.fit();
      terminal.focus();

    } catch (err) {
      console.error('Failed to spawn PTY:', err);
      setError(err instanceof Error ? err.message : 'Failed to start terminal');
      containerEl.remove();
    }
  }, [projectRoot, getTerminalTheme]);

  // Kill/close a terminal session
  const killSession = useCallback(async (sessionId: number) => {
    const session = sessionsRef.current.get(sessionId);
    if (!session) return;

    // Kill PTY
    if (session.isConnected) {
      try {
        await window.pulseAPI.pty.kill(sessionId);
      } catch (e) {
        console.warn('Error killing PTY:', e);
      }
    }

    // Dispose terminal
    session.terminal.dispose();
    session.containerEl.remove();
    sessionsRef.current.delete(sessionId);

    // Update state
    setSessions(prev => prev.filter(s => s.id !== sessionId));

    // If this was active, switch to another session
    if (activeSessionId === sessionId) {
      const remaining = [...sessionsRef.current.keys()];
      setActiveSessionId(remaining.length > 0 ? remaining[0] : null);
    }
  }, [activeSessionId]);

  // Switch to a session
  const switchToSession = useCallback((sessionId: number) => {
    // Hide current session
    if (activeSessionId !== null) {
      const currentSession = sessionsRef.current.get(activeSessionId);
      if (currentSession) {
        currentSession.containerEl.style.display = 'none';
      }
    }

    // Show new session
    const newSession = sessionsRef.current.get(sessionId);
    if (newSession) {
      newSession.containerEl.style.display = 'block';
      setActiveSessionId(sessionId);
      setTimeout(() => {
        newSession.fitAddon.fit();
        newSession.terminal.focus();
      }, 10);
    }
  }, [activeSessionId]);

  // Auto-create first session when panel becomes visible with no sessions
  useEffect(() => {
    if (terminalVisible && sessions.length === 0 && mainContainerRef.current) {
      createSession();
    }
  }, [terminalVisible, sessions.length, createSession]);

  // Update theme when it changes
  useEffect(() => {
    sessionsRef.current.forEach(session => {
      session.terminal.options.theme = getTerminalTheme();
    });
  }, [theme, getTerminalTheme]);

  // Refit on resize or visibility change
  useEffect(() => {
    if (terminalVisible && activeSessionId !== null) {
      const session = sessionsRef.current.get(activeSessionId);
      if (session) {
        setTimeout(() => {
          session.fitAddon.fit();
          session.terminal.focus();
        }, 10);
      }
    }
  }, [terminalHeight, terminalVisible, activeSessionId]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (terminalVisible && activeSessionId !== null) {
        const session = sessionsRef.current.get(activeSessionId);
        if (session) {
          session.fitAddon.fit();
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [terminalVisible, activeSessionId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      sessionsRef.current.forEach(session => {
        if (session.isConnected) {
          window.pulseAPI.pty.kill(session.id);
        }
        session.terminal.dispose();
      });
      sessionsRef.current.clear();
    };
  }, []);

  // Drag resize handler
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startY = e.clientY;
    const startHeight = terminalHeight;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = startY - e.clientY;
      setTerminalHeight(Math.max(100, Math.min(500, startHeight + delta)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      // Refit after resize
      if (activeSessionId !== null) {
        const session = sessionsRef.current.get(activeSessionId);
        if (session) {
          setTimeout(() => session.fitAddon.fit(), 0);
        }
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  if (!terminalVisible) return null;

  const activeSession = activeSessionId !== null ? sessionsRef.current.get(activeSessionId) : null;

  return (
    <div
      className="bg-pulse-bg border-t border-pulse-border flex flex-col flex-shrink-0"
      style={{ height: terminalHeight }}
    >
      {/* Resize Handle */}
      <div
        className={`h-1 cursor-ns-resize transition-colors ${isResizing ? 'bg-pulse-primary' : 'bg-pulse-border hover:bg-pulse-primary'
          }`}
        onMouseDown={handleMouseDown}
      />

      {/* Header with Tabs */}
      <div className="flex items-center justify-between px-2 py-1 bg-pulse-bg-secondary border-b border-pulse-border flex-shrink-0">
        {/* Left: Tabs */}
        <div className="flex items-center space-x-1 overflow-x-auto">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center px-2 py-0.5 rounded text-xs cursor-pointer transition-colors ${session.id === activeSessionId
                ? 'bg-pulse-bg text-pulse-fg'
                : 'text-pulse-fg-muted hover:bg-pulse-bg-tertiary hover:text-pulse-fg'
                }`}
              onClick={() => switchToSession(session.id)}
            >
              <TerminalIcon />
              <span className="ml-1.5 truncate max-w-24">{session.name}</span>
              {/* Kill button on hover */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  killSession(session.id);
                }}
                className="ml-1.5 p-0.5 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded transition-opacity"
                title="Kill Terminal"
              >
                <CloseIcon />
              </button>
            </div>
          ))}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center space-x-1 ml-2">
          {/* Connection Status */}
          {activeSession?.isConnected && (
            <span className="w-2 h-2 rounded-full bg-pulse-success mr-2" title="Connected" />
          )}
          {error && (
            <span className="text-xs text-pulse-warning mr-2" title={error}>
              (Error)
            </span>
          )}

          {/* New Terminal Button */}
          <button
            onClick={createSession}
            className="text-pulse-fg-muted hover:text-pulse-fg p-1 rounded hover:bg-pulse-bg-tertiary"
            title="New Terminal"
          >
            <PlusIcon />
          </button>
          {/* Minimize Button */}
          <button
            onClick={() => setTerminalHeight(100)}
            className="text-pulse-fg-muted hover:text-pulse-fg p-1 rounded hover:bg-pulse-bg-tertiary"
            title="Minimize Terminal"
          >
            <MinimizeIcon />
          </button>
          {/* Close Panel Button */}
          <button
            onClick={() => useUIStore.getState().toggleTerminal()}
            className="text-pulse-fg-muted hover:text-pulse-fg p-1 rounded hover:bg-pulse-bg-tertiary"
            title="Close Terminal (Ctrl+`)"
          >
            <CloseIcon />
          </button>
        </div>
      </div>

      {/* Terminal Content */}
      <div
        ref={mainContainerRef}
        className="flex-1 overflow-hidden p-1"
        onClick={() => activeSession?.terminal.focus()}
      />
    </div>
  );
}

// ============================================================================
// Icons
// ============================================================================

function TerminalIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 flex-shrink-0">
      <path d="M2 3a1 1 0 011-1h10a1 1 0 011 1v10a1 1 0 01-1 1H3a1 1 0 01-1-1V3zm1 0v10h10V3H3z" />
      <path d="M4 6l3 2-3 2V6zm4 4h4v1H8v-1z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
      <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2" fill="none" />
    </svg>
  );
}

function MinimizeIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
      <path d="M2 8h12v1H2z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3">
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  );
}
