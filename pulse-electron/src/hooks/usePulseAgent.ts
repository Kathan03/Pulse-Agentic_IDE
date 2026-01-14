/**
 * usePulseAgent Hook
 *
 * Main hook for interacting with the Pulse AI agent backend.
 * Manages WebSocket connection, message handling, and state synchronization.
 */

import { useCallback, useEffect, useRef } from 'react';
import { PulseWebSocket, type WebSocketState } from '@/services/websocket';
import { useAgentStore, type Message } from '@/stores/agentStore';
import { useEditorStore } from '@/stores/editorStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import type {
  WSMessage,
  AgentRequestPayload,
  EventPayload,
  ApprovalRequiredPayload,
  RunResultPayload,
  ErrorPayload,
  PatchApprovalData,
  TerminalApprovalData,
} from '@/types/websocket';

const DEFAULT_WS_PORT = 8765;

export interface UsePulseAgentOptions {
  port?: number;
  autoConnect?: boolean;
}

export interface UsePulseAgentReturn {
  // Connection
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;

  // Run state
  isRunning: boolean;
  currentRunId: string | null;

  // Actions
  connect: () => Promise<void>;
  disconnect: () => void;
  sendMessage: (userInput: string) => void;
  cancelRun: () => void;
  approveAction: (feedback?: string) => void;
  denyAction: (feedback?: string) => void;
}

