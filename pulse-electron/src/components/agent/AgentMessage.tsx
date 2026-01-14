/**
 * AgentMessage - Individual Chat Message
 *
 * Displays a single message with avatar, content, and metadata.
 */

import type { Message } from '@/stores/agentStore';

interface AgentMessageProps {
  message: Message;
}

export function AgentMessage({ message }: AgentMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`
          max-w-[85%] rounded-lg px-3 py-2
          ${isUser ? 'bg-pulse-primary text-white' : 'bg-pulse-bg-tertiary'}
          ${isSystem ? 'bg-pulse-warning/20 border border-pulse-warning/50' : ''}
        `}
      >
        {/* Avatar row */}
        {!isUser && (
          <div className="flex items-center mb-1.5">
            <div className="w-5 h-5 rounded-full bg-pulse-primary flex items-center justify-center mr-2">
              <PulseIcon />
            </div>
            <span className="text-xs font-medium text-pulse-fg-muted">
              {isSystem ? 'System' : 'Pulse'}
            </span>
            {message.isStreaming && (
              <span className="ml-2 text-xs text-pulse-primary animate-pulse">
                typing...
              </span>
            )}
          </div>
        )}

        {/* Content */}
        <div className="text-sm whitespace-pre-wrap break-words">
          <MessageContent content={message.content} />
        </div>

        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2 pt-2 border-t border-pulse-border space-y-1">
            {message.toolCalls.map((tool, idx) => (
              <ToolCallBadge key={idx} name={tool.name} success={tool.success} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div className={`text-xs mt-1 ${isUser ? 'text-white/70' : 'text-pulse-fg-muted'}`}>
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Message Content
// ============================================================================

function MessageContent({ content }: { content: string }) {
  // Simple markdown-like rendering
  // In a real app, use a proper markdown renderer

  // Code blocks
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <>
      {parts.map((part, idx) => {
        if (part.startsWith('```')) {
          const lines = part.slice(3, -3).split('\n');
          const language = lines[0] || 'text';
          const code = lines.slice(1).join('\n');
          return (
            <pre
              key={idx}
              className="mt-2 mb-2 p-2 bg-pulse-bg rounded text-xs overflow-x-auto"
            >
              <code>{code || part.slice(3, -3)}</code>
            </pre>
          );
        }

        // Inline code
        const inlineParts = part.split(/(`[^`]+`)/g);
        return (
          <span key={idx}>
            {inlineParts.map((inline, i) => {
              if (inline.startsWith('`') && inline.endsWith('`')) {
                return (
                  <code
                    key={i}
                    className="px-1 py-0.5 bg-pulse-bg rounded text-xs font-mono"
                  >
                    {inline.slice(1, -1)}
                  </code>
                );
              }
              return inline;
            })}
          </span>
        );
      })}
    </>
  );
}

// ============================================================================
// Tool Call Badge
// ============================================================================

function ToolCallBadge({ name, success }: { name: string; success?: boolean }) {
  return (
    <div className="inline-flex items-center px-2 py-0.5 bg-pulse-bg rounded text-xs">
      <ToolIcon />
      <span className="ml-1">{name}</span>
      {success !== undefined && (
        <span className={`ml-1 ${success ? 'text-pulse-success' : 'text-pulse-error'}`}>
          {success ? '✓' : '✗'}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ============================================================================
// Icons
// ============================================================================

function PulseIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="white" className="w-3 h-3">
      <path d="M2 8h2l1.5-3 2 6 2-8 2 5 1.5-2H14" stroke="white" strokeWidth="1.5" fill="none" />
    </svg>
  );
}

function ToolIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3 text-pulse-fg-muted">
      <path d="M14.5 3.5l-2-2-5 5L5 4 2 7l2.5 2.5L2 12l2 2 2.5-2.5L9 14l3-3-2.5-2.5 5-5z" />
    </svg>
  );
}
