/**
 * AgentPanel - Right-side AI Chat Panel
 *
 * Contains the AI assistant chat interface with mode selector and vibe loader.
 */

import { AgentChat } from '../agent/AgentChat';
import { AgentInput } from '../agent/AgentInput';
import { ModeSelector } from '../agent/ModeSelector';
import { ModelSelector } from '../agent/ModelSelector';
import { ChatHistory } from '../agent/ChatHistory';
import { VibeLoader } from '../vibe/VibeLoader';
import { useAgentStore, selectIsRunning } from '@/stores/agentStore';
import { PulseLogo } from '@/components/common/PulseLogo';

export function AgentPanel() {
  const isRunning = useAgentStore(selectIsRunning);
  const clearMessages = useAgentStore((s) => s.clearMessages);

  // Handle new chat - clears current messages
  const handleNewChat = () => {
    clearMessages();
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-9 px-3 flex items-center justify-between border-b border-pulse-border">
        <div className="flex items-center gap-2">
          <PulseLogo size={35} />
          <span className="text-xs font-semibold uppercase tracking-wide text-pulse-fg-muted">
            Pulse Agent
          </span>
        </div>
        <div className="flex items-center gap-1">
          {/* New Chat Button */}
          <button
            onClick={handleNewChat}
            className="p-1.5 rounded hover:bg-pulse-bg-tertiary transition-colors"
            title="New Chat"
          >
            <PlusIcon />
          </button>
          <ChatHistory />
          <ModelSelector />
          <ModeSelector />
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-hidden">
        <AgentChat />
      </div>

      {/* Vibe Loader (shown when running) */}
      {isRunning && (
        <div className="px-3 py-2 border-t border-pulse-border">
          <VibeLoader />
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-pulse-border">
        <AgentInput />
      </div>
    </div>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 text-pulse-fg-muted">
      <path d="M8 0a.75.75 0 01.75.75v6.5h6.5a.75.75 0 010 1.5h-6.5v6.5a.75.75 0 01-1.5 0v-6.5H.75a.75.75 0 010-1.5h6.5V.75A.75.75 0 018 0z" />
    </svg>
  );
}

