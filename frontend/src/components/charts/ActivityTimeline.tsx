// Activity Timeline Component for Dashboard
import { useState } from 'react';
import { Icon, Icons } from '../common';
import styles from './ActivityTimeline.module.css';
import type { MemoryEvent } from '../../types';

interface ActivityTimelineProps {
  events: MemoryEvent[];
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ events }) => {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  const toggleEvent = (id: string) => {
    setExpandedEvents(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const getEventColor = (type: string): string => {
    switch (type) {
      case 'action':
        return 'var(--blue)';
      case 'memory':
        return 'var(--green)';
      case 'conversation':
        return 'var(--yellow)';
      case 'system':
        return 'var(--purple)';
      default:
        return 'var(--text-muted)';
    }
  };

  const getEventIcon = (type: string): string => {
    switch (type) {
      case 'action':
        return Icons.bolt;
      case 'memory':
        return Icons.brain;
      case 'conversation':
        return Icons.chat;
      case 'system':
        return Icons.settings;
      default:
        return Icons.info;
    }
  };

  if (events.length === 0) {
    return (
      <div className={styles.emptyTimeline}>
        <div className={styles.emptyIcon}>🕐</div>
        <div className={styles.emptyText}>No recent activity yet</div>
      </div>
    );
  }

  return (
    <div className={styles.timelineContainer}>
      {events.map((event, idx) => {
        const isExpanded = expandedEvents.has(event.id);

        return (
          <div
            key={event.id}
            className={`${styles.timelineItem} ${isExpanded ? styles.expanded : ''}`}
            onClick={() => toggleEvent(event.id)}
          >
            {/* Timeline line and dot */}
            <div className={styles.timelineLine}>
              {idx < events.length - 1 && <div className={styles.lineConnector}></div>}
              <div
                className={styles.timelineDot}
                style={{ backgroundColor: getEventColor(event.type) }}
              >
                <Icon icon={getEventIcon(event.type)} size="sm" />
              </div>
            </div>

            {/* Event content */}
            <div className={styles.eventContent}>
              <div className={styles.eventHeader}>
                <span className={styles.eventTime}>
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                <span
                  className={styles.eventType}
                  style={{ backgroundColor: getEventColor(event.type) + '20' }}
                >
                  {event.type}
                </span>
                <span className={styles.importanceBadge} style={{ opacity: event.importance }}>
                  {event.importance >= 0.8 ? '●●●' : event.importance >= 0.5 ? '●●' : '●'}
                </span>
              </div>

              <div className={styles.eventContentText}>
                <div className={styles.eventTitle}>
                  {event.content.substring(0, isExpanded ? 120 : 60)}
                  {event.content.length > 60 && !isExpanded && '...'}
                </div>
                <div className={styles.eventMetadata}>
                  <span className={styles.dateLabel}>
                    {new Date(event.timestamp).toLocaleDateString()}
                  </span>
                  {event.importance >= 0.5 && <span className={styles.important}>Important</span>}
                </div>
              </div>

              {isExpanded && (
                <div className={styles.eventDetails}>
                  <div className={styles.fullContent}>{event.content}</div>
                  {event.embedding && (
                    <div className={styles.embeddingInfo}>
                      <strong>Embedding:</strong> {event.embedding.length} dimensions
                    </div>
                  )}
                </div>
              )}

              <button className={styles.expandToggle}>
                {isExpanded ? 'Show less' : 'Show more'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};