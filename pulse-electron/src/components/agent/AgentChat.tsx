/**
 * AgentChat - Message List Component
 *
 * Displays the conversation history with the AI agent.
 */

import { useEffect, useRef } from 'react';
import { useAgentStore, type Message } from '@/stores/agentStore';
import { AgentMessage } from './AgentMessage';
import { FoxMascot } from '@/components/common/FoxMascot';

export function AgentChat() {
  const { messages, streamingContent, isConnected, connectionError } = useAgentStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  // Show connection status when not connected
  if (!isConnected && messages.length === 0) {
    return <DisconnectedState error={connectionError} />;
  }

  // Empty state
  if (messages.length === 0 && !streamingContent) {
    return <EmptyChat />;
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto px-3 py-4 space-y-4">
      {messages.map((message) => (
        <AgentMessage key={message.id} message={message} />
      ))}

      {/* Streaming content */}
      {streamingContent && (
        <AgentMessage
          message={{
            id: 'streaming',
            role: 'assistant',
            content: streamingContent,
            timestamp: Date.now(),
            isStreaming: true,
          }}
        />
      )}
    </div>
  );
}

// ============================================================================
// Disconnected State
// ============================================================================

function DisconnectedState({ error }: { error: string | null }) {
  return (
    <div className="h-full flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 mb-4 text-pulse-warning">
        <DisconnectedIcon />
      </div>
      <h3 className="text-lg font-medium text-pulse-fg mb-2">
        Backend Not Connected
      </h3>
      <p className="text-sm text-pulse-fg-muted max-w-xs mb-4">
        {error || 'The Pulse backend server is not running.'}
      </p>
      <div className="bg-pulse-bg-tertiary rounded-lg p-4 max-w-xs">
        <p className="text-xs text-pulse-fg-muted mb-2">Start the backend with:</p>
        <code className="block bg-pulse-bg px-3 py-2 rounded text-pulse-primary text-sm font-mono">
          python -m src.server.main
        </code>
      </div>
      <p className="text-xs text-pulse-fg-muted mt-4">
        The agent will auto-connect when the server starts.
      </p>
    </div>
  );
}

function DisconnectedIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  );
}

// ============================================================================
// Empty State
// ============================================================================

function EmptyChat() {
  return (
    <div className="h-full flex flex-col items-center justify-center p-6 text-center">
      <div className="w-24 h-24 mb-4">
        <FoxMascot bodyColor="var(--pulse-primary)" eyeColor="#FFFFFF" />
      </div>
      <h3 className="text-lg font-medium text-pulse-fg mb-2">
        Start a conversation
      </h3>
      <p className="text-sm text-pulse-fg-muted max-w-xs">
        Ask me to help with your PLC code, explain concepts, or modify files in your workspace.
      </p>

      {/* Quick suggestions */}
      <div className="mt-6 space-y-2 w-full max-w-xs">
        <Suggestion text="Explain what this program does" />
        <Suggestion text="Find all function blocks" />
        <Suggestion text="Add error handling to the main program" />
      </div>
    </div>
  );
}

function Suggestion({ text }: { text: string }) {
  const { addMessage } = useAgentStore();

  const handleClick = () => {
    addMessage({
      role: 'user',
      content: text,
    });
    // Note: The actual send would be handled by usePulseAgent hook
  };

  return (
    <button
      onClick={handleClick}
      className="w-full text-left px-3 py-2 text-sm text-pulse-fg-muted hover:text-pulse-fg bg-pulse-bg-tertiary hover:bg-pulse-input rounded transition-colors"
    >
      {text}
    </button>
  );
}

