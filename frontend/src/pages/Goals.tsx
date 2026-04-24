// Goals Page with real API data + real-time updates
import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getWebSocketManager } from '../services/websocket';
import { apiClient } from '../services/api';
import { Button, Icon, Icons } from '../components/common';
import { useToast } from '../hooks/useToast';
import styles from './Goals.module.css';

interface Goal {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'abandoned';
  progress: number;
  createdAt: number;
  updatedAt: number;
  tasks: Task[];
  color: string;
}

interface Task {
  id: string;
  title: string;
  completed: boolean;
}

const COLORS = [
  { name: 'blue', value: 'var(--blue)', bg: 'var(--blue-dim, rgba(59, 130, 246, 0.15))' },
  { name: 'green', value: 'var(--green)', bg: 'var(--green-dim, rgba(16, 185, 129, 0.15))' },
  { name: 'purple', value: 'var(--purple)', bg: 'var(--purple-dim, rgba(139, 92, 246, 0.15))' },
  { name: 'cyan', value: 'var(--cyan)', bg: 'var(--cyan-dim, rgba(6, 182, 212, 0.15))' },
  { name: 'orange', value: 'var(--yellow)', bg: 'var(--yellow-dim, rgba(245, 158, 11, 0.15))' },
];

const STATUS_CONFIG = {
  pending: { label: 'Pending', icon: Icons.timer, color: 'var(--text-muted)' },
  active: { label: 'Active', icon: Icons.bolt, color: 'var(--blue)' },
  completed: { label: 'Completed', icon: Icons.check, color: 'var(--green)' },
  abandoned: { label: 'Abandoned', icon: Icons.trash, color: 'var(--red)' },
};

