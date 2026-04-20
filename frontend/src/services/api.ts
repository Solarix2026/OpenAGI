// REST API 服务层
import type { Tool, Skill, Goal, MemoryEvent, ChatSession, Settings, SystemStatus, Capabilities } from '../types';

const API_BASE = '/api';

class APIClient {
  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Status & System
  getStatus(): Promise<SystemStatus> {
    return this.fetch('/status');
  }

  getCapabilities(): Promise<Capabilities> {
    return this.fetch('/capabilities');
  }

  getHealth(): Promise<any> {
    return this.fetch('/health');
  }

  // History & Sessions
  getHistory(): Promise<{ messages: any[] }> {
    return this.fetch('/history');
  }

  getSessions(): Promise<ChatSession[]> {
    return this.fetch<ChatSession[]>('/sessions').catch(() => []);
  }

  // Skills & Tools
  getSkills(): Promise<Skill[]> {
    return this.fetch<Skill[]>('/skills');
  }

  getTools(): Promise<Tool[]> {
    return this.fetch<Tool[]>('/tools').catch(() => []);
  }

  // Get tools from status endpoint (returns { tool_names: [...] })
  getToolNames(): Promise<string[]> {
    return this.fetch('/status').then(data => data.tool_names || []).catch(() => []);
  }

  // Goals
  getGoals(): Promise<Goal[]> {
    return this.fetch('/goals');
  }

  addGoal(description: string): Promise<Goal> {
    return this.fetch('/goals', {
      method: 'POST',
      body: JSON.stringify({ description }),
    });
  }

  updateGoal(id: string, updates: Partial<Goal>): Promise<Goal> {
    return this.fetch(`/goals/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  deleteGoal(id: string): Promise<void> {
    return this.fetch(`/goals/${id}`, { method: 'DELETE' });
  }

  // Memory
  getRecentMemory(limit: number = 15): Promise<MemoryEvent[]> {
    return this.fetch(`/memory/recent?limit=${limit}`);
  }

  searchMemory(query: string): Promise<MemoryEvent[]> {
    return this.fetch(`/memory/search?q=${encodeURIComponent(query)}`);
  }

  clearMemory(): Promise<void> {
    return this.fetch('/memory/clear', { method: 'POST' });
  }

  // Settings
  getSettings(): Promise<Settings> {
    return this.fetch('/settings');
  }

  updateSettings(settings: Partial<Settings>): Promise<Settings> {
    return this.fetch('/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  }

  // Sessions
  async deleteSession(sessionId: string): Promise<void> {
    await this.fetch<void>(`/sessions/${sessionId}`, { method: 'DELETE' }).catch(() => undefined);
  }

  // File operations
  readFile(path: string): Promise<string> {
    return this.fetch(`/file?path=${encodeURIComponent(path)}`).then((res: any) => res.content || '');
  }
}

  // Logs
  getLogs(level?: string, module?: string, limit?: number, offset?: number): Promise<{ logs: any[]; total: number; modules: string[] }> {
    const params = new URLSearchParams();
    if (level && level !== 'all') params.append('level', level);
    if (module && module !== 'all') params.append('module', module);
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    const queryString = params.toString() ? `?${params.toString()}` : '';
    return this.fetch(`/logs${queryString}`);
  }

  clearLogs(): Promise<void> {
    return this.fetch('/logs/clear', { method: 'POST' });
  }
}

export const apiClient = new APIClient();
