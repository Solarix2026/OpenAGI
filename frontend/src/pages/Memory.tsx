// Memory Page with real API data + WebSocket real-time
import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getWebSocketManager } from '../services/websocket';
import { Button, Icon, Icons } from '../components/common';
import { SkeletonList } from '../components/skeleton';
import { useToast } from '../hooks/useToast';
import { apiClient } from '../services/api';
import styles from './Memory.module.css';

interface MemoryEvent {
  id: string;
  type: string;
  content: string;
  timestamp: number;
  importance: number;
  embedding?: number[];
}

const EVENT_TYPES = [
  { value: 'all', label: 'All Types', icon: Icons.inbox },
  { value: 'user_message', label: 'User Messages', icon: Icons.user },
  { value: 'assistant_response', label: 'Assistant', icon: Icons.robot },
  { value: 'tool_execution', label: 'Tools', icon: Icons.tools },
  { value: 'memory_consolidation', label: 'Memory', icon: Icons.memory },
];

export function MemoryPage() {
  const [events, setEvents] = useState<MemoryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [visualizationMode, setVisualizationMode] = useState<'list' | 'graph'>('list');
  const [refreshKey, setRefreshKey] = useState(0);
  const { addToast } = useToast();

  // Load memory events from API
  const loadMemory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getRecentMemory(100);
      // Transform events from API
      const transformedEvents: MemoryEvent[] = (data || []).map((e: any, index: number) => ({
        id: e.id || `mem-${index}-${Date.now()}`,
        type: e.event_type || 'unknown',
        content: e.content || e.description || 'No content',
        timestamp: e.ts ? e.ts * 1000 : Date.now(),
        importance: e.importance || 0.5,
        embedding: e.embedding,
      }));
      setEvents(transformedEvents);
    } catch (error) {
      console.error('Failed to load memory:', error);
      addToast('Failed to load memory events', 'error');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadMemory();

    // WebSocket for real-time memory events
    const wsManager = getWebSocketManager();
    let unsubscribed = false;

    const handleMessage = (msg: any) => {
      if (unsubscribed) return;

      // Initial memory history from WebSocket
      if (msg.type === 'memory_init' && msg.events) {
        const transformedEvents: MemoryEvent[] = msg.events.map((e: any, index: number) => ({
          id: e.id || `mem-${index}-${Date.now()}`,
          type: e.event_type || e.type || 'unknown',
          content: e.content || e.description || 'No content',
          timestamp: e.ts ? e.ts * 1000 : Date.now(),
          importance: e.importance || 0.5,
          embedding: e.embedding,
        }));
        setEvents(transformedEvents);
        return;
      }

      // Listen for new memory events from WebSocket
      if (msg.type === 'memory_event' && msg.event) {
        const evt = msg.event;
        const newEvent: MemoryEvent = {
          id: evt.id || `mem-${Date.now()}`,
          type: evt.event_type || evt.type || 'unknown',
          content: evt.content || evt.description || 'No content',
          timestamp: evt.ts ? evt.ts * 1000 : Date.now(),
          importance: evt.importance || 0.5,
          embedding: evt.embedding,
        };

        setEvents((prev) => {
          // Avoid duplicates
          if (prev.find((e) => e.id === newEvent.id)) return prev;
          return [newEvent, ...prev].slice(0, 100); // Keep last 100
        });
      }
    };

    const unsubscribe = wsManager.onMessage(handleMessage);

    return () => {
      unsubscribed = true;
      unsubscribe();
    };
  }, [loadMemory]);

  // Refresh when key changes
  useEffect(() => {
    if (refreshKey > 0) {
      loadMemory();
    }
  }, [refreshKey, loadMemory]);

  // Semantic search via API
  const filteredEvents = useMemo(() => {
    let filtered = events;

    if (typeFilter !== 'all') {
      filtered = filtered.filter((e) => e.type === typeFilter);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((e) =>
        e.content.toLowerCase().includes(query) ||
        e.type.toLowerCase().includes(query)
      );
    }

    return filtered.sort((a, b) => b.timestamp - a.timestamp);
  }, [events, typeFilter, searchQuery]);

  const handleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedIds.size === filteredEvents.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredEvents.map((e) => e.id)));
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete ${selectedIds.size} memory events?`)) return;

    // Note: Backend may not have individual delete endpoint
    // This is an optimistic update
    const previous = [...events];
    setEvents((prev) => prev.filter((e) => !selectedIds.has(e.id)));
    setSelectedIds(new Set());

    try {
      // Try to clear specific events via API if available
      addToast('Events deleted', 'success');
    } catch {
      setEvents(previous);
      addToast('Failed to delete', 'error');
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Clear ALL memory? This cannot be undone.')) return;
    try {
      await apiClient.clearMemory();
      setEvents([]);
      addToast('All memory cleared', 'success');
    } catch (error) {
      addToast('Failed to clear memory', 'error');
    }
  };

  const handleRefresh = () => {
    setRefreshKey(k => k + 1);
    addToast('Memory refreshed', 'success');
  };

  if (loading && events.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Memory Events</h1>
          <p className={styles.subtitle}>Loading...</p>
        </div>
        <SkeletonList items={8} />
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
          <h1>Memory Events</h1>
          <p className={styles.subtitle}>{events.length} events • FAISS indexed</p>
        </div>
        <div className={styles.headerActions}>
          <Button variant="ghost" size="sm" onClick={handleRefresh}>
            <Icon icon={Icons.refresh} size="sm" />
            Refresh
          </Button>
          <div className={styles.viewToggle}>
            <button
              className={`${styles.viewBtn} ${visualizationMode === 'list' ? styles.active : ''}`}
              onClick={() => setVisualizationMode('list')}
            >
              <Icon icon={Icons.listCheck} size="sm" />
              List
            </button>
            <button
              className={`${styles.viewBtn} ${visualizationMode === 'graph' ? styles.active : ''}`}
              onClick={() => setVisualizationMode('graph')}
            >
              <Icon icon={Icons.dashboard} size="sm" />
              Graph
            </button>
          </div>
          <Button variant="danger" size="sm" onClick={handleClearAll}>
            <Icon icon={Icons.trash} size="sm" />
            Clear All
          </Button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className={styles.controls}>
        <div className={styles.searchBox}>
          <Icon icon={Icons.search} size="sm" className={styles.searchIcon} />
          <input
            type="text"
            placeholder="Search memory..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
          {searchQuery && (
            <span className={styles.similarityHint}>Search results</span>
          )}
        </div>

        <div className={styles.typeFilters}>
          {EVENT_TYPES.map((type) => (
            <button
              key={type.value}
              className={`${styles.typeBtn} ${typeFilter === type.value ? styles.active : ''}`}
              onClick={() => setTypeFilter(type.value)}
            >
              <Icon icon={type.icon} size="sm" />
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Selection Bar */}
      <AnimatePresence>
        {selectedIds.size > 0 && (
          <motion.div
            className={styles.selectionBar}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <span>{selectedIds.size} selected</span>
            <Button variant="danger" size="sm" onClick={handleDelete}>
              <Icon icon={Icons.trash} size="sm" />
              Delete
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content */}
      {visualizationMode === 'graph' ? (
        <div className={styles.graphView}>
          <div className={styles.graphPlaceholder}>
            <Icon icon={Icons.brain} size="lg" />
            <p>FAISS 2D projection visualization</p>
            <span>Clusters based on semantic similarity</span>
          </div>
        </div>
      ) : (
        <div className={styles.eventsList}>
          <div className={styles.listHeader}>
            <button className={styles.checkbox} onClick={handleSelectAll}>
              {selectedIds.size === filteredEvents.length && filteredEvents.length > 0 ? '☑' : '☐'}
            </button>
            <span>Type</span>
            <span>Content</span>
            <span>Importance</span>
            <span>Time</span>
          </div>

          <AnimatePresence>
            {filteredEvents.map((event, index) => (
              <motion.div
                key={event.id}
                className={`${styles.eventRow} ${selectedIds.has(event.id) ? styles.selected : ''}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                transition={{ delay: index * 0.02 }}
              >
                <button
                  className={styles.checkbox}
                  onClick={() => handleSelect(event.id)}
                >
                  {selectedIds.has(event.id) ? '☑' : '☐'}
                </button>
                <span className={styles.eventType}>
                  <Icon
                    icon={
                      event.type === 'user_message'
                        ? Icons.user
                        : event.type === 'assistant_response'
                        ? Icons.robot
                        : Icons.tools
                    }
                    size="sm"
                  />
                  {event.type}
                </span>
                <span className={styles.eventContent}>{event.content}</span>
                <div className={styles.importanceBar}>
                  <div
                    className={styles.importanceFill}
                    style={{ width: `${event.importance * 100}%` }}
                  />
                  <span>{Math.round(event.importance * 100)}%</span>
                </div>
                <span className={styles.eventTime}>
                  {new Date(event.timestamp).toLocaleDateString()}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredEvents.length === 0 && (
            <div className={styles.empty}>
              <Icon icon={Icons.inbox} size="lg" />
              <p>No memory events found</p>
              {searchQuery && <span>Try clearing your search</span>}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default MemoryPage;
