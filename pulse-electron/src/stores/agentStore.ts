/**
 * Agent Store (Zustand)
 *
 * Manages agent state, messages, run status, and vibe animation.
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { VibeCategory } from '@/styles/theme';

// ============================================================================
// Message Types
// ============================================================================

export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;

  // Tool call info (for assistant messages)
  toolCalls?: ToolCallInfo[];
}

export interface ToolCallInfo {
  name: string;
  input: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
  timestamp: number;
}

// ============================================================================
// Run State
// ============================================================================

export type RunStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'awaiting_approval'
  | 'completed'
  | 'cancelled'
  | 'error';

export type AgentMode = 'agent' | 'ask' | 'plan';

// ============================================================================
// Vibe State
// ============================================================================

export interface VibeState {
  isActive: boolean;
  category: VibeCategory;
  currentWord: string;
}

// ============================================================================
// Store State
// ============================================================================

interface AgentState {
  // Connection
  isConnected: boolean;
  connectionId: string | null;
  connectionError: string | null;

  // Run state
  currentRunId: string | null;
  conversationId: string | null;
  runStatus: RunStatus;
  mode: AgentMode;

  // Messages
  messages: Message[];
  streamingContent: string;

  // Vibe animation
  vibe: VibeState;

  // Execution log
  executionLog: ToolCallInfo[];
}

// ============================================================================
// Store Actions
// ============================================================================

interface AgentActions {
  // Connection
  setConnected: (connected: boolean, connectionId?: string) => void;
  setConnectionError: (error: string | null) => void;

  // Run state
  startRun: (runId: string, conversationId?: string) => void;
  endRun: (success: boolean, response?: string) => void;
  cancelRun: () => void;
  setRunStatus: (status: RunStatus) => void;
  setMode: (mode: AgentMode) => void;

  // Messages
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateStreamingContent: (chunk: string) => void;
  finalizeStreaming: () => void;
  clearMessages: () => void;

  // Vibe animation
  setVibeActive: (active: boolean) => void;
  setVibeCategory: (category: VibeCategory) => void;
  setVibeWord: (word: string) => void;

  // Tool calls
  addToolCall: (toolCall: Omit<ToolCallInfo, 'timestamp'>) => void;
  updateToolResult: (toolName: string, result: unknown, success: boolean) => void;

  // Utility
  reset: () => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: AgentState = {
  isConnected: false,
  connectionId: null,
  connectionError: null,
  currentRunId: null,
  conversationId: null,
  runStatus: 'idle',
  mode: 'agent',
  messages: [],
  streamingContent: '',
  vibe: {
    isActive: false,
    category: 'thinking',
    currentWord: '',
  },
  executionLog: [],
};

// ============================================================================
// Store Implementation
// ============================================================================

export const useAgentStore = create<AgentState & AgentActions>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    // ========================================================================
    // Connection
    // ========================================================================

    setConnected: (connected, connectionId) => {
      set({
        isConnected: connected,
        connectionId: connectionId || null,
        connectionError: connected ? null : get().connectionError,
      });
    },

    setConnectionError: (error) => {
      // Only set connectionError, don't reset isConnected here
      // The explicit setConnected(false) in handleStateChange handles disconnection
      // This prevents race conditions where errors during connection setup
      // overwrite successful connection state
      set({ connectionError: error });
    },

    // ========================================================================
    // Run State
    // ========================================================================

    startRun: (runId, conversationId) => {
      set({
        currentRunId: runId,
        conversationId: conversationId || get().conversationId,
        runStatus: 'running',
        streamingContent: '',
        executionLog: [],
        vibe: {
          isActive: true,
          category: 'thinking',
          currentWord: 'Starting',
        },
      });
    },

    endRun: (success, response) => {
      const state = get();

      // Finalize any streaming content
      if (state.streamingContent) {
        get().finalizeStreaming();
      }

      // Add final response if provided
      if (response) {
        get().addMessage({
          role: 'assistant',
          content: response,
        });
      }

      set({
        currentRunId: null,
        runStatus: success ? 'completed' : 'error',
        vibe: {
          isActive: false,
          category: 'thinking',
          currentWord: '',
        },
      });
    },

    cancelRun: () => {
      set({
        currentRunId: null,
        runStatus: 'cancelled',
        vibe: {
          isActive: false,
          category: 'thinking',
          currentWord: '',
        },
      });
    },

    setRunStatus: (status) => {
      set({ runStatus: status });
    },

    setMode: (mode) => {
      set({ mode });
    },

    // ========================================================================
    // Messages
    // ========================================================================

    addMessage: (message) => {
      set((state) => ({
        messages: [
          ...state.messages,
          {
            ...message,
            id: crypto.randomUUID(),
            timestamp: Date.now(),
          },
        ],
      }));
    },

    updateStreamingContent: (chunk) => {
      set((state) => ({
        streamingContent: state.streamingContent + chunk,
      }));
    },

    finalizeStreaming: () => {
      const content = get().streamingContent;
      if (!content) return;

      get().addMessage({
        role: 'assistant',
        content,
      });

      set({ streamingContent: '' });
    },

    clearMessages: () => {
      set({
        messages: [],
        streamingContent: '',
        conversationId: null,
      });
    },

    // ========================================================================
    // Vibe Animation
    // ========================================================================

    setVibeActive: (active) => {
      set((state) => ({
        vibe: { ...state.vibe, isActive: active },
      }));
    },

    setVibeCategory: (category) => {
      set((state) => ({
        vibe: { ...state.vibe, category },
      }));
    },

    setVibeWord: (word) => {
      set((state) => ({
        vibe: { ...state.vibe, currentWord: word },
      }));
    },

    // ========================================================================
    // Tool Calls
    // ========================================================================

    addToolCall: (toolCall) => {
      set((state) => ({
        executionLog: [
          ...state.executionLog,
          {
            ...toolCall,
            timestamp: Date.now(),
          },
        ],
      }));
    },

    updateToolResult: (toolName, result, success) => {
      set((state) => {
        const log = [...state.executionLog];
        // Find the most recent matching tool call without a result
        for (let i = log.length - 1; i >= 0; i--) {
          if (log[i].name === toolName && log[i].result === undefined) {
            log[i] = { ...log[i], result, success };
            break;
          }
        }
        return { executionLog: log };
      });
    },

    // ========================================================================
    // Utility
    // ========================================================================

    reset: () => {
      set(initialState);
    },
  }))
);

// ============================================================================
// Selectors
// ============================================================================

export const selectIsRunning = (state: AgentState) =>
  state.runStatus === 'running' || state.runStatus === 'awaiting_approval';

export const selectCanSendMessage = (state: AgentState) =>
  state.isConnected && state.runStatus !== 'running';

export const selectLatestMessage = (state: AgentState) =>
  state.messages[state.messages.length - 1];
