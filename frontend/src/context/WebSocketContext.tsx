// WebSocket上下文
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { getWebSocketManager } from '../services/websocket';
import type { Message } from '../types';

interface WebSocketContextType {
  messages: Message[];
  isConnected: boolean;
  send: (text: string) => void;
  clearMessages: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const wsManager = getWebSocketManager();

    // 连接
    wsManager.connect().catch((e) => {
      console.error('Failed to connect WebSocket:', e);
    });

    // 监听消息
    const unsubscribeMessage = wsManager.onMessage((msg) => {
      setMessages((prev) => [...prev, msg]);
    });

    // 监听连接状态
    const unsubscribeStatus = wsManager.onStatusChange((status) => {
      setIsConnected(status === 'connected');
    });

    return () => {
      unsubscribeMessage();
      unsubscribeStatus();
    };
  }, []);

  const send = useCallback((text: string) => {
    const wsManager = getWebSocketManager();
    wsManager.sendText(text);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return (
    <WebSocketContext.Provider value={{ messages, isConnected, send, clearMessages }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}
