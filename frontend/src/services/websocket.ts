// WebSocket 连接管理和事件处理
import type { Message } from '../types';

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private messageListeners: ((msg: Message) => void)[] = [];
  private statusListeners: ((status: 'connected' | 'disconnected' | 'error') => void)[] = [];
  private messageQueue: Message[] = [];

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    this.url = `${protocol}//${host}/ws`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected');
          this.reconnectAttempts = 0;
          this.notifyStatusChange('connected');

          // 发送队列中的消息
          while (this.messageQueue.length > 0) {
            const msg = this.messageQueue.shift();
            if (msg) this.send(msg);
          }

          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const message: Message = {
              type: data.type || 'response',
              text: data.text || '',
              timestamp: data.ts || Date.now(),
              level: data.level,
              module: data.module,
            };
            this.notifyMessageReceived(message);
          } catch (e) {
            console.error('[WebSocket] Failed to parse message:', e);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          this.notifyStatusChange('error');
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('[WebSocket] Closed');
          this.notifyStatusChange('disconnected');
          this.attemptReconnect();
        };
      } catch (e) {
        reject(e);
      }
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(
        `[WebSocket] Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
      );
      setTimeout(() => this.connect().catch(console.error), this.reconnectDelay);
    }
  }

  send(message: Message): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Connection not open, queuing message');
      this.messageQueue.push(message);
    }
  }

  sendText(text: string): void {
    this.send({
      type: 'message',
      text,
      timestamp: Date.now(),
    });
  }

  onMessage(callback: (msg: Message) => void): () => void {
    this.messageListeners.push(callback);
    return () => {
      this.messageListeners = this.messageListeners.filter((cb) => cb !== callback);
    };
  }

  onStatusChange(callback: (status: 'connected' | 'disconnected' | 'error') => void): () => void {
    this.statusListeners.push(callback);
    return () => {
      this.statusListeners = this.statusListeners.filter((cb) => cb !== callback);
    };
  }

  private notifyMessageReceived(msg: Message): void {
    this.messageListeners.forEach((cb) => cb(msg));
  }

  private notifyStatusChange(status: 'connected' | 'disconnected' | 'error'): void {
    this.statusListeners.forEach((cb) => cb(status));
  }

  disconnect(): void {
    this.maxReconnectAttempts = 0; // 防止自动重连
    this.ws?.close();
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// 全局单例
let wsManager: WebSocketManager | null = null;

export function getWebSocketManager(): WebSocketManager {
  if (!wsManager) {
    wsManager = new WebSocketManager();
  }
  return wsManager;
}
