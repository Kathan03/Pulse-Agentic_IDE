/**
 * AgentInput - User Input Component
 *
 * Text area for sending messages to the AI agent.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useAgentStore, selectIsRunning, selectCanSendMessage } from '@/stores/agentStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';

export function AgentInput() {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { addMessage, cancelRun, mode, isConnected, connectionError } = useAgentStore();
  const isRunning = useAgentStore(selectIsRunning);
  const canSend = useAgentStore(selectCanSendMessage);
  const { projectRoot } = useWorkspaceStore();

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || !canSend) return;

    // Add user message
    addMessage({
      role: 'user',
      content: trimmed,
    });

    // Clear input
    setInput('');

    // Note: The actual WebSocket send would be handled by usePulseAgent hook
    // which listens for new user messages
  }, [input, canSend, addMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleCancel = useCallback(() => {
    cancelRun();
  }, [cancelRun]);

  return (
    <div className="p-3">
      {/* Warning if not connected */}
      {!isConnected && (
        <div className="mb-2 px-3 py-1.5 bg-pulse-error/20 border border-pulse-error/50 rounded text-xs text-pulse-error">
          <span className="font-medium">Not connected to backend.</span>
          {' '}
          {connectionError || 'Start the Python server on port 8765.'}
        </div>
      )}

      {/* Warning if no workspace */}
      {!projectRoot && isConnected && (
        <div className="mb-2 px-3 py-1.5 bg-pulse-warning/20 border border-pulse-warning/50 rounded text-xs text-pulse-warning">
          Open a workspace folder to enable file operations
        </div>
      )}

      {/* Input area */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={getPlaceholder(mode)}
          disabled={isRunning}
          rows={1}
          className={`
            w-full px-3 py-2 pr-12
            bg-pulse-input border border-pulse-border rounded-lg
            text-sm resize-none
            focus:outline-none focus:border-pulse-primary
            placeholder:text-pulse-fg-muted
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        />

        {/* Send/Cancel button */}
        <div className="absolute right-2 bottom-2">
          {isRunning ? (
            <button
              onClick={handleCancel}
              className="p-1.5 rounded hover:bg-pulse-error/20 text-pulse-error transition-colors"
              title="Cancel"
            >
              <StopIcon />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim() || !canSend}
              className="p-1.5 rounded hover:bg-pulse-primary/20 text-pulse-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Send (Enter)"
            >
              <SendIcon />
            </button>
          )}
        </div>
      </div>

      {/* Hints */}
      <div className="mt-1.5 flex items-center justify-between text-xs text-pulse-fg-muted">
        <span>
          {isRunning ? 'Agent is working...' : 'Press Enter to send, Shift+Enter for new line'}
        </span>
        <span className="capitalize">{mode} mode</span>
      </div>
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function getPlaceholder(mode: string): string {
  switch (mode) {
    case 'agent':
      return 'Ask me to help with your code...';
    case 'ask':
      return 'Ask a question (read-only mode)...';
    case 'plan':
      return 'Describe what you want to build...';
    default:
      return 'Type a message...';
  }
}

// ============================================================================
// Icons
// ============================================================================

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
      <path
        d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}
