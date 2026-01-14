/**
 * AgentPanel - Right-side AI Chat Panel
 *
 * Contains the AI assistant chat interface with mode selector and vibe loader.
 */

import { AgentChat } from '../agent/AgentChat';
import { AgentInput } from '../agent/AgentInput';
import { ModeSelector } from '../agent/ModeSelector';
import { VibeLoader } from '../vibe/VibeLoader';
import { useAgentStore, selectIsRunning } from '@/stores/agentStore';
import { PulseLogo } from '@/components/common/PulseLogo';

export function AgentPanel() {
  const isRunning = useAgentStore(selectIsRunning);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-9 px-3 flex items-center justify-between border-b border-pulse-border">
        <div className="flex items-center gap-2">
          <PulseLogo size={55} />
          <span className="text-xs font-semibold uppercase tracking-wide text-pulse-fg-muted">
            Pulse Agent
          </span>
        </div>
        <ModeSelector />
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

