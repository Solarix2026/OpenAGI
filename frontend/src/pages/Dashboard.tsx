// Dashboard Page V2 with interactive charts, animations, and real-time updates
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useWebSocket } from '../context/WebSocketContext';
import { apiClient } from '../services/api';
import { MetricCard, RingProgress, QuickStat } from '../components/dashboard';
import { ActivityTimeline } from '../components/charts/ActivityTimeline';
import { InteractiveRadar } from '../components/dashboard';
import { SkeletonDashboard } from '../components/skeleton';
import { useDashboardStore } from '../store/appStore';
import styles from './Dashboard.module.css';
import { Icons } from '../components/common';
import type { SystemStatus, Capabilities, MemoryEvent } from '../types';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] },
  },
};

export function DashboardPage() {
  const { isConnected, send: wsSend } = useWebSocket();
  const { isLoading: storeLoading, setLoading: setStoreLoading } = useDashboardStore();
  const [status, setStatus] = useState<SystemStatus>({
    online: true,
    uptime: '0h 0m',
    toolCount: 0,
    activeTools: 0,
    memorySize: 0,
    memoryUsage: 0,
    avgResponseTime: 0,
    requestsPerMin: 0,
    apiKeysSet: { groq: false, nvidia: false },
  });
  const [capabilities, setCapabilities] = useState<Capabilities>({
    memory: 80,
    reasoning: 75,
    planning: 70,
    coding: 85,
    computer: 70,
    browser: 65,
    evolution: 70,
  });
  const [recentMemory, setRecentMemory] = useState<MemoryEvent[]>([]);
  const [selectedDimension, setSelectedDimension] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statusData, capabilitiesData, memoryData] = await Promise.all([
        apiClient.getStatus().catch(() => null),
        apiClient.getCapabilities().catch(() => null),
        apiClient.getRecentMemory(8).catch(() => []),
      ]);

      if (statusData) {
        setStatus({
          online: statusData.online ?? true,
          uptime: statusData.uptime ?? '0h 0m',
          toolCount: statusData.toolCount ?? 24,
          activeTools: statusData.activeTools ?? 3,
          memorySize: statusData.memorySize ?? 0,
          memoryUsage: statusData.memoryUsage ?? 0,
          avgResponseTime: statusData.avgResponseTime ?? 0,
          requestsPerMin: statusData.requestsPerMin ?? 0,
          apiKeysSet: statusData.apiKeysSet ?? { groq: false, nvidia: false },
        });
      }

      if (capabilitiesData) {
        setCapabilities(capabilitiesData);
      }

      if (memoryData && Array.isArray(memoryData)) {
        setRecentMemory(memoryData.slice(0, 8));
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
      setStoreLoading(false);
    }
  }, [setStoreLoading]);

  // Initial load
  useEffect(() => {
    setStoreLoading(true);
    loadData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      setRefreshKey(k => k + 1);
    }, 30000);

    return () => clearInterval(interval);
  }, [loadData, setStoreLoading]);

  // Re-fetch when refresh key changes
  useEffect(() => {
    if (refreshKey > 0) {
      loadData();
    }
  }, [refreshKey, loadData]);

  const handleManualRefresh = () => {
    setRefreshKey(k => k + 1);
  };

  const handleDimensionClick = (dimension: string) => {
    setSelectedDimension(dimension);
  };

  // Quick action handlers
  const handleQuickAction = (command: string) => {
    wsSend(command);
  };

  // Generate sparkline data (mock)
  const generateSparkline = (base: number) => {
    return Array.from({ length: 10 }, (_, i) => {
      const variation = Math.sin(i * 0.5) * 10 + Math.random() * 5;
      return Math.max(0, Math.min(100, base + variation));
    });
  };

  // Quick stats data
  const quickStats = [
    { icon: Icons.bolt, value: status.activeTools, label: 'Active Tools', color: 'green' },
    { icon: Icons.memory, value: Math.floor(status.memorySize / 1024), label: 'MB Memory', color: 'cyan' },
    { icon: Icons.timer, value: status.avgResponseTime, label: 'ms Avg Response', color: 'blue' },
    { icon: Icons.dashboard, value: status.requestsPerMin, label: 'Req/Min', color: 'purple' },
  ];

  if (loading || storeLoading) {
    return <SkeletonDashboard />;
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <motion.header
        className={styles.header}
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className={styles.headerLeft}>
          <h1>Dashboard</h1>
          <p className={styles.subtitle}>System overview and performance metrics</p>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.connectionStatus}>
            <span className={`${styles.statusDot} ${isConnected ? styles.online : styles.offline}`} />
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
          <button className={styles.refreshBtn} onClick={handleManualRefresh}>
            <svg viewBox="0 0 24 24" className={styles.refreshIcon}>
              <path
                fill="currentColor"
                d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
              />
            </svg>
            Refresh
          </button>
        </div>
      </motion.header>

      {/* Main Grid */}
      <motion.div
        className={styles.grid}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Metric Cards Row */}
        <motion.div className={styles.metricsRow} variants={itemVariants}>
          <MetricCard
            title="System Health"
            value={status.online ? '🟢 Online' : '🔴 Offline'}
            subvalue={`Uptime: ${status.uptime}`}
            icon={Icons.check}
            color={status.online ? 'green' : 'red'}
            trend="neutral"
            sparklineData={generateSparkline(95)}
          />
          <MetricCard
            title="Available Tools"
            value={status.toolCount}
            subvalue={`${status.activeTools} active now`}
            icon={Icons.tools}
            color="blue"
            trend="up"
            trendValue="+2 today"
            sparklineData={generateSparkline(status.toolCount * 4)}
          />
          <MetricCard
            title="Memory Usage"
            value={`${(status.memorySize / 1024 / 1024).toFixed(1)}MB`}
            subvalue={`${Math.floor(status.memoryUsage || 0)}% of total`}
            icon={Icons.memory}
            color="cyan"
            sparklineData={generateSparkline(status.memoryUsage || 50)}
          />
          <MetricCard
            title="Performance"
            value={`${status.avgResponseTime || 0}ms`}
            subvalue={`${status.requestsPerMin || 0} req/min`}
            icon={Icons.bolt}
            color="purple"
            trend="up"
            trendValue="-15%"
            sparklineData={generateSparkline(100 - (status.avgResponseTime || 0) / 10)}
          />
        </motion.div>

        {/* Capability Radar & Activity Combined Row */}
        <motion.div className={styles.visualRow} variants={itemVariants}>
          <div className={styles.radarSection}>
            <div className={styles.sectionHeader}>
              <h2>Capability Matrix</h2>
              <p>Agent capabilities across all dimensions</p>
            </div>
            {selectedDimension && (
              <div className={styles.dimensionInfo}>
                <strong>{selectedDimension}</strong>: {capabilities[selectedDimension as keyof Capabilities]}/100
              </div>
            )}
            <InteractiveRadar
              data={{
                'Reasoning': capabilities.reasoning,
                'Knowledge': capabilities.memory,
                'Execution': capabilities.computer,
                'Memory': capabilities.memory,
                'Learning': capabilities.evolution,
                'Vision': capabilities.browser,
                'Autonomy': capabilities.planning,
              }}
              onDimensionClick={handleDimensionClick}
            />
          </div>

          <div className={styles.activitySection}>
            <div className={styles.sectionHeader}>
              <h2>Quick Stats</h2>
              <p>Key performance indicators</p>
            </div>
            <div className={styles.quickStatsGrid}>
              {quickStats.map((stat, idx) => (
                <QuickStat key={idx} {...stat} />
              ))}
            </div>
            <div className={styles.ringGrid}>
              <RingProgress
                value={status.memoryUsage || 0}
                size={70}
                color="var(--cyan)"
                label="Memory"
              />
              <RingProgress
                value={75}
                size={70}
                color="var(--green)"
                label="Health"
              />
              <RingProgress
                value={Math.min(100, (status.activeTools / Math.max(status.toolCount, 1)) * 100)}
                size={70}
                color="var(--blue)"
                label="Tools"
              />
            </div>
          </div>
        </motion.div>

        {/* Activity Timeline */}
        <motion.div className={styles.activityRow} variants={itemVariants}>
          <div className={styles.sectionHeader}>
            <h2>Recent Activity</h2>
            <p>Recent system events and memory logs</p>
          </div>
          <div className={styles.activityContent}>
            <ActivityTimeline events={recentMemory} />
          </div>
        </motion.div>

        {/* Quick Actions */}
        <motion.div className={styles.actionsRow} variants={itemVariants}>
          <div className={styles.sectionHeader}>
            <h2>Quick Actions</h2>
            <p>Common tasks and system operations</p>
          </div>
          <div className={styles.actionButtons}>
            <motion.button
              className={`${styles.actionBtn} ${styles.actionBtnPrimary}`}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleQuickAction('morning briefing')}
            >
              <svg viewBox="0 0 24 24" className={styles.actionIcon}>
                <path fill="currentColor" d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"/>
              </svg>
              Morning Briefing
            </motion.button>
            <motion.button
              className={styles.actionBtn}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleQuickAction('status')}
            >
              <svg viewBox="0 0 24 24" className={styles.actionIcon}>
                <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
              </svg>
              System Status
            </motion.button>
            <motion.button
              className={styles.actionBtn}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleQuickAction('what is happening in the world')}
            >
              <svg viewBox="0 0 24 24" className={styles.actionIcon}>
                <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
              </svg>
              World Events
            </motion.button>
            <motion.button
              className={styles.actionBtn}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleQuickAction('evolve')}
            >
              <svg viewBox="0 0 24 24" className={styles.actionIcon}>
                <path fill="currentColor" d="M4 14v8h16v-8H4zm14 4H6v-2h12v2zM4 .756l5.725 5.725L4 8.806V.756zm7 0v8.05l5.725-2.325L11 .756z"/>
              </svg>
              Run Evolution
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}

export default DashboardPage;
