// Settings Modal with animations
import { useState, type ChangeEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSettings } from '../../context/SettingsContext';
import { Button, Input, Icon, Icons } from '../common';
import styles from './SettingsModal.module.css';
import type { Settings } from '../../types';

export function SettingsModal() {
  const { settings, isOpen, closeSettings, updateSettings, saving } = useSettings();
  const [activeTab, setActiveTab] = useState<'basic' | 'routing' | 'advanced' | 'shortcuts' | 'danger'>('basic');
  const [localSettings, setLocalSettings] = useState<Settings | null>(settings);

  if (!isOpen || !settings || !localSettings) return null;

  const handleChange = (key: string, value: any) => {
    setLocalSettings({
      ...localSettings,
      [key]: value,
    });
  };

  const handleNestedChange = (parent: string, key: string, value: any) => {
    setLocalSettings({
      ...localSettings,
      [parent]: {
        ...(localSettings[parent as keyof typeof localSettings] as any),
        [key]: value,
      },
    });
  };

  const handleSave = async () => {
    try {
      if (!localSettings) return;
      await updateSettings(localSettings);
      closeSettings();
    } catch (error) {
      alert('Failed to save settings');
    }
  };

  const tabs = [
    { id: 'basic' as const, label: 'Basic', icon: Icons.settings },
    { id: 'routing' as const, label: 'Routing', icon: 'fa-route' },
    { id: 'advanced' as const, label: 'Advanced', icon: Icons.flask },
    { id: 'shortcuts' as const, label: 'Shortcuts', icon: 'fa-keyboard' },
    { id: 'danger' as const, label: 'Danger', icon: 'fa-triangle-exclamation' },
  ];

  return (
    <motion.div
      className={styles.modalOverlay}
      onClick={closeSettings}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <motion.div
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      >
        <div className={styles.header}>
          <h2>Settings</h2>
          <button className={styles.closeBtn} onClick={closeSettings}><Icon icon={Icons.close} size="md" /></button>
        </div>

        <div className={styles.tabs}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`${styles.tab} ${activeTab === tab.id ? styles.active : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon icon={tab.icon} size="sm" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        <div className={styles.content}>
          {/* Basic Tab */}
          {activeTab === 'basic' && (
            <div className={styles.tabContent}>
              <h3>Model &amp; API Keys</h3>

              <div className={styles.section}>
                <label>Model</label>
                <select
                  value={localSettings?.model || ''}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => handleChange('model', e.target.value)}
                  className={styles.select}
                >
                  <option value="moonshotai/kimi-k2-instruct">Kimi K2.5 (Recommended)</option>
                  <option value="nvidia/nemotron-4-340b">Nemotron 49B</option>
                  <option value="meta-llama/llama-3.1-70b">Llama 3.1 70B</option>
                  <option value="deepseek/deepseek-r1">DeepSeek R1</option>
                </select>
              </div>

              <div className={styles.section}>
                <label>Groq API Key</label>
                <Input
                  type="password"
                  value={localSettings?.apiKeys?.groq || ''}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => handleNestedChange('apiKeys', 'groq', e.target.value)}
                  placeholder="gsk_..."
                />
              </div>

              <div className={styles.section}>
                <label>NVIDIA API Key</label>
                <Input
                  type="password"
                  value={localSettings?.apiKeys?.nvidia || ''}
                  onChange={(e) => handleNestedChange('apiKeys', 'nvidia', e.target.value)}
                  placeholder="nvapi_..."
                />
              </div>

              <h3>User Context</h3>

              <div className={styles.grid2}>
                <div className={styles.section}>
                  <label>Your City</label>
                  <Input
                    value={localSettings?.city || ''}
                    onChange={(e) => handleChange('city', e.target.value)}
                    placeholder="e.g., San Francisco"
                  />
                </div>
                <div className={styles.section}>
                  <label>Country</label>
                  <Input
                    value={localSettings?.country || ''}
                    onChange={(e) => handleChange('country', e.target.value)}
                    placeholder="e.g., USA"
                  />
                </div>
              </div>

              <div className={styles.grid2}>
                <div className={styles.section}>
                  <label>Theme</label>
                  <select
                    value={localSettings?.theme || 'dark'}
                    onChange={(e) => handleChange('theme', e.target.value)}
                    className={styles.select}
                  >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="auto">Auto</option>
                  </select>
                </div>
                <div className={styles.section}>
                  <label>Language</label>
                  <select
                    value={localSettings?.language || 'en'}
                    onChange={(e) => handleChange('language', e.target.value)}
                    className={styles.select}
                  >
                    <option value="en">English</option>
                    <option value="zh">中文</option>
                    <option value="es">Español</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Routing Tab */}
          {activeTab === 'routing' && (
            <div className={styles.tabContent}>
              <h3>Behavior Settings</h3>

              <div className={styles.toggle}>
                <label>
                  <input
                    type="checkbox"
                    checked={localSettings?.proactiveNudges || false}
                    onChange={(e) => handleChange('proactiveNudges', e.target.checked)}
                  />
                  <span>Enable Proactive Nudges</span>
                </label>
                <p className={styles.hint}>AI will suggest actions based on context</p>
              </div>

              <div className={styles.toggle}>
                <label>
                  <input
                    type="checkbox"
                    checked={localSettings?.desktopPet || false}
                    onChange={(e) => handleChange('desktopPet', e.target.checked)}
                  />
                  <span>Enable Desktop Pet</span>
                </label>
                <p className={styles.hint}>Show animated companion in bottom-right</p>
              </div>

              <div className={styles.section}>
                <label>History Depth (Turns)</label>
                <input
                  type="range"
                  min="4"
                  max="32"
                  value={localSettings?.historyDepth || 8}
                  onChange={(e) => handleChange('historyDepth', parseInt(e.target.value))}
                  className={styles.slider}
                />
                <span className={styles.value}>{localSettings?.historyDepth || 8} turns</span>
              </div>

              <div className={styles.section}>
                <label>TTS Language</label>
                <select
                  value={localSettings?.ttsLanguage || 'auto'}
                  onChange={(e) => handleChange('ttsLanguage', e.target.value)}
                  className={styles.select}
                >
                  <option value="auto">Auto-Detect</option>
                  <option value="en">English</option>
                  <option value="zh">Chinese</option>
                </select>
              </div>
            </div>
          )}

          {/* Advanced Tab */}
          {activeTab === 'advanced' && (
            <div className={styles.tabContent}>
              <h3>Advanced Settings</h3>

              <div className={styles.section}>
                <label>Log Level</label>
                <select
                  value={localSettings?.logLevel || 'info'}
                  onChange={(e) => handleChange('logLevel', e.target.value)}
                  className={styles.select}
                >
                  <option value="debug">Debug</option>
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="error">Error</option>
                </select>
              </div>

              <div className={styles.section}>
                <label>Memory Cache Size (MB)</label>
                <input
                  type="number"
                  min="50"
                  max="1000"
                  value={localSettings?.memoryCacheSize || 100}
                  onChange={(e) => handleChange('memoryCacheSize', parseInt(e.target.value))}
                  className={styles.input}
                />
              </div>

              <div className={styles.section}>
                <label>Concurrent Tool Limit</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={localSettings?.concurrentToolLimit || 3}
                  onChange={(e) => handleChange('concurrentToolLimit', parseInt(e.target.value))}
                  className={styles.input}
                />
              </div>

              <div className={styles.section}>
                <label>Memory Strategy</label>
                <select
                  value={localSettings?.memoryStrategy || 'episodic'}
                  onChange={(e) => handleChange('memoryStrategy', e.target.value)}
                  className={styles.select}
                >
                  <option value="episodic">Episodic (Events)</option>
                  <option value="semantic">Semantic (Knowledge)</option>
                  <option value="hybrid">Hybrid</option>
                </select>
              </div>
            </div>
          )}

          {/* Shortcuts Tab */}
          {activeTab === 'shortcuts' && (
            <div className={styles.tabContent}>
              <h3>Keyboard Shortcuts</h3>
              <div className={styles.shortcutsList}>
                <div className={styles.shortcutItem}>
                  <span className={styles.key}>Cmd+K</span>
                  <span>Command Palette</span>
                </div>
                <div className={styles.shortcutItem}>
                  <span className={styles.key}>Cmd+/</span>
                  <span>Toggle Sidebar</span>
                </div>
                <div className={styles.shortcutItem}>
                  <span className={styles.key}>Shift+Enter</span>
                  <span>New Line in Input</span>
                </div>
                <div className={styles.shortcutItem}>
                  <span className={styles.key}>Escape</span>
                  <span>Clear Input</span>
                </div>
              </div>
            </div>
          )}

          {/* Danger Tab */}
          {activeTab === 'danger' && (
            <div className={styles.tabContent}>
              <h3 className={styles.dangerTitle}><Icon icon="fa-triangle-exclamation" size="md" /> Danger Zone</h3>

              <div className={styles.dangerSection}>
                <div>
                  <h4>Clear All Memory</h4>
                  <p>Delete all stored events and memory embeddings. This cannot be undone.</p>
                </div>
                <Button variant="danger" size="sm">Clear Memory</Button>
              </div>

              <div className={styles.dangerSection}>
                <div>
                  <h4>Export Data</h4>
                  <p>Download all your data as JSON for backup or analysis.</p>
                </div>
                <Button variant="secondary" size="sm">Export</Button>
              </div>

              <div className={styles.dangerSection}>
                <div>
                  <h4>Reset Settings</h4>
                  <p>Restore all settings to their default values.</p>
                </div>
                <Button variant="secondary" size="sm">Reset</Button>
              </div>
            </div>
          )}
        </div>

        <div className={styles.footer}>
          <Button variant="ghost" onClick={closeSettings}>Cancel</Button>
          <Button
            variant="primary"
            onClick={handleSave}
            loading={saving}
            disabled={saving}
          >
            Save Changes
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}
