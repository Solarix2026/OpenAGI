// Zustand store for global app state management
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface DashboardState {
  isLoading: boolean;
  lastUpdated: number;
  setLoading: (loading: boolean) => void;
  updateTimestamp: () => void;
}

interface PageState {
  currentPage: string;
  isTransitioning: boolean;
  transitionProgress: number;
  setPage: (page: string) => void;
  setTransitioning: (isTransitioning: boolean) => void;
  setTransitionProgress: (progress: number) => void;
}

interface SkeletonState {
  activeSkeletons: Set<string>;
  registerSkeleton: (id: string) => void;
  unregisterSkeleton: (id: string) => void;
  hasSkeleton: (id: string) => boolean;
  clearAll: () => void;
}

interface OptimisticUpdate {
  id: string;
  type: string;
  previousValue: unknown;
  newValue: unknown;
  status: 'pending' | 'success' | 'error';
  error?: string;
}

interface OptimisticState {
  updates: Map<string, OptimisticUpdate>;
  addUpdate: (update: OptimisticUpdate) => void;
  removeUpdate: (id: string) => void;
  updateStatus: (id: string, status: OptimisticUpdate['status'], error?: string) => void;
  getUpdate: (id: string) => OptimisticUpdate | undefined;
}

interface ToastState {
  toasts: Array<{
    id: string;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    duration: number;
  }>;
  addToast: (message: string, type: ToastState['toasts'][0]['type'], duration?: number) => void;
  removeToast: (id: string) => void;
}

// Dashboard Store
export const useDashboardStore = create<DashboardState>((set) => ({
  isLoading: true,
  lastUpdated: Date.now(),
  setLoading: (loading) => set({ isLoading: loading }),
  updateTimestamp: () => set({ lastUpdated: Date.now() }),
}));

// Page Navigation Store
export const usePageStore = create<PageState>((set) => ({
  currentPage: 'chat',
  isTransitioning: false,
  transitionProgress: 0,
  setPage: (page) => set({ currentPage: page }),
  setTransitioning: (isTransitioning) => set({ isTransitioning }),
  setTransitionProgress: (progress) => set({ transitionProgress: progress }),
}));

// Skeleton Loading Store
export const useSkeletonStore = create<SkeletonState>((set, get) => ({
  activeSkeletons: new Set(),
  registerSkeleton: (id) =>
    set((state) => ({
      activeSkeletons: new Set([...state.activeSkeletons, id]),
    })),
  unregisterSkeleton: (id) =>
    set((state) => {
      const newSet = new Set(state.activeSkeletons);
      newSet.delete(id);
      return { activeSkeletons: newSet };
    }),
  hasSkeleton: (id) => get().activeSkeletons.has(id),
  clearAll: () => set({ activeSkeletons: new Set() }),
}));

// Optimistic Updates Store
export const useOptimisticStore = create<OptimisticState>((set, get) => ({
  updates: new Map(),
  addUpdate: (update) =>
    set((state) => {
      const newUpdates = new Map(state.updates);
      newUpdates.set(update.id, update);
      return { updates: newUpdates };
    }),
  removeUpdate: (id) =>
    set((state) => {
      const newUpdates = new Map(state.updates);
      newUpdates.delete(id);
      return { updates: newUpdates };
    }),
  updateStatus: (id, status, error) =>
    set((state) => {
      const newUpdates = new Map(state.updates);
      const update = newUpdates.get(id);
      if (update) {
        newUpdates.set(id, { ...update, status, error });
      }
      return { updates: newUpdates };
    }),
  getUpdate: (id) => get().updates.get(id),
}));

// Toast Store
export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  addToast: (message, type, duration = 3000) => {
    const id = Math.random().toString(36).substring(7);
    set((state) => ({
      toasts: [...state.toasts, { id, message, type, duration }],
    }));
    setTimeout(() => {
      get().removeToast(id);
    }, duration);
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));

// Session History Store with Persistence
export const useSessionStore = create(
  persist<
    {
      sessions: Array<{
        id: string;
        title: string;
        messages: Array<{
          role: string;
          content: string;
          timestamp: number;
        }>;
        createdAt: number;
        updatedAt: number;
      }>;
      currentSessionId: string | null;
      addSession: (session: { id: string; title: string }) => void;
      addMessage: (sessionId: string, message: { role: string; content: string }) => void;
      setCurrentSession: (id: string | null) => void;
      deleteSession: (id: string) => void;
      renameSession: (id: string, title: string) => void;
    }
  >(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      addSession: (session) =>
        set((state) => ({
          sessions: [
            {
              ...session,
              messages: [],
              createdAt: Date.now(),
              updatedAt: Date.now(),
            },
            ...state.sessions,
          ],
          currentSessionId: session.id,
        })),
      addMessage: (sessionId, message) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: [...s.messages, { ...message, timestamp: Date.now() }],
                  updatedAt: Date.now(),
                }
              : s
          ),
        })),
      setCurrentSession: (id) => set({ currentSessionId: id }),
      deleteSession: (id) =>
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== id),
          currentSessionId: state.currentSessionId === id ? null : state.currentSessionId,
        })),
      renameSession: (id, title) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id ? { ...s, title } : s
          ),
        })),
    }),
    {
      name: 'openagi-sessions',
    }
  )
);

// Settings Store with Persistence
export const useSettingsStore = create(
  persist<{
    llmProvider: string;
    theme: 'dark' | 'light' | 'auto';
    sidebarCollapsed: boolean;
    notifications: boolean;
    soundEffects: boolean;
    setLLMProvider: (provider: string) => void;
    setTheme: (theme: 'dark' | 'light' | 'auto') => void;
    toggleSidebar: () => void;
    setNotifications: (enabled: boolean) => void;
    setSoundEffects: (enabled: boolean) => void;
  }>(
    (set) => ({
      llmProvider: 'auto',
      theme: 'auto',
      sidebarCollapsed: false,
      notifications: true,
      soundEffects: true,
      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setNotifications: (enabled) => set({ notifications: enabled }),
      setSoundEffects: (enabled) => set({ soundEffects: enabled }),
    }),
    {
      name: 'openagi-settings',
    }
  )
);
