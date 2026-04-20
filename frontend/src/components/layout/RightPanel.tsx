// RightPanel component for Memory and Capabilities
import React, { useState, useEffect } from 'react';
import { Icon, Icons } from '../common';
import { apiClient } from '../../services/api';
import type { MemoryEvent } from '../../types';
import styles from './RightPanel.module.css';

interface CapabilitiesData {
  memory: number;
  reasoning: number;
  planning: number;
  coding: number;
  computer: number;
  browser: number;
  evolution: number;
}

interface RightPanelProps {
  className?: string;
}

export const RightPanel: React.FC<RightPanelProps> = ({ className }) => {
  const [memoryEvents, setMemoryEvents] = useState<MemoryEvent[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilitiesData>({
    memory: 0.85,
    reasoning: 0.70,
    planning: 0.65,
    coding: 0.60,
    computer: 0.45,
    browser: 0.45,
    evolution: 0.68,
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);

      // Load recent memory events
      const memoryData = await apiClient.getRecentMemory(10).catch(() => null);
      if (memoryData) {
        setMemoryEvents(memoryData);
      }

      // Load capabilities
      const capabilitiesData = await apiClient.getCapabilities().catch(() => null);
      if (capabilitiesData) {
        setCapabilities(capabilitiesData as CapabilitiesData);
      }
    } catch (error) {
      console.error('Failed to load right panel data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timestamp?: number) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();

    if (isToday) {
      return formatTime(timestamp);
    }
    return date.toLocaleDateString([], {
      month: 'short',
      day: 'numeric'
    });
  };

  const getCapabilityColor = (value: number) => {
    if (value >= 0.8) return '#10b981'; // green
    if (value >= 0.6) return '#3b82f6'; // blue
    if (value >= 0.4) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  const getImportanceColor = (importance: number) => {
    if (importance >= 0.8) return '#8b5cf6'; // purple
    if (importance >= 0.6) return '#3b82f6'; // blue
    if (importance >= 0.4) return '#f59e0b'; // yellow
    return '#64748b'; // muted
  };

  if (isLoading && memoryEvents.length === 0) {
    return (
      <div className={`${styles.container} ${className}`}>
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <Icon icon={Icons.memory} size="md" />
            <span>Recent Memory</span>
          </div>
          <div className={styles.loading}>
            <Icon icon={Icons.spinner} size="md" className="spin" />
          </div>
        </div>
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <Icon icon={Icons.bolt} size="md" />
            <span>Capabilities</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.container} ${className}`}>
      {/* Memory Section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <Icon icon={Icons.memory} size="md" />
          <span>Recent Memory</span>
          <button
            className={styles.refreshBtn}
            onClick={loadData}
            title="Refresh"
          >
            <Icon icon={Icons.refresh} size="sm" />
          </button>
        </div>
        <div className={styles.memoryList}>
          {memoryEvents.length === 0 ? (
            <div className={styles.empty}>
              <Icon icon={Icons.inbox} size="lg" />
              <p>No events yet</p>
            </div>
          ) : (
            memoryEvents.map((event) => (
              <div key={event.id} className={styles.memoryItem}>
                <div className={styles.memoryHeader}>
                  <span className={styles.memoryType}>{event.type || 'event'}</span>
                  <span className={styles.memoryTime}>
                    {formatDate(event.timestamp)}
                  </span>
                </div>
                <div
                  className={styles.memoryContent}
                  title={event.content}
                >
                  {event.content?.substring(0, 80)}
                  {event.content && event.content.length > 80 ? '...' : ''}
                </div>
                <div className={styles.memoryFooter}>
                  <div
                    className={styles.importanceBadge}
                    style={{
                      background: getImportanceColor(event.importance || 0.5),
                      opacity: (event.importance || 0.5) * 0.8 + 0.2
                    }}
                  >
                    {(event.importance || 0.5) * 100}%
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Capabilities Section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <Icon icon={Icons.bolt} size="md" />
          <span>Capabilities</span>
        </div>
        <div className={styles.capabilitiesList}>
          {Object.entries(capabilities).map(([name, score]) => (
            <div key={name} className={styles.capabilityItem}>
              <div className={styles.capabilityHeader}>
                <span className={styles.capabilityName}>
                  {name.charAt(0).toUpperCase() + name.slice(1)}
                </span>
                <span className={styles.capabilityScore}>
                  {(score * 100).toFixed(0)}%
                </span>
              </div>
              <div className={styles.progressTrack}>
                <div
                  className={styles.progressFill}
                  style={{
                    width: `${score * 100}%`,
                    background: getCapabilityColor(score)
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Status Section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <Icon icon={Icons.info} size="md" />
          <span>Status</span>
        </div>
        <div className={styles.statusList}>
          <div className={styles.statusItem}>
            <div className={`${styles.statusDot} ${styles.online}`} />
            <span>System Online</span>
          </div>
          <div className={styles.statusItem}>
            <Icon icon={Icons.toolCount} size="sm" />
            <span>24 Tools</span>
          </div>
          <div className={styles.statusItem}>
            <Icon icon={Icons.memory} size="sm" />
            <span>{memoryEvents.length} Events</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RightPanel;
