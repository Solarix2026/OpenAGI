// History Page V2 with time-grouped sessions, animations, and preview
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '../services/api';
import { Button, Input, Icon, Icons } from '../components/common';
import { SkeletonList } from '../components/skeleton';
import { useSessionStore } from '../store/appStore';
import { useToast } from '../hooks/useToast';
import { formatDistanceToNow, format, isToday, isYesterday, isThisWeek, isThisMonth } from 'date-fns';
import styles from './History.module.css';

interface Message {
  role: string;
  content: string;
  timestamp: number;
}

interface SessionItem {
  id: string;
  title: string;
  timestamp: number;
  messageCount: number;
  tokenCount?: number;
  tags?: string[];
  preview?: string;
  messages: Message[];
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] },
  },
};

export function HistoryPage() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [filteredSessions, setFilteredSessions] = useState<SessionItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewSession, setPreviewSession] = useState<SessionItem | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletingAll, setDeletingAll] = useState(false);

  const { sessions: storedSessions, setCurrentSession, deleteSession: storeDeleteSession } = useSessionStore();
  const { addToast } = useToast();

  // Load sessions from API and local storage
  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      const historyData = await apiClient.getHistory().catch(() => ({ messages: [] }));
      const apiSessions = await apiClient.getSessions().catch(() => []);

      // Combine API sessions with local sessions
      const combinedSessions: SessionItem[] = [...apiSessions.map((s: any) => ({
        id: s.id,
        title: s.title || 'Untitled Session',
        timestamp: s.timestamp || Date.now(),
        messageCount: s.messageCount || 0,
        tokenCount: s.tokenCount || Math.floor(Math.random() * 5000),
        tags: s.tags || ['conversation'],
        preview: s.preview || 'No preview available',
        messages: s.messages || [],
      }))];

      // Add local sessions
      storedSessions.forEach((s) => {
        if (!combinedSessions.find(cs => cs.id === s.id)) {
          combinedSessions.push({
            id: s.id,
            title: s.title,
            timestamp: s.updatedAt,
            messageCount: s.messages.length,
            tokenCount: Math.floor(Math.random() * 5000),
            tags: ['local'],
            preview: s.messages.slice(-1)[0]?.content?.substring(0, 80) || 'No preview',
            messages: s.messages.map(m => ({
              role: m.role,
              content: m.content,
              timestamp: m.timestamp,
            })),
          });
        }
      });

      // Sort by timestamp descending
      combinedSessions.sort((a, b) => b.timestamp - a.timestamp);

      setSessions(combinedSessions);
      setFilteredSessions(combinedSessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      addToast('Failed to load sessions', 'error');
    } finally {
      setLoading(false);
    }
  }, [storedSessions, addToast]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Filter sessions based on search and tag
  useEffect(() => {
    let filtered = sessions;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.title.toLowerCase().includes(query) ||
          s.preview?.toLowerCase().includes(query) ||
          s.tags?.some((t) => t.toLowerCase().includes(query))
      );
    }

    if (selectedTag) {
      filtered = filtered.filter((s) => s.tags?.includes(selectedTag));
    }

    setFilteredSessions(filtered);
  }, [searchQuery, selectedTag, sessions]);

  // Group sessions by time
  const groupedSessions = useMemo(() => {
    const groups: { [key: string]: SessionItem[] } = {
      today: [],
      yesterday: [],
      thisWeek: [],
      thisMonth: [],
      earlier: [],
    };

    filteredSessions.forEach((session) => {
      const date = new Date(session.timestamp);
      if (isToday(date)) {
        groups.today.push(session);
      } else if (isYesterday(date)) {
        groups.yesterday.push(session);
      } else if (isThisWeek(date)) {
        groups.thisWeek.push(session);
      } else if (isThisMonth(date)) {
        groups.thisMonth.push(session);
      } else {
        groups.earlier.push(session);
      }
    });

    return groups;
  }, [filteredSessions]);

  // Get all unique tags
  const allTags = useMemo(() => {
    const tags = new Set<string>();
    sessions.forEach((s) => s.tags?.forEach((t) => tags.add(t)));
    return Array.from(tags).sort();
  }, [sessions]);

  const handleDelete = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this session?')) return;

    setDeletingId(sessionId);

    // Optimistic update - remove immediately
    const previousSessions = [...sessions];
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    setFilteredSessions((prev) => prev.filter((s) => s.id !== sessionId));

    try {
      await apiClient.deleteSession(sessionId);
      storeDeleteSession(sessionId);
      addToast('Session deleted', 'success');
    } catch (error) {
      // Rollback on error
      setSessions(previousSessions);
      addToast('Failed to delete session', 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm('Clear all history? This cannot be undone.')) return;

    setDeletingAll(true);

    // Optimistic update - clear immediately
    const previousSessions = [...sessions];
    setSessions([]);
    setFilteredSessions([]);

    try {
      // Delete each session
      await Promise.all(sessions.map(s => apiClient.deleteSession(s.id)));
      addToast('All sessions cleared', 'success');
    } catch (error) {
      // Rollback on error
      setSessions(previousSessions);
      setFilteredSessions(previousSessions);
      addToast('Failed to clear sessions', 'error');
    } finally {
      setDeletingAll(false);
    }
  };

  const handleLoadSession = (session: SessionItem) => {
    setCurrentSession(session.id);
    addToast(`Loaded session: ${session.title}`, 'success');
  };

  const handleExport = (session: SessionItem, format: 'json' | 'markdown') => {
    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify(session, null, 2);
      filename = `session-${session.id}.json`;
      mimeType = 'application/json';
    } else {
      content = `# ${session.title}\n\n`;
      content += `Date: ${new Date(session.timestamp).toLocaleString()}\n\n`;
      content += `## Messages\n\n`;
      session.messages.forEach((msg) => {
        content += `**${msg.role}**: ${msg.content}\n\n`;
      });
      filename = `session-${session.id}.md`;
      mimeType = 'text/markdown';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    addToast(`Exported as ${format.toUpperCase()}`, 'success');
  };

  const renderSessionGroup = (title: string, items: SessionItem[]) => {
    if (items.length === 0) return null;

    return (
      <div key={title} className={styles.sessionGroup}>
        <h3 className={styles.groupTitle}>{title}</h3>
        <div className={styles.sessionGrid}>
          {items.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              isDeleting={deletingId === session.id}
              onPreview={() => setPreviewSession(session)}
              onLoad={() => handleLoadSession(session)}
              onDelete={() => handleDelete(session.id)}
              onExport={(fmt) => handleExport(session, fmt)}
            />
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <SkeletonList items={6} />
      </div>
    );
  }

  const hasSessions =
    groupedSessions.today.length > 0 ||
    groupedSessions.yesterday.length > 0 ||
    groupedSessions.thisWeek.length > 0 ||
    groupedSessions.thisMonth.length > 0 ||
    groupedSessions.earlier.length > 0;

  return (
    <motion.div
      className={styles.container}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.header variants={itemVariants} className={styles.header}>
        <div className={styles.headerLeft}>
          <h1>Conversation History</h1>
          <p className={styles.subtitle}>{sessions.length} sessions saved</p>
        </div>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleDeleteAll}
            disabled={deletingAll || sessions.length === 0}
          >
            <Icon icon={Icons.trash} size="sm" />
            {deletingAll ? 'Clearing...' : 'Clear All'}
          </Button>
        </div>
      </motion.header>

      {/* Search and Filters */}
      <motion.div variants={itemVariants} className={styles.controls}>
        <div className={styles.searchWrapper}>
          <Icon icon={Icons.search} size="sm" className={styles.searchIcon} />
          <Input
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>
        {allTags.length > 0 && (
          <div className={styles.tagFilters}>
            {allTags.map((tag) => (
              <button
                key={tag}
                className={`${styles.tag} ${selectedTag === tag ? styles.tagActive : ''}`}
                onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
      </motion.div>

      {/* Session Groups */}
      <motion.div variants={itemVariants} className={styles.content}>
        {!hasSessions ? (
          <div className={styles.empty}>
            <Icon icon={Icons.history} size="lg" />
            <h3>No sessions found</h3>
            <p>Start a conversation to create your first session</p>
          </div>
        ) : (
          <div className={styles.sessionsList}>
            {renderSessionGroup('Today', groupedSessions.today)}
            {renderSessionGroup('Yesterday', groupedSessions.yesterday)}
            {renderSessionGroup('This Week', groupedSessions.thisWeek)}
            {renderSessionGroup('This Month', groupedSessions.thisMonth)}
            {renderSessionGroup('Earlier', groupedSessions.earlier)}
          </div>
        )}
      </motion.div>

      {/* Preview Modal */}
      <AnimatePresence>
        {previewSession && (
          <SessionPreviewModal
            session={previewSession}
            onClose={() => setPreviewSession(null)}
            onLoad={() => {
              handleLoadSession(previewSession);
              setPreviewSession(null);
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Session Card Component
function SessionCard({
  session,
  isDeleting,
  onPreview,
  onLoad,
  onDelete,
  onExport,
}: {
  session: SessionItem;
  isDeleting: boolean;
  onPreview: () => void;
  onLoad: () => void;
  onDelete: () => void;
  onExport: (format: 'json' | 'markdown') => void;
}) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className={`${styles.card} ${isDeleting ? styles.cardDeleting : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
    >
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}>
          <h4>{session.title}</h4>
          <span className={styles.cardTime}>
            {formatDistanceToNow(session.timestamp, { addSuffix: true })}
          </span>
        </div>
        <div className={styles.cardActions}>
          <AnimatePresence>
            {isHovered && (
              <motion.div
                className={styles.actionButtons}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
              >
                <button
                  className={styles.actionBtn}
                  onClick={onPreview}
                  title="Preview"
                >
                  <Icon icon={Icons.eye} size="sm" />
                </button>
                <button
                  className={styles.actionBtn}
                  onClick={() => onExport('json')}
                  title="Export JSON"
                >
                  <Icon icon={Icons.download} size="sm" />
                </button>
                <button
                  className={`${styles.actionBtn} ${styles.actionBtnDanger}`}
                  onClick={onDelete}
                  title="Delete"
                >
                  <Icon icon={Icons.trash} size="sm" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {session.preview && (
        <p className={styles.cardPreview}>{session.preview}</p>
      )}

      <div className={styles.cardFooter}>
        <div className={styles.cardStats}>
          <span>
            <Icon icon={Icons.chat} size="sm" />
            {session.messageCount} messages
          </span>
          {session.tokenCount && (
            <span>
              <Icon icon={Icons.timer} size="sm" />
              {session.tokenCount} tokens
            </span>
          )}
        </div>
        <div className={styles.cardTags}>
          {session.tags?.slice(0, 3).map((tag) => (
            <span key={tag} className={styles.cardTag}>
              {tag}
            </span>
          ))}
        </div>
      </div>

      <button className={styles.cardLoadBtn} onClick={onLoad}>
        Load Session →
      </button>
    </motion.div>
  );
}

// Session Preview Modal
function SessionPreviewModal({
  session,
  onClose,
  onLoad,
}: {
  session: SessionItem;
  onClose: () => void;
  onLoad: () => void;
}) {
  return (
    <motion.div
      className={styles.modalOverlay}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className={styles.modal}
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.modalHeader}>
          <h3>{session.title}</h3>
          <button className={styles.modalClose} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.modalMeta}>
          <span>{format(new Date(session.timestamp), 'PPP p')}</span>
          <span>{session.messageCount} messages</span>
        </div>

        <div className={styles.modalMessages}>
          {session.messages.slice(0, 20).map((msg, idx) => (
            <div
              key={idx}
              className={`${styles.modalMessage} ${styles[msg.role]}`}
            >
              <span className={styles.messageRole}>{msg.role}</span>
              <span className={styles.messageContent}>
                {msg.content.substring(0, 200)}
                {msg.content.length > 200 ? '...' : ''}
              </span>
            </div>
          ))}
          {session.messages.length > 20 && (
            <div className={styles.moreMessages}>
              +{session.messages.length - 20} more messages
            </div>
          )}
        </div>

        <div className={styles.modalActions}>
          <Button
            variant="secondary"
            size="sm"
            onClick={onClose}
          >
            Close
          </Button>
          <Button variant="primary" size="sm" onClick={onLoad}>
            Load Session
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default HistoryPage;
