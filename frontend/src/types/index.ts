// API 类型定义

export type MessageType = 'message' | 'thinking' | 'response' | 'proactive' | 'log' | 'mode' | 'status';

export interface Message {
  type: MessageType;
  text: string;
  timestamp?: number;
  level?: 'debug' | 'info' | 'warning' | 'error';
  module?: string;
}

export interface Tool {
  name: string;
  description: string;
  parameters?: Record<string, any>;
  icon?: string;
}

export interface Skill {
  name: string;
  description: string;
  category?: string;
  tags?: string[];
}

export interface Goal {
  id: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'abandoned';
  source: 'user' | 'system';
  createdAt: number;
  progress?: number;
}

export interface MemoryEvent {
  id: string;
  type: string;
  content: string;
  timestamp: number;
  importance: number;
  embedding?: number[];
}

export interface ChatSession {
  id: string;
  title: string;
  timestamp: number;
  messages: Message[];
  messageCount: number;
}

export interface Channel {
  id: string;
  name: string;
  platform: 'telegram' | 'discord' | 'slack' | 'whatsapp' | 'signal' | 'imessage';
  status: 'connected' | 'disconnected' | 'error';
  dmPolicy?: 'pairing' | 'open' | 'closed';
  allowlist?: string[];
}

export interface SystemStatus {
  online: boolean;
  toolCount: number;
  activeTools: number;
  memorySize: number;
  memoryUsage: number;
  uptime: string;
  avgResponseTime: number;
  requestsPerMin: number;
  tool_names?: string[];
  apiKeysSet: {
    groq: boolean;
    nvidia: boolean;
    telegram?: boolean;
  };
}

export interface Capabilities {
  memory: number;
  reasoning: number;
  planning: number;
  coding: number;
  computer: number;
  browser: number;
  evolution: number;
}

export interface Settings {
  // Basic
  theme: 'light' | 'dark' | 'auto';
  language: string;
  model: string;
  apiKeys: {
    groq?: string;
    nvidia?: string;
    telegram?: string;
  };
  telegram_set?: boolean;

  // User Context
  city?: string;
  country?: string;
  timezone?: string;

  // Routing
  proactiveNudges: boolean;
  desktopPet: boolean;
  historyDepth: number;
  ttsLanguage: 'auto' | 'en' | 'zh';

  // Advanced
  logLevel: 'debug' | 'info' | 'warning' | 'error';
  memoryCacheSize: number;
  memoryStrategy: string;
  sandboxPermissions: string[];
  concurrentToolLimit: number;
}
