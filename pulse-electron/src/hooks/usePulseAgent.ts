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
} from '@/types/websocket';

const DEFAULT_WS_PORT = 8765;

// ============================================================================
// MODULE-LEVEL SINGLETON for shared WebSocket connection
// This ensures all usePulseAgent instances share the same connection
// ============================================================================
let sharedWsRef: PulseWebSocket | null = null;
let sharedPingInterval: NodeJS.Timeout | null = null;
let sharedPortRef = DEFAULT_WS_PORT;
let sharedIsConnecting = false;
let sharedHasConnectedOnce = false;

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

  // Use module-level refs for connection state (shared across all instances)
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
          // Update currentRunId from backend's actual run_id
          if (data.run_id) {
            startRun(data.run_id as string);
          } else {
            setVibeActive(true);
            setVibeCategory('thinking');
          }
          break;

        case 'run_completed':
          // Run completed event - vibe will be deactivated when run_result is processed
          break;

        case 'approval_processed':
          // Server confirms approval was processed - resume vibe and update status
          console.log('[usePulseAgent] Approval processed:', data);
          setRunStatus('running');
          setVibeActive(true);
          setVibeCategory('action');
          break;

        default:
          console.log('[usePulseAgent] Unknown event type:', event_type);
      }
    },
    [addToolCall, updateToolResult, updateStreamingContent, setVibeCategory, setVibeWord, cancelRunState, setVibeActive, startRun]
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
      } else if (payload.approval_type === 'file_write') {
        // Handle file_write similar to patch (preview content)
        const fileData = payload.data as { operation: string; path: string; content: string; diff?: string };

        // Construct absolute path by joining projectRoot with relative path
        // If path is already absolute (starts with / or contains :), use as-is
        const isAbsolute = fileData.path.startsWith('/') || fileData.path.includes(':');
        const fullPath = isAbsolute
          ? fileData.path
          : (projectRoot ? `${projectRoot}/${fileData.path}`.replace(/\\/g, '/') : fileData.path);

        console.log('[usePulseAgent] file_write approval - fullPath:', fullPath, 'projectRoot:', projectRoot);

        // For file_write, we might be creating a new file or updating one
        let originalContent = '';
        try {
          // Try to read existing file content if it exists
          originalContent = await window.pulseAPI.fs.readFile(fullPath);
        } catch (e) {
          // File likely doesn't exist, which is fine for creation
          console.log('[usePulseAgent] File does not exist (likely creation):', fullPath);
          originalContent = '';
        }

        // Open/Ensure file tab exists (use the fullPath)
        if (!files.has(fullPath)) {
          openFile(fullPath, originalContent);
        }

        // Add pending patch (reusing patch mechanism for diff view)
        addPendingPatch({
          id: crypto.randomUUID(),
          runId: payload.run_id,
          filePath: fullPath,
          originalContent: originalContent,
          patchedContent: fileData.content,
          patchSummary: `${fileData.operation} file: ${fileData.path}`,
          timestamp: Date.now(),
        });

        // Enter diff preview
        enterDiffPreview(fullPath);
      }

      // Add to approval queue
      addApproval({
        runId: payload.run_id,
        type: payload.approval_type,
        description: payload.description,
        data: payload.data,
      });
    },
    [setRunStatus, setVibeActive, files, openFile, addPendingPatch, enterDiffPreview, addApproval, projectRoot]
  );

  const handleRunResult = useCallback(
    (payload: RunResultPayload) => {
      console.log('[usePulseAgent] Run result received:', {
        success: payload.success,
        response: payload.response?.substring(0, 100),
        error: payload.error,
        cancelled: payload.cancelled,
        conversation_id: payload.conversation_id,
      });
      // Store conversation_id for subsequent messages in this chat session
      if (payload.conversation_id) {
        useAgentStore.getState().startRun(payload.run_id, payload.conversation_id);
      }
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
      console.log('[usePulseAgent] State change:', state, 'hasConnectedOnce:', sharedHasConnectedOnce);
      switch (state) {
        case 'connecting':
          // Only set to disconnected if we haven't successfully connected yet
          // This prevents a new connection attempt from resetting an existing connection
          if (!sharedHasConnectedOnce) {
            setConnectionError(null);
          }
          break;
        case 'connected':
          sharedHasConnectedOnce = true;
          sharedIsConnecting = false;
          setConnected(true);
          setConnectionError(null);
          console.log('[usePulseAgent] Successfully connected, setting isConnected=true');
          break;
        case 'disconnected':
          // Only update if this is our active WebSocket
          if (!sharedIsConnecting) {
            sharedHasConnectedOnce = false;
            setConnected(false);
          }
          break;
        case 'error':
          sharedIsConnecting = false;
          if (!sharedHasConnectedOnce) {
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
    if (sharedWsRef?.isConnected()) {
      console.log('[usePulseAgent] Already connected, skipping');
      return;
    }

    // Check if WebSocket is already in CONNECTING state
    if (sharedWsRef?.getReadyState() === WebSocket.CONNECTING) {
      console.log('[usePulseAgent] WebSocket already connecting, waiting...');
      return;
    }

    if (sharedIsConnecting) {
      console.log('[usePulseAgent] Already connecting (flag), skipping');
      return;
    }

    if (sharedHasConnectedOnce) {
      console.log('[usePulseAgent] Already connected once, skipping duplicate attempt');
      return;
    }

    sharedIsConnecting = true;
    console.log('[usePulseAgent] Starting connection...');

    // Fetch dynamic port from backend (in production) or use default
    try {
      if (window.pulseAPI?.backend?.getPort) {
        const port = await window.pulseAPI.backend.getPort();
        sharedPortRef = port;
        console.log('[usePulseAgent] Using backend port:', port);
      }
    } catch (error) {
      console.warn('[usePulseAgent] Failed to get backend port, using default:', error);
    }

    // Wait for backend to be ready (Issue #1 fix: health polling)
    const maxRetries = 30; // 30 retries x 1 second = 30 seconds max wait
    const healthUrl = `http://127.0.0.1:${sharedPortRef}/api/health`;
    let backendReady = false;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`[usePulseAgent] Health check attempt ${attempt}/${maxRetries}...`);
        const response = await fetch(healthUrl, {
          method: 'GET',
          signal: AbortSignal.timeout(3000) // 3 second timeout per request
        });
        if (response.ok) {
          console.log('[usePulseAgent] Backend is healthy, proceeding with WebSocket connection');
          backendReady = true;
          break;
        }
      } catch (healthError) {
        console.log(`[usePulseAgent] Health check failed (attempt ${attempt}):`, healthError);
        if (attempt < maxRetries) {
          // Wait 1 second before retry
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
    }

    if (!backendReady) {
      console.error('[usePulseAgent] Backend health check failed after all retries');
      sharedIsConnecting = false;
      throw new Error('Backend is not ready. Please wait and try again.');
    }

    const wsUrl = `ws://127.0.0.1:${sharedPortRef}/ws`;
    console.log('[usePulseAgent] Connecting to:', wsUrl);

    // Clean up any existing WebSocket
    if (sharedWsRef) {
      sharedWsRef.disconnect();
    }

    sharedWsRef = new PulseWebSocket(wsUrl, {
      onStateChange: handleStateChange,
      onMessage: handleMessage,
      onError: handleWsError,
    });

    try {
      await sharedWsRef.connect();

      // Start ping interval only if not already started
      if (!sharedPingInterval) {
        sharedPingInterval = setInterval(() => {
          sharedWsRef?.ping();
        }, 30000);
      }
    } catch (error) {
      sharedIsConnecting = false;
      throw error;
    }
  }, [handleStateChange, handleMessage, handleWsError]);

  const disconnect = useCallback(() => {
    console.log('[usePulseAgent] Disconnecting...');
    if (sharedPingInterval) {
      clearInterval(sharedPingInterval);
      sharedPingInterval = null;
    }
    sharedWsRef?.disconnect();
    sharedWsRef = null;
    sharedIsConnecting = false;
    sharedHasConnectedOnce = false;
  }, []);

  const sendMessage = useCallback(
    (userInput: string) => {
      if (!sharedWsRef?.isConnected() || !projectRoot) {
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

      sharedWsRef.sendAgentRequest(payload);
    },
    [projectRoot, mode, startRun]
  );

  const cancelRun = useCallback(() => {
    if (!sharedWsRef?.isConnected() || !currentRunId) return;

    sharedWsRef.sendCancelRequest({ run_id: currentRunId });
    cancelRunState();
  }, [currentRunId, cancelRunState]);

  const approveAction = useCallback(
    (feedback?: string) => {
      if (!sharedWsRef?.isConnected() || !currentRunId) return;

      sharedWsRef.sendApprovalResponse({
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
      if (!sharedWsRef?.isConnected() || !currentRunId) return;

      sharedWsRef.sendApprovalResponse({
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
        // IMPORTANT: If messages were reset (e.g., loadConversationHistory), sync the ref
        // This prevents auto-sending when loading conversation history
        if (messages.length < lastMessageCountRef.current) {
          // Messages were replaced/cleared - sync ref without sending
          lastMessageCountRef.current = messages.length;
          return;
        }

        // Check if a new message was added (incrementally)
        if (messages.length > lastMessageCountRef.current) {
          // PERMANENT FIX: Skip if we're loading conversation history
          // This prevents auto-sending the last user message when opening old conversations
          const storeState = useAgentStore.getState();
          if (storeState.isLoadingHistory) {
            console.log('[usePulseAgent] Skipping auto-send - loading conversation history');
            lastMessageCountRef.current = messages.length;
            return;
          }

          const newMessage = messages[messages.length - 1];

          // Only send user messages that are new
          if (newMessage.role === 'user') {
            console.log('[usePulseAgent] New user message detected:', newMessage.content.substring(0, 50));

            // Check connection status from STORE (not wsRef which has stale closure)
            // The store's isConnected is properly updated when WebSocket connects
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
            } else if (storeState.currentRunId) {
              console.warn('[usePulseAgent] Cannot send message: A run is already active:', storeState.currentRunId);
              // Don't send duplicate requests while a run is in progress
            } else {
              // Guard: Check wsRef is available before sending
              if (!sharedWsRef) {
                console.error('[usePulseAgent] Cannot send: wsRef is null despite isConnected=true');
                return;
              }

              // Send via WebSocket
              const runId = crypto.randomUUID();
              // Get current conversation ID from store to continue the conversation
              const currentConversationId = storeState.conversationId;
              console.log('[usePulseAgent] Sending agent request with runId:', runId, 'conversationId:', currentConversationId);
              startRun(runId, currentConversationId || undefined);

              const payload: AgentRequestPayload = {
                user_input: newMessage.content,
                project_root: projectRoot,
                mode: mode,
                max_iterations: 10,
                conversation_id: currentConversationId || undefined,
              };

              console.log('[usePulseAgent] Payload:', payload);
              sharedWsRef.sendAgentRequest(payload);
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
