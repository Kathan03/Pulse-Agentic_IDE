/**
 * TerminalPanel - Interactive Terminal with PTY
 *
 * VS Code-style terminal panel using xterm.js with node-pty backend.
 * Provides a real interactive shell (PowerShell/bash).
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
  terminal: Terminal;
  fitAddon: FitAddon;
}

export function TerminalPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<TerminalSession | null>(null);
  const { terminalHeight, setTerminalHeight, terminalVisible } = useUIStore();
  const { projectRoot } = useWorkspaceStore();
  const { theme } = useTheme();
  const [isResizing, setIsResizing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
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

  // Initialize terminal and PTY
  useEffect(() => {
    if (!containerRef.current || sessionRef.current) return;

    const initTerminal = async () => {
      // Check if PTY API is available
      if (!window.pulseAPI?.pty) {
        setError('Terminal API not available');
        return;
      }

      // Create xterm.js terminal
      const terminal = new Terminal({
        fontFamily: '"Cascadia Code", Consolas, "Courier New", monospace',
        fontSize: 13,
        theme: getTerminalTheme(),
        cursorBlink: true,
        cursorStyle: 'bar',
        scrollback: 5000,
        allowTransparency: false,
        windowsMode: window.pulseAPI.platform === 'win32',
      });

      // Load addons
      const fitAddon = new FitAddon();
      const webLinksAddon = new WebLinksAddon();
      terminal.loadAddon(fitAddon);
      terminal.loadAddon(webLinksAddon);

      // Open terminal in container
      terminal.open(containerRef.current!);

      // Delay fit to ensure container is sized
      await new Promise(resolve => setTimeout(resolve, 50));
      fitAddon.fit();

      // Spawn PTY process
      try {
        const { id } = await window.pulseAPI.pty.spawn({
          cwd: projectRoot || undefined,
          cols: terminal.cols,
          rows: terminal.rows,
        });

        // Store session
        sessionRef.current = {
          id,
          terminal,
          fitAddon,
        };

        setIsConnected(true);
        setError(null);

        // Forward terminal input to PTY
        terminal.onData((data) => {
          window.pulseAPI.pty.write(id, data);
        });

        // Handle terminal resize
        terminal.onResize(({ cols, rows }) => {
          window.pulseAPI.pty.resize(id, cols, rows);
        });

        // Subscribe to PTY output
        const unsubData = window.pulseAPI.pty.onData((ptyId, data) => {
          if (ptyId === id && sessionRef.current?.terminal) {
            sessionRef.current.terminal.write(data);
          }
        });

        // Subscribe to PTY exit
        const unsubExit = window.pulseAPI.pty.onExit((ptyId, exitCode) => {
          if (ptyId === id) {
            terminal.writeln(`\r\n\x1b[33mProcess exited with code ${exitCode}\x1b[0m`);
            setIsConnected(false);
          }
        });

        // Focus terminal
        terminal.focus();

        // Return cleanup function
        return () => {
          unsubData();
          unsubExit();
          window.pulseAPI.pty.kill(id);
          terminal.dispose();
          sessionRef.current = null;
        };
      } catch (err) {
        console.error('Failed to spawn PTY:', err);
        setError(err instanceof Error ? err.message : 'Failed to start terminal');

        // Fall back to simple terminal mode
        terminal.writeln('\x1b[1;36mPulse Terminal (Simple Mode)\x1b[0m');
        terminal.writeln('\x1b[33mInteractive terminal not available. Using command execution mode.\x1b[0m');
        terminal.writeln('');
        terminal.write('$ ');

        sessionRef.current = {
          id: -1,
          terminal,
          fitAddon,
        };

        // Simple command execution mode (fallback)
        let currentLine = '';
        terminal.onData((data) => {
          if (data === '\r') {
            terminal.writeln('');
            if (currentLine.trim() && window.pulseAPI?.terminal?.execute) {
              window.pulseAPI.terminal.execute(currentLine)
                .then((result) => {
                  if (result) {
                    result.split('\n').forEach(line => terminal.writeln(line));
                  }
                  terminal.write('$ ');
                })
                .catch((err) => {
                  terminal.writeln(`\x1b[31mError: ${err.message}\x1b[0m`);
                  terminal.write('$ ');
                });
            } else {
              terminal.write('$ ');
            }
            currentLine = '';
          } else if (data === '\u007f') {
            if (currentLine.length > 0) {
              currentLine = currentLine.slice(0, -1);
              terminal.write('\b \b');
            }
          } else if (data === '\x03') {
            terminal.writeln('^C');
            currentLine = '';
            terminal.write('$ ');
          } else if (data >= ' ' || data === '\t') {
            currentLine += data;
            terminal.write(data);
          }
        });
      }
    };

    initTerminal();

    return () => {
      if (sessionRef.current) {
        if (sessionRef.current.id !== -1) {
          window.pulseAPI.pty.kill(sessionRef.current.id);
        }
        sessionRef.current.terminal.dispose();
        sessionRef.current = null;
      }
    };
  }, []); // Only run once on mount

  // Update theme when it changes
  useEffect(() => {
    if (sessionRef.current?.terminal) {
      sessionRef.current.terminal.options.theme = getTerminalTheme();
    }
  }, [theme, getTerminalTheme]);

  // Refit on resize or visibility change
  useEffect(() => {
    if (sessionRef.current?.fitAddon && terminalVisible) {
      setTimeout(() => {
        sessionRef.current?.fitAddon.fit();
        sessionRef.current?.terminal.focus();
      }, 10);
    }
  }, [terminalHeight, terminalVisible]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (sessionRef.current?.fitAddon && terminalVisible) {
        sessionRef.current.fitAddon.fit();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [terminalVisible]);

  // Update PTY working directory when project changes
  useEffect(() => {
    if (projectRoot && sessionRef.current?.id && sessionRef.current.id !== -1) {
      window.pulseAPI.pty.setCwd(sessionRef.current.id, projectRoot);
    }
  }, [projectRoot]);

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
      setTimeout(() => sessionRef.current?.fitAddon.fit(), 0);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // Restart terminal
  const handleRestart = useCallback(async () => {
    if (sessionRef.current) {
      if (sessionRef.current.id !== -1) {
        await window.pulseAPI.pty.kill(sessionRef.current.id);
      }
      sessionRef.current.terminal.dispose();
      sessionRef.current = null;
    }

    setIsConnected(false);
    setError(null);

    // Re-trigger initialization by forcing a remount
    // This is a bit hacky, but works reliably
    const container = containerRef.current;
    if (container) {
      container.innerHTML = '';

      // Small delay then re-initialize
      setTimeout(async () => {
        if (!window.pulseAPI?.pty) return;

        const terminal = new Terminal({
          fontFamily: '"Cascadia Code", Consolas, "Courier New", monospace',
          fontSize: 13,
          theme: getTerminalTheme(),
          cursorBlink: true,
          cursorStyle: 'bar',
          scrollback: 5000,
          windowsMode: window.pulseAPI.platform === 'win32',
        });

        const fitAddon = new FitAddon();
        terminal.loadAddon(fitAddon);
        terminal.open(container);

        await new Promise(r => setTimeout(r, 50));
        fitAddon.fit();

        try {
          const { id } = await window.pulseAPI.pty.spawn({
            cwd: projectRoot || undefined,
            cols: terminal.cols,
            rows: terminal.rows,
          });

          sessionRef.current = { id, terminal, fitAddon };
          setIsConnected(true);

          terminal.onData((data) => window.pulseAPI.pty.write(id, data));
          terminal.onResize(({ cols, rows }) => window.pulseAPI.pty.resize(id, cols, rows));
          window.pulseAPI.pty.onData((ptyId, data) => {
            if (ptyId === id) terminal.write(data);
          });

          terminal.focus();
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to restart terminal');
        }
      }, 100);
    }
  }, [projectRoot, getTerminalTheme]);

  if (!terminalVisible) return null;

  return (
    <div
      className="bg-pulse-bg border-t border-pulse-border flex flex-col flex-shrink-0"
      style={{ height: terminalHeight }}
    >
      {/* Resize Handle */}
      <div
        className={`h-1 cursor-ns-resize transition-colors ${
          isResizing ? 'bg-pulse-primary' : 'bg-pulse-border hover:bg-pulse-primary'
        }`}
        onMouseDown={handleMouseDown}
      />

      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1 bg-pulse-bg-secondary border-b border-pulse-border flex-shrink-0">
        <div className="flex items-center space-x-2">
          <TerminalIcon />
          <span className="text-xs font-medium text-pulse-fg">Terminal</span>
          {isConnected && (
            <span className="w-2 h-2 rounded-full bg-pulse-success" title="Connected" />
          )}
          {error && (
            <span className="text-xs text-pulse-warning" title={error}>
              (Limited Mode)
            </span>
          )}
        </div>
        <div className="flex items-center space-x-1">
          {/* New Terminal Button */}
          <button
            onClick={handleRestart}
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
          {/* Close Button */}
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
        ref={containerRef}
        className="flex-1 overflow-hidden"
        style={{ padding: '4px 8px' }}
        onClick={() => sessionRef.current?.terminal.focus()}
      />
    </div>
  );
}

// ============================================================================
// Icons
// ============================================================================

function TerminalIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 text-pulse-fg-muted">
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