export function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();
  const loadingStartTime = useRef<number>(0);

  // Load goals from API
  const loadGoals = useCallback(async (showSkeleton = true) => {
    try {
      loadingStartTime.current = Date.now();
      if (showSkeleton) setLoading(true);
      const data = await apiClient.getGoals();
      // Transform server data to Goal format
      const transformedGoals: Goal[] = (data.goals || []).map((g: any, index: number) => ({
        id: g.id || `goal-${index}`,
        title: g.description || g.title || 'Untitled Goal',
        description: g.notes || g.description || 'No description',
        status: g.status || 'pending',
        progress: g.progress || 0,
        createdAt: g.created_at || Date.now(),
        updatedAt: g.updated_at || Date.now(),
        tasks: (g.tasks || []).map((t: any, i: number) => ({
          id: t.id || `task-${i}`,
          title: t.description || t.title || 'Task',
          completed: t.completed || false,
        })),
        color: COLORS[index % COLORS.length].name,
      }));
      setGoals(transformedGoals);
    } catch (error) {
      console.error('Failed to load goals:', error);
      addToast('Failed to load goals', 'error');
      setGoals([]);
    } finally {
      // Minimum loading time to prevent flash
      const elapsed = Date.now() - (loadingStartTime.current || 0);
      const minLoadingTime = 300;
      if (elapsed < minLoadingTime) {
        setTimeout(() => setLoading(false), minLoadingTime - elapsed);
      } else {
        setLoading(false);
      }
    }
  }, []); // removed addToast

  // Load goals on mount and set up WebSocket for real-time updates
  useEffect(() => {
    loadGoals(true);

    // WebSocket for real-time goal updates
    const wsManager = getWebSocketManager();
    let unsubscribed = false;

    const handleMessage = (msg: any) => {
      if (unsubscribed) return;

      // Initial goals from WebSocket
      if (msg.type === 'goals_init' && msg.goals) {
        const transformedGoals: Goal[] = msg.goals.map((g: any, index: number) => ({
          id: g.id || `goal-${index}`,
          title: g.description || g.title || 'Untitled Goal',
          description: g.notes || g.description || 'No description',
          status: g.status || 'pending',
          progress: g.progress || 0,
          createdAt: g.created_at || Date.now(),
          updatedAt: g.updated_at || Date.now(),
          tasks: (g.tasks || []).map((t: any, i: number) => ({
            id: t.id || `task-${i}`,
            title: t.description || t.title || 'Task',
            completed: t.completed || false,
          })),
          color: COLORS[index % COLORS.length].name,
        }));
        setGoals(transformedGoals);
        return;
      }

      // Listen for goal updates from WebSocket
      if (msg.type === 'goal_update' && msg.goal) {
        const g = msg.goal;
        setGoals((prev) => {
          const exists = prev.find((goal) => goal.id === g.id);
          if (exists) {
            // Update existing goal
            return prev.map((goal) =>
              goal.id === g.id
                ? {
                    ...goal,
                    status: g.status || goal.status,
                    progress: g.progress ?? goal.progress,
                    updatedAt: Date.now(),
                  }
                : goal
            );
          }
          return prev;
        });
      } else if (msg.type === 'goal_created' && msg.goal) {
        // New goal added - refresh list without flashing
        loadGoals(false);
      }
    };

    const unsubscribe = wsManager.onMessage(handleMessage);

    // Also poll every 30s as fallback
    const interval = setInterval(() => {
      loadGoals(false);
    }, 30000);

    return () => {
      unsubscribed = true;
      unsubscribe();
      clearInterval(interval);
    };
  }, [loadGoals]);

  const filteredGoals = goals.filter((g) => {
    if (filter === 'all') return true;
    if (filter === 'completed') return g.status === 'completed';
    return g.status !== 'completed';
  });

  const handleToggleTask = (goalId: string, taskId: string) => {
    setGoals((prev) =>
      prev.map((g) => {
        if (g.id !== goalId) return g;
        const updatedTasks = g.tasks.map((t) =>
          t.id === taskId ? { ...t, completed: !t.completed } : t
        );
        const completed = updatedTasks.filter((t) => t.completed).length;
        const progress = updatedTasks.length > 0 ? Math.round((completed / updatedTasks.length) * 100) : 0;
        return { ...g, tasks: updatedTasks, progress, updatedAt: Date.now() };
      })
    );
  };

  const handleAddGoal = async () => {
    const newGoal: Goal = {
      id: `goal-${Date.now()}`,
      title: 'New Goal',
      description: 'Click to edit description',
      status: 'pending',
      progress: 0,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      tasks: [],
      color: COLORS[Math.floor(Math.random() * COLORS.length)].name,
    };
    setGoals([newGoal, ...goals]);
    setExpandedId(newGoal.id);
    try {
      await apiClient.addGoal(newGoal.description);
      addToast('Goal created', 'success');
    } catch {
      // Silent fail - goal is already in UI
    }
  };

  const handleDeleteGoal = (id: string) => {
    if (!confirm('Delete this goal?')) return;
    setGoals((prev) => prev.filter((g) => g.id !== id));
    try {
      apiClient.deleteGoal(id);
    } catch {
      // Silent
    }
    addToast('Goal deleted', 'success');
  };

  const handleUpdateStatus = (id: string, status: Goal['status']) => {
    setGoals((prev) =>
      prev.map((g) => (g.id === id ? { ...g, status, updatedAt: Date.now() } : g))
    );
    try {
      apiClient.updateGoal(id, { status });
    } catch {
      // Silent
    }
    addToast(`Goal ${status}`, 'success');
  };

  const getColor = (name: string) => COLORS.find((c) => c.name === name) || COLORS[0];

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <div>
            <h1>Goals</h1>
            <p className={styles.subtitle}>Loading...</p>
          </div>
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
          <h1>Goals</h1>
          <p className={styles.subtitle}>
            {goals.filter((g) => g.status === 'active').length} active •{' '}
            {goals.filter((g) => g.status === 'completed').length} completed
          </p>
        </div>
        <Button variant="primary" size="md" onClick={handleAddGoal}>
          <Icon icon={Icons.more} size="sm" />
          New Goal
        </Button>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        {(['all', 'active', 'completed'] as const).map((f) => (
          <button
            key={f}
            className={`${styles.filterBtn} ${filter === f ? styles.active : ''}`}
            onClick={() => setFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            <span className={styles.count}>
              {f === 'all'
                ? goals.length
                : goals.filter((g) => (f === 'completed' ? g.status === 'completed' : g.status !== 'completed')).length}
            </span>
          </button>
        ))}
      </div>

      {/* Goals Grid */}
      <div className={styles.goalsGrid}>
        <AnimatePresence mode="popLayout">
          {filteredGoals.map((goal, index) => {
            const color = getColor(goal.color);
            const statusConfig = STATUS_CONFIG[goal.status];
            const isExpanded = expandedId === goal.id;

            return (
              <motion.div
                key={goal.id}
                className={styles.goalCard}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.05 }}
                style={{ '--goal-color': color.value } as React.CSSProperties}
              >
                {/* Card Header */}
                <div className={styles.cardHeader}>
                  <div className={styles.goalIcon} style={{ background: color.bg }}>
                    <span style={{ color: statusConfig.color }}>
                      <Icon icon={statusConfig.icon} size="md" />
                    </span>
                  </div>
                  <div className={styles.goalActions}>
                    {Object.keys(STATUS_CONFIG).map((status) => (
                      <button
                        key={status}
                        className={`${styles.statusDot} ${goal.status === status ? styles.active : ''}`}
                        onClick={() => handleUpdateStatus(goal.id, status as Goal['status'])}
                        style={{ background: STATUS_CONFIG[status as keyof typeof STATUS_CONFIG].color }}
                        title={STATUS_CONFIG[status as keyof typeof STATUS_CONFIG].label}
                      />
                    ))}
                    <button
                      className={styles.deleteBtn}
                      onClick={() => handleDeleteGoal(goal.id)}
                      title="Delete"
                    >
                      <Icon icon={Icons.trash} size="sm" />
                    </button>
                  </div>
                </div>

                {/* Goal Info */}
                <div className={styles.goalInfo}>
                  <h3 className={styles.goalTitle}>{goal.title}</h3>
                  <p className={styles.goalDescription}>{goal.description}</p>
                </div>

                {/* Progress */}
                <div className={styles.progressSection}>
                  <div className={styles.progressHeader}>
                    <span className={styles.progressLabel}>Progress</span>
                    <span className={styles.progressValue}>{goal.progress}%</span>
                  </div>
                  <div className={styles.progressBar}>
                    <motion.div
                      className={styles.progressFill}
                      initial={{ width: 0 }}
                      animate={{ width: `${goal.progress}%` }}
                      transition={{ duration: 0.5, delay: index * 0.1 }}
                      style={{ background: color.value }}
                    />
                  </div>
                </div>

                {/* Tasks Preview */}
                <div className={styles.tasksPreview}>
                  <span
                    className={styles.expandBtn}
                    onClick={() => setExpandedId(isExpanded ? null : goal.id)}
                  >
                    {goal.tasks.filter((t) => t.completed).length}/{goal.tasks.length} tasks
                    <Icon icon={isExpanded ? Icons.chevronDown : Icons.chevronRight} size="sm" />
                  </span>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        className={styles.taskList}
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                      >
                        {goal.tasks.length === 0 ? (
                          <p className={styles.noTasks}>No tasks yet</p>
                        ) : (
                          goal.tasks.map((task) => (
                            <label key={task.id} className={styles.taskItem}>
                              <input
                                type="checkbox"
                                checked={task.completed}
                                onChange={() => handleToggleTask(goal.id, task.id)}
                              />
                              <span className={task.completed ? styles.completed : ''}>
                                {task.title}
                              </span>
                            </label>
                          ))
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Footer */}
                <div className={styles.cardFooter}>
                  <span className={styles.updatedAt}>
                    Updated {new Date(goal.updatedAt).toLocaleDateString()}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {filteredGoals.length === 0 && (
        <div className={styles.empty}>
          <Icon icon={Icons.goals} size="lg" />
          <p>No goals found</p>
        </div>
      )}
    </motion.div>
  );
}

export default GoalsPage;
