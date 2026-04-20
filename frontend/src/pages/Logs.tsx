// Logs Page with real-time WebSocket + REST API logs
import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FixedSizeList as List } from 'react-window';
import { getWebSocketManager } from '../services/websocket';
import { apiClient } from '../services/api';
import { Button, Icon, Icons } from '../components/common';
import { SkeletonList } from '../components/skeleton';
import { useToast } from '../hooks/useToast';
import styles from './Logs.module.css';

interface LogEntry {
  id: string;
  timestamp: number;
  level: 'debug' | 'info' | 'warning' | 'error';
  module: string;
  message: string;
  details?: string;
}

const LOG_LEVELS = [
  { value: 'all', label: 'All Levels', color: 'var(--text)' },
  { value: 'debug', label: 'Debug', color: 'var(--text-muted)' },
  { value: 'info', label: 'Info', color: 'var(--blue)' },
  { value: 'warning', label: 'Warning', color: 'var(--yellow)' },
  { value: 'error', label: 'Error', color: 'var(--red)' },
] as const;

const levelColors: Record<string, string> = {
  debug: 'var(--text-muted)',
  info: 'var(--blue)',
  warning: 'var(--yellow)',
  error: 'var(--red)',
};

const levelBgColors: Record<string, string> = {
  debug: 'rgba(148, 163, 184, 0.1)',
  info: 'rgba(59, 130, 246, 0.1)',
  warning: 'rgba(245, 158, 11, 0.1)',
  error: 'rgba(239, 68, 68, 0.1)',
};

