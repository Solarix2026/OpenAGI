// Settings 模态框和Context
import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '../services/api';
import type { Settings } from '../types';

interface SettingsContextType {
  settings: Settings | null;
  isOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  saving: boolean;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

const defaultSettings: Settings = {
  theme: 'dark',
  language: 'en',
  model: 'moonshotai/kimi-k2-instruct',
  apiKeys: {},
  city: undefined,
  country: undefined,
  timezone: undefined,
  proactiveNudges: true,
  desktopPet: true,
  historyDepth: 8,
  ttsLanguage: 'auto',
  logLevel: 'info',
  memoryCacheSize: 100,
  memoryStrategy: 'episodic',
  sandboxPermissions: [],
  concurrentToolLimit: 3,
};

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [isOpen, setIsOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  // 初始加载设置
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const loaded = await apiClient.getSettings().catch(() => null);
        if (loaded) {
          setSettings({ ...defaultSettings, ...loaded });
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    };
    loadSettings();
  }, []);

  const openSettings = () => setIsOpen(true);
  const closeSettings = () => setIsOpen(false);

  const updateSettings = async (updates: Partial<Settings>) => {
    try {
      setSaving(true);
      const newSettings = { ...settings, ...updates };
      const saved = await apiClient.updateSettings(updates).catch(() => null);
      if (saved) {
        setSettings({ ...newSettings, ...saved });
      } else {
        setSettings(newSettings);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      throw error;
    } finally {
      setSaving(false);
    }
  };

  return (
    <SettingsContext.Provider value={{ settings, isOpen, openSettings, closeSettings, updateSettings, saving }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return context;
}
