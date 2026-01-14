/**
 * WebSocket Service
 *
 * Low-level WebSocket client for communicating with the Pulse backend.
 */

import type {
  WSMessage,
  MessageType,
  AgentRequestPayload,
  ApprovalResponsePayload,
  CancelRequestPayload,
} from '@/types/websocket';

export type WebSocketState = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketEvents {
  onStateChange: (state: WebSocketState) => void;
  onMessage: (message: WSMessage) => void;
  onError: (error: Error) => void;
}

/**
 * WebSocket client for Pulse backend communication.
 */
export class PulseWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private events: WebSocketEvents;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private connectionId: string | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isIntentionalDisconnect = false; // Track intentional disconnects to prevent reconnect on code 1006

  constructor(url: string, events: WebSocketEvents) {
    this.url = url;
    this.events = events;
  }

  /**
   * Connect to the WebSocket server.
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        console.log('[WebSocket] Already connected');
        resolve();
        return;
      }

      // Reset intentional disconnect flag when connecting
      this.isIntentionalDisconnect = false;

      console.log(`[WebSocket] Connecting to ${this.url}...`);
      this.events.onStateChange('connecting');

      // Connection timeout
      const connectionTimeout = setTimeout(() => {
        console.error('[WebSocket] Connection timeout after 10s');
        this.events.onStateChange('error');
        this.events.onError(new Error('Connection timeout'));
        reject(new Error('Connection timeout'));
      }, 10000);

      let resolved = false;

      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('[WebSocket] Socket opened, waiting for server confirmation...');
          this.reconnectAttempts = 0;
          // Connection confirmed when we receive pong with connection_id
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WSMessage;
            console.log('[WebSocket] Received:', message.type);

            // Handle connection confirmation
            if (message.type === 'pong' && message.payload.connection_id) {
              this.connectionId = message.payload.connection_id as string;
              console.log(`[WebSocket] Connected with ID: ${this.connectionId}`);
              this.events.onStateChange('connected');
              if (!resolved) {
                resolved = true;
                clearTimeout(connectionTimeout);
                resolve();
              }
            }

            this.events.onMessage(message);
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (event) => {
          console.error('[WebSocket] Error event received');
          const error = new Error('WebSocket connection failed. Is the Python server running?');
          this.events.onError(error);
          this.events.onStateChange('error');
          if (!resolved) {
            resolved = true;
            clearTimeout(connectionTimeout);
            reject(error);
          }
        };

        this.ws.onclose = (event) => {
          console.log(`[WebSocket] Closed: code=${event.code}, reason=${event.reason}, intentional=${this.isIntentionalDisconnect}`);
          this.events.onStateChange('disconnected');
          this.connectionId = null;

          // Attempt reconnection only if:
          // 1. Not an intentional disconnect (covers both code 1000 and code 1006 from closing connecting socket)
          // 2. Haven't exceeded max attempts
          if (!this.isIntentionalDisconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };
      } catch (error) {
        console.error('[WebSocket] Failed to create socket:', error);
        this.events.onStateChange('error');
        clearTimeout(connectionTimeout);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket server.
   */
  disconnect(): void {
    // Mark as intentional disconnect to prevent auto-reconnect
    this.isIntentionalDisconnect = true;

    // Cancel any pending reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
      this.connectionId = null;
    }
  }

  /**
   * Send a message to the server.
   */
  send(type: MessageType, payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    const message: WSMessage = {
      type,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      payload,
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Send an agent request.
   */
  sendAgentRequest(payload: AgentRequestPayload): void {
    this.send('agent_request', payload as unknown as Record<string, unknown>);
  }

  /**
   * Send an approval response.
   */
  sendApprovalResponse(payload: ApprovalResponsePayload): void {
    this.send('approval_response', payload as unknown as Record<string, unknown>);
  }

  /**
   * Send a cancel request.
   */
  sendCancelRequest(payload: CancelRequestPayload): void {
    this.send('cancel_request', payload as unknown as Record<string, unknown>);
  }

  /**
   * Send a ping to keep the connection alive.
   */
  ping(): void {
    this.send('ping', { timestamp: new Date().toISOString() });
  }

  /**
   * Get the connection ID.
   */
  getConnectionId(): string | null {
    return this.connectionId;
  }

  /**
   * Check if connected.
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Schedule a reconnection attempt.
   */
  private scheduleReconnect(): void {
    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(console.error);
    }, delay);
  }

  /**
   * Get the WebSocket ready state.
   */
  getReadyState(): number | undefined {
    return this.ws?.readyState;
  }
}