export function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [modules, setModules] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const [moduleFilter, setModuleFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const { addToast } = useToast();
  const listRef = useRef<List>(null);
  const logsRef = useRef<LogEntry[]>([]);
  const [newLogCount, setNewLogCount] = useState(0);

  // Keep ref in sync for the row renderer
  logsRef.current = logs;

  // Fetch logs via REST API
  const fetchLogs = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/logs?level=${levelFilter}&module=${moduleFilter}&limit=500`
      );
      if (!response.ok) throw new Error('Failed to fetch logs');
      const data = await response.json();

      if (data.logs) {
        // Transform API format to LogEntry
        const transformed: LogEntry[] = data.logs.map((l: any) => ({
          id: l.id || `log-${l.timestamp}`,
          timestamp: l.timestamp || Date.now(),
          level: l.level || 'info',
          module: l.module || 'Unknown',
          message: l.message || 'No message',
          details: l.details,
        }));
        setLogs(transformed);
      }
      if (data.modules) {
        setModules(data.modules);
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error);
      addToast('Failed to fetch logs from server', 'error');
    }
  }, [levelFilter, moduleFilter, addToast]);

  // Initial load via REST API
  useEffect(() => {
    const loadInitial = async () => {
      setLoading(true);
      await fetchLogs();
      setLoading(false);
    };
    loadInitial();
  }, [fetchLogs]);

  // Subscribe to real-time WebSocket logs
  useEffect(() => {
    const wsManager = getWebSocketManager();
    let unsubscribed = false;

    const handleMessage = (msg: any) => {
      if (unsubscribed) return;

      // Initial history from WebSocket
      if (msg.type === 'log' && msg.log) {
        const logData = msg.log;
        const entry: LogEntry = {
          id: logData.id || `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: logData.timestamp || Date.now(),
          level: logData.level || 'info',
          module: logData.module || 'Unknown',
          message: logData.message || 'No message',
          details: logData.details,
        };

        setLogs((prev) => {
          // Avoid duplicates
          if (prev.find((l) => l.id === entry.id)) return prev;
          const newLogs = [...prev, entry];
          // Keep last 1000 logs
          if (newLogs.length > 1000) {
            return newLogs.slice(newLogs.length - 1000);
          }
          return newLogs;
        });

        // Auto-scroll on new log if enabled
        if (isAutoScroll) {
          setTimeout(() => {
            if (listRef.current) {
              listRef.current.scrollToItem(newLogs.length - 1, 'end');
            }
          }, 50);
        } else {
          setNewLogCount((c) => c + 1);
        }
      }
    };

    const unsubscribe = wsManager.onMessage(handleMessage);

    return () => {
      unsubscribed = true;
      unsubscribe();
    };
  }, [isAutoScroll]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (isAutoScroll && listRef.current && !loading && filteredLogs.length > 0) {
      listRef.current.scrollToItem(filteredLogs.length - 1, 'end');
    }
  }, [logs, isAutoScroll, loading, filteredLogs.length]);

  // Filter logs client-side
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch =
        !searchQuery ||
        log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.module.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSearch;
    });
  }, [logs, searchQuery]);

  const handleClear = async () => {
    if (!confirm('Clear all logs?')) return;
    try {
      const response = await fetch('/api/logs/clear', { method: 'POST' });
      if (!response.ok) throw new Error('Failed to clear logs');
      setLogs([]);
      addToast('Logs cleared', 'success');
    } catch (error) {
      addToast('Failed to clear logs', 'error');
    }
  };

  const handleExport = () => {
    const data = JSON.stringify(filteredLogs, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    addToast('Logs exported', 'success');
  };

  const handleScrollToBottom = () => {
    if (listRef.current) {
      listRef.current.scrollToItem(filteredLogs.length - 1, 'end');
      setNewLogCount(0);
    }
  };

  // Row renderer for virtual list
  const LogRow = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const log = filteredLogs[index];
    if (!log) return null;

    const timestamp = new Date(log.timestamp);
    const isToday = timestamp.toDateString() === new Date().toDateString();
    const timeStr = timestamp.toLocaleTimeString([], {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    const dateStr = timestamp.toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
    });

    return (
      <div style={style}>
        <motion.div
          className={styles.logRow}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: Math.min(index * 0.005, 0.3) }}
          onClick={() => setSelectedLog(log)}
        >
          <span className={styles.logTime}>
            {isToday ? timeStr : `${dateStr} ${timeStr}`}
          </span>
          <span
            className={styles.logLevel}
            style={{
              color: levelColors[log.level],
              background: levelBgColors[log.level],
            }}
          >
            {log.level.toUpperCase()}
          </span>
          <span className={styles.logModule}>[{log.module}]</span>
          <span className={styles.logMessage}>{log.message}</span>
        </motion.div>
      </div>
    );
  }, [filteredLogs]);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>System Logs</h1>
          <SkeletonList items={10} />
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className={styles.container}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className={styles.header}>
        <div>
          <h1>System Logs</h1>
          <p className={styles.subtitle}>
            {filteredLogs.length} entries • Real-time from WebSocket
          </p>
        </div>
        <div className={styles.headerActions}>
          <button
            className={`${styles.autoScrollBtn} ${isAutoScroll ? styles.active : ''}`}
            onClick={() => setIsAutoScroll(!isAutoScroll)}
          >
            <Icon icon={isAutoScroll ? Icons.check : Icons.more} size="sm" />
            Auto-scroll
          </button>
          <Button variant="secondary" size="sm" onClick={handleExport}>
            <Icon icon={Icons.download} size="sm" />
            Export
          </Button>
          <Button variant="danger" size="sm" onClick={handleClear}>
            <Icon icon={Icons.trash} size="sm" />
            Clear
          </Button>
        </div>
      </div>

      {/* New logs notification */}
      {newLogCount > 0 && !isAutoScroll && (
        <motion.div
          className={styles.newLogsNotification}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={handleScrollToBottom}
        >
          {newLogCount} new log{newLogCount > 1 ? 's' : ''}
          <Icon icon={Icons.chevronDown} size="sm" />
        </motion.div>
      )}

      {/* Filters */}
      <motion.div className={styles.filters} layout>
        <div className={styles.filterGroup}>
          <label>Level</label>
          <div className={styles.filterButtons}>
            {LOG_LEVELS.map((level) => (
              <button
                key={level.value}
                className={`${styles.filterBtn} ${levelFilter === level.value ? styles.active : ''}`}
                onClick={() => setLevelFilter(level.value)}
                style={{ '--filter-color': level.color } as React.CSSProperties}
              >
                {level.label}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.filterGroup}>
          <label>Module</label>
          <select
            className={styles.select}
            value={moduleFilter}
            onChange={(e) => setModuleFilter(e.target.value)}
          >
            <option value="all">All Modules</option>
            {modules.map((mod) => (
              <option key={mod} value={mod}>
                {mod}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label>Search</label>
          <div className={styles.searchInput}>
            <Icon icon={Icons.search} size="sm" />
            <input
              type="text"
              placeholder="Filter logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </motion.div>

      {/* Log List */}
      <div className={styles.logList}>
        <div className={styles.logHeader}>
          <span className={styles.headerTime}>Time</span>
          <span className={styles.headerLevel}>Level</span>
          <span className={styles.headerModule}>Module</span>
          <span className={styles.headerMessage}>Message</span>
        </div>
        {filteredLogs.length === 0 ? (
          <div className={styles.empty}>
            <Icon icon={Icons.inbox} size="lg" />
            <p>No logs match your filters</p>
            {levelFilter !== 'all' && (
              <button
                className={styles.resetBtn}
                onClick={() => setLevelFilter('all')}
              >
                Reset filters
              </button>
            )}
          </div>
        ) : (
          <List
            ref={listRef}
            height={400}
            itemCount={filteredLogs.length}
            itemSize={40}
            width="100%"
            className={styles.virtualList}
          >
            {LogRow}
          </List>
        )}
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedLog && (
          <motion.div
            className={styles.modalOverlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedLog(null)}
          >
            <motion.div
              className={styles.modal}
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className={styles.modalHeader}>
                <h3>Log Details</h3>
                <button className={styles.modalClose} onClick={() => setSelectedLog(null)}>
                  ×
                </button>
              </div>
              <div className={styles.modalContent}>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Timestamp</span>
                  <span className={styles.detailValue}>
                    {new Date(selectedLog.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Level</span>
                  <span
                    className={styles.detailValue}
                    style={{ color: levelColors[selectedLog.level] }}
                  >
                    {selectedLog.level.toUpperCase()}
                  </span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Module</span>
                  <span className={styles.detailValue}>{selectedLog.module}</span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Message</span>
                  <pre className={styles.detailMessage}>{selectedLog.message}</pre>
                </div>
                {selectedLog.details && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Details</span>
                    <pre className={styles.detailDetails}>{selectedLog.details}</pre>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default LogsPage;