export function usePulseAgent(options: UsePulseAgentOptions = {}): UsePulseAgentReturn {
  const { autoConnect = true } = options;

  const wsRef = useRef<PulseWebSocket | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const portRef = useRef<number>(DEFAULT_WS_PORT);
  const isConnectingRef = useRef<boolean>(false); // Lock to prevent multiple simultaneous connections
  const hasConnectedOnceRef = useRef<boolean>(false); // Track if we've ever connected

  // Stores
  const {
    isConnected,
    connectionError,
    currentRunId,
    runStatus,
    mode,
    setConnected,
    setConnectionError,
    startRun,
    endRun,
    cancelRun: cancelRunState,
    setRunStatus,
    setVibeActive,
    setVibeCategory,
    setVibeWord,
    updateStreamingContent,
    addToolCall,
    updateToolResult,
  } = useAgentStore();

  const { addPendingPatch, enterDiffPreview, openFile, files } = useEditorStore();
  const { addApproval } = useApprovalStore();
  const { projectRoot } = useWorkspaceStore();

  // ========================================================================
  // Message Handlers
  // ========================================================================

  const handleMessage = useCallback(
    (message: WSMessage) => {
      switch (message.type) {
        case 'pong':
          // Connection confirmed (handled in websocket.ts)
          break;

        case 'event':
          handleEvent(message.payload as unknown as EventPayload);
          break;

        case 'approval_required':
          handleApprovalRequired(message.payload as unknown as ApprovalRequiredPayload);
          break;

        case 'run_result':
          handleRunResult(message.payload as unknown as RunResultPayload);
          break;

        case 'error':
          handleError(message.payload as unknown as ErrorPayload);
          break;

        default:
          console.log('Unknown message type:', message.type);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const handleEvent = useCallback(
    (payload: EventPayload) => {
      const { event_type, data } = payload;
      console.log('[usePulseAgent] Event received:', event_type, data);

      switch (event_type) {
        case 'status_changed':
          // Update vibe state
          if (data.vibe_category) {
            setVibeCategory(data.vibe_category as 'thinking' | 'context' | 'action');
          }
          if (data.vibe_word) {
            setVibeWord(data.vibe_word as string);
          }
          // Also handle "status" field from backend events
          if (data.status) {
            setVibeWord(data.status as string);
          }
          break;

        // Handle both frontend naming (tool_started) and backend naming (tool_requested)
        case 'tool_started':
        case 'tool_requested':
          addToolCall({
            name: (data.tool_name || data.tool) as string,
            input: (data.tool_input || data.args || {}) as Record<string, unknown>,
          });
          setVibeCategory('action');
          break;

        // Handle both frontend naming (tool_completed) and backend naming (tool_executed)
        case 'tool_completed':
        case 'tool_executed':
          updateToolResult(
            (data.tool_name || data.tool) as string,
            data.result,
            data.success as boolean
          );
          break;

        case 'message_chunk':
          updateStreamingContent(data.chunk as string);
          break;

        case 'thinking_started':
        case 'node_entered':
          if (data.node === 'master_agent') {
            setVibeCategory('thinking');
          }
          break;

        case 'thinking_completed':
        case 'node_exited':
          if (data.node === 'master_agent') {
            setVibeCategory('context');
          }
          break;

        case 'run_cancelled':
          cancelRunState();
          setVibeActive(false);
          break;

        case 'run_started':
          setVibeActive(true);
          setVibeCategory('thinking');
          break;

        case 'run_completed':
          // Run completed event - vibe will be deactivated when run_result is processed
          break;

        default:
          console.log('[usePulseAgent] Unknown event type:', event_type);
      }
    },
    [addToolCall, updateToolResult, updateStreamingContent, setVibeCategory, setVibeWord, cancelRunState, setVibeActive]
  );

  const handleApprovalRequired = useCallback(
    async (payload: ApprovalRequiredPayload) => {
      setRunStatus('awaiting_approval');
      setVibeActive(false);

      if (payload.approval_type === 'patch') {
        const patchData = payload.data as PatchApprovalData;

        // Open the file in editor if not already open
        if (!files.has(patchData.file_path)) {
          try {
            const content = await window.pulseAPI.fs.readFile(patchData.file_path);
            openFile(patchData.file_path, content);
          } catch (error) {
            console.error('Failed to open file for patch:', error);
          }
        }

        // Add pending patch
        addPendingPatch({
          id: crypto.randomUUID(),
          runId: payload.run_id,
          filePath: patchData.file_path,
          originalContent: patchData.original_content,
          patchedContent: patchData.patched_content,
          patchSummary: patchData.patch_summary,
          timestamp: Date.now(),
        });

        // Enter diff preview
        enterDiffPreview(patchData.file_path);
      }

      // Add to approval queue
      addApproval({
        runId: payload.run_id,
        type: payload.approval_type,
        description: payload.description,
        data: payload.data,
      });
    },
    [setRunStatus, setVibeActive, files, openFile, addPendingPatch, enterDiffPreview, addApproval]
  );

  const handleRunResult = useCallback(
    (payload: RunResultPayload) => {
      console.log('[usePulseAgent] Run result received:', {
        success: payload.success,
        response: payload.response?.substring(0, 100),
        error: payload.error,
        cancelled: payload.cancelled,
      });
      endRun(payload.success, payload.response);
    },
    [endRun]
  );

  const handleError = useCallback(
    (payload: ErrorPayload) => {
      console.error('Agent error:', payload.code, payload.message);
      setRunStatus('error');
      setVibeActive(false);
    },
    [setRunStatus, setVibeActive]
  );

  // ========================================================================
  // WebSocket State Handler
  // ========================================================================

  const handleStateChange = useCallback(
    (state: WebSocketState) => {
      console.log('[usePulseAgent] State change:', state, 'hasConnectedOnce:', hasConnectedOnceRef.current);
      switch (state) {
        case 'connecting':
          // Only set to disconnected if we haven't successfully connected yet
          // This prevents a new connection attempt from resetting an existing connection
          if (!hasConnectedOnceRef.current) {
            setConnectionError(null);
          }
          break;
        case 'connected':
          hasConnectedOnceRef.current = true;
          isConnectingRef.current = false;
          setConnected(true);
          setConnectionError(null);
          console.log('[usePulseAgent] Successfully connected, setting isConnected=true');
          break;
        case 'disconnected':
          // Only update if this is our active WebSocket
          if (!isConnectingRef.current) {
            hasConnectedOnceRef.current = false;
            setConnected(false);
          }
          break;
        case 'error':
          isConnectingRef.current = false;
          if (!hasConnectedOnceRef.current) {
            setConnected(false);
            setConnectionError('Connection failed');
          }
          break;
      }
    },
    [setConnected, setConnectionError]
  );

  const handleWsError = useCallback(
    (error: Error) => {
      setConnectionError(error.message);
    },
    [setConnectionError]
  );

  // ========================================================================
  // Actions
  // ========================================================================

  const connect = useCallback(async () => {
    // Prevent multiple simultaneous connection attempts
    if (wsRef.current?.isConnected()) {
      console.log('[usePulseAgent] Already connected, skipping');
      return;
    }

    // Check if WebSocket is already in CONNECTING state
    if (wsRef.current?.getReadyState() === WebSocket.CONNECTING) {
      console.log('[usePulseAgent] WebSocket already connecting, waiting...');
      return;
    }

    if (isConnectingRef.current) {
      console.log('[usePulseAgent] Already connecting (flag), skipping');
      return;
    }

    if (hasConnectedOnceRef.current) {
      console.log('[usePulseAgent] Already connected once, skipping duplicate attempt');
      return;
    }

    isConnectingRef.current = true;
    console.log('[usePulseAgent] Starting connection...');

    // Fetch dynamic port from backend (in production) or use default
    try {
      if (window.pulseAPI?.backend?.getPort) {
        const port = await window.pulseAPI.backend.getPort();
        portRef.current = port;
        console.log('[usePulseAgent] Using backend port:', port);
      }
    } catch (error) {
      console.warn('[usePulseAgent] Failed to get backend port, using default:', error);
    }

    const wsUrl = `ws://127.0.0.1:${portRef.current}/ws`;
    console.log('[usePulseAgent] Connecting to:', wsUrl);

    // Clean up any existing WebSocket
    if (wsRef.current) {
      wsRef.current.disconnect();
    }

    wsRef.current = new PulseWebSocket(wsUrl, {
      onStateChange: handleStateChange,
      onMessage: handleMessage,
      onError: handleWsError,
    });

    try {
      await wsRef.current.connect();

      // Start ping interval only if not already started
      if (!pingIntervalRef.current) {
        pingIntervalRef.current = setInterval(() => {
          wsRef.current?.ping();
        }, 30000);
      }
    } catch (error) {
      isConnectingRef.current = false;
      throw error;
    }
  }, [handleStateChange, handleMessage, handleWsError]);

  const disconnect = useCallback(() => {
    console.log('[usePulseAgent] Disconnecting...');
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    wsRef.current?.disconnect();
    wsRef.current = null;
    isConnectingRef.current = false;
    hasConnectedOnceRef.current = false;
  }, []);

  const sendMessage = useCallback(
    (userInput: string) => {
      if (!wsRef.current?.isConnected() || !projectRoot) {
        console.warn('Cannot send message: not connected or no project root');
        return;
      }

      const runId = crypto.randomUUID();
      startRun(runId);

      const payload: AgentRequestPayload = {
        user_input: userInput,
        project_root: projectRoot,
        mode: mode,
        max_iterations: 10,
      };

      wsRef.current.sendAgentRequest(payload);
    },
    [projectRoot, mode, startRun]
  );

  const cancelRun = useCallback(() => {
    if (!wsRef.current?.isConnected() || !currentRunId) return;

    wsRef.current.sendCancelRequest({ run_id: currentRunId });
    cancelRunState();
  }, [currentRunId, cancelRunState]);

  const approveAction = useCallback(
    (feedback?: string) => {
      if (!wsRef.current?.isConnected() || !currentRunId) return;

      wsRef.current.sendApprovalResponse({
        run_id: currentRunId,
        approved: true,
        feedback: feedback || '',
      });

      setRunStatus('running');
      setVibeActive(true);
    },
    [currentRunId, setRunStatus, setVibeActive]
  );

  const denyAction = useCallback(
    (feedback?: string) => {
      if (!wsRef.current?.isConnected() || !currentRunId) return;

      wsRef.current.sendApprovalResponse({
        run_id: currentRunId,
        approved: false,
        feedback: feedback || '',
      });

      setRunStatus('running');
      setVibeActive(true);
    },
    [currentRunId, setRunStatus, setVibeActive]
  );

  // ========================================================================
  // Auto-connect on mount
  // ========================================================================

  useEffect(() => {
    if (autoConnect) {
      connect().catch(console.error);
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // ========================================================================
  // Subscribe to new user messages and send them
  // ========================================================================

  const lastMessageCountRef = useRef(0);

  useEffect(() => {
    // Subscribe to message changes
    const unsubscribe = useAgentStore.subscribe(
      (state) => state.messages,
      (messages: Message[]) => {
        // Check if a new message was added
        if (messages.length > lastMessageCountRef.current) {
          const newMessage = messages[messages.length - 1];

          // Only send user messages that are new
          if (newMessage.role === 'user') {
            console.log('[usePulseAgent] New user message detected:', newMessage.content.substring(0, 50));

            // Check connection status from STORE (not wsRef which has stale closure)
            // The store's isConnected is properly updated when WebSocket connects
            const storeState = useAgentStore.getState();
            console.log('[usePulseAgent] Connection check - isConnected:', storeState.isConnected, 'projectRoot:', projectRoot);

            if (!storeState.isConnected) {
              console.warn('[usePulseAgent] Cannot send message: WebSocket not connected');
              // Add system message to inform user
              useAgentStore.getState().addMessage({
                role: 'assistant',
                content: 'Cannot send message: Not connected to backend. Please start the backend server with: `python -m src.server.main`',
              });
            } else if (!projectRoot) {
              console.warn('[usePulseAgent] Cannot send message: No project root (folder not opened)');
              // Add system message to inform user
              useAgentStore.getState().addMessage({
                role: 'assistant',
                content: 'Cannot send message: No folder is open. Please open a folder first using File > Open Folder (Ctrl+O).',
              });
            } else {
              // Guard: Check wsRef is available before sending
              if (!wsRef.current) {
                console.error('[usePulseAgent] Cannot send: wsRef is null despite isConnected=true');
                return;
              }

              // Send via WebSocket
              const runId = crypto.randomUUID();
              console.log('[usePulseAgent] Sending agent request with runId:', runId);
              startRun(runId);

              const payload: AgentRequestPayload = {
                user_input: newMessage.content,
                project_root: projectRoot,
                mode: mode,
                max_iterations: 10,
              };

              console.log('[usePulseAgent] Payload:', payload);
              wsRef.current.sendAgentRequest(payload);
            }
          }
        }
        lastMessageCountRef.current = messages.length;
      }
    );

    return () => {
      unsubscribe();
    };
  }, [projectRoot, mode, startRun]);

  // ========================================================================
  // Return
  // ========================================================================

  return {
    isConnected,
    isConnecting: runStatus === 'connecting',
    connectionError,
    isRunning: runStatus === 'running' || runStatus === 'awaiting_approval',
    currentRunId,
    connect,
    disconnect,
    sendMessage,
    cancelRun,
    approveAction,
    denyAction,
  };
}
