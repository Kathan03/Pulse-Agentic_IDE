/**
 * WebSocket Protocol Types
 *
 * These types match the Python backend's WebSocket protocol.
 * See: src/server/models.py
 */

// ============================================================================
// Message Types (matches MessageType enum in Python)
// ============================================================================

export type MessageType =
  | 'agent_request'
  | 'approval_response'
  | 'cancel_request'
  | 'ping'
  | 'event'
  | 'approval_required'
  | 'run_result'
  | 'error'
  | 'pong';

// ============================================================================
// Base Message Structure
// ============================================================================

export interface WSMessage<T = Record<string, unknown>> {
  type: MessageType;
  id: string;
  timestamp: string;
  payload: T;
}

// ============================================================================
// Client → Server Messages
// ============================================================================

export interface AgentRequestPayload {
  user_input: string;
  project_root: string;
  mode: 'agent' | 'ask' | 'plan';
  max_iterations: number;
  conversation_id?: string;
}

export interface ApprovalResponsePayload {
  run_id: string;
  approved: boolean;
  feedback: string;
}

export interface CancelRequestPayload {
  run_id: string;
}

export interface PingPayload {
  timestamp?: string;
}

// ============================================================================
// Server → Client Messages
// ============================================================================

export interface PongPayload {
  timestamp?: string;
  connection_id?: string;
  status?: string;
}

export interface EventPayload {
  event_type: string;
  data: Record<string, unknown>;
}

export interface ApprovalRequiredPayload {
  run_id: string;
  approval_type: 'patch' | 'terminal';
  description: string;
  data: PatchApprovalData | TerminalApprovalData;
}

export interface PatchApprovalData {
  file_path: string;
  original_content: string;
  patched_content: string;
  patch_summary: string;
}

export interface TerminalApprovalData {
  command: string;
  working_directory: string;
  risk_level: 'low' | 'medium' | 'high';
  explanation: string;
}

export interface RunResultPayload {
  run_id: string;
  conversation_id: string;
  success: boolean;
  response: string;
  files_touched: string[];
  execution_log: ExecutionLogEntry[];
  cancelled: boolean;
  error?: string;
}

export interface ExecutionLogEntry {
  timestamp: string;
  type: 'tool_call' | 'tool_result' | 'message' | 'approval';
  data: Record<string, unknown>;
}

export interface ErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// Event Types (from agent execution)
// ============================================================================

export type AgentEventType =
  | 'status_changed'
  | 'tool_started'
  | 'tool_completed'
  | 'tool_error'
  | 'message_chunk'
  | 'thinking_started'
  | 'thinking_completed'
  | 'approval_processed'
  | 'run_cancelled';

export interface StatusChangedEvent {
  event_type: 'status_changed';
  data: {
    status: string;
    vibe_category?: 'thinking' | 'context' | 'action';
    vibe_word?: string;
  };
}

export interface ToolStartedEvent {
  event_type: 'tool_started';
  data: {
    tool_name: string;
    tool_input: Record<string, unknown>;
  };
}

export interface ToolCompletedEvent {
  event_type: 'tool_completed';
  data: {
    tool_name: string;
    result: unknown;
    success: boolean;
  };
}

export interface ToolErrorEvent {
  event_type: 'tool_error';
  data: {
    tool_name: string;
    error: string;
  };
}

export interface MessageChunkEvent {
  event_type: 'message_chunk';
  data: {
    chunk: string;
    role: 'assistant' | 'user';
  };
}

// ============================================================================
// Typed Message Helpers
// ============================================================================

export type AgentRequestMessage = WSMessage<AgentRequestPayload>;
export type ApprovalResponseMessage = WSMessage<ApprovalResponsePayload>;
export type CancelRequestMessage = WSMessage<CancelRequestPayload>;
export type PingMessage = WSMessage<PingPayload>;
export type PongMessage = WSMessage<PongPayload>;
export type EventMessage = WSMessage<EventPayload>;
export type ApprovalRequiredMessage = WSMessage<ApprovalRequiredPayload>;
export type RunResultMessage = WSMessage<RunResultPayload>;
export type ErrorMessage = WSMessage<ErrorPayload>;
