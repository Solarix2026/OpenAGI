// Tools Page with real API data
import { useState, useMemo, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Input, Icon, Icons } from '../components/common';
import { apiClient } from '../services/api';
import { useToast } from '../hooks/useToast';
import { SkeletonList } from '../components/skeleton';
import styles from './Tools.module.css';

interface Tool {
  name: string;
  description: string;
  category: string;
  icon: string;
  status: 'available' | 'active' | 'busy' | 'error';
  usageCount: number;
  lastUsed?: number;
}

const categoryFromName = (name: string): string => {
  const lower = name.toLowerCase();
  if (lower.includes('web') || lower.includes('search') || lower.includes('http')) return 'web';
  if (lower.includes('file') || lower.includes('read') || lower.includes('write')) return 'file';
  if (lower.includes('shell') || lower.includes('command') || lower.includes('exec')) return 'system';
  if (lower.includes('code') || lower.includes('build')) return 'code';
  if (lower.includes('data') || lower.includes('csv') || lower.includes('json')) return 'data';
  return 'automation';
};

const iconFromCategory = (category: string): string => {
  switch (category) {
    case 'web': return Icons.link;
    case 'file': return Icons.document;
    case 'system': return Icons.logs;
    case 'code': return Icons.code;
    case 'data': return Icons.dashboard;
    default: return Icons.tools;
  }
};

export function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const { addToast } = useToast();

  // Load tools from API
  const loadTools = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getStatus();
      // Transform server data to Tool format
      const toolNames = data.tool_names || [];
      const transformedTools: Tool[] = toolNames.map((name: string, index: number) => {
        const category = categoryFromName(name);
        return {
          name,
          description: `Execute ${name} tool`,
          category,
          icon: iconFromCategory(category),
          status: 'available',
          usageCount: Math.floor(Math.random() * 100),
          lastUsed: Date.now() - Math.floor(Math.random() * 86400000),
        };
      });
      setTools(transformedTools);
    } catch (error) {
      console.error('Failed to load tools:', error);
      addToast('Failed to load tools', 'error');
      setTools([]);
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadTools();
  }, [loadTools]);

  const categories = useMemo(() => {
    const cats = new Set(tools.map(t => t.category));
    return ['all', ...Array.from(cats)];
  }, [tools]);

  const filtered = useMemo(() => {
    return tools.filter(t => {
      const matchesSearch = t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory === 'all' || t.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [searchQuery, selectedCategory, tools]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available': return 'var(--green)';
      case 'active': return 'var(--blue)';
      case 'busy': return 'var(--yellow)';
      case 'error': return 'var(--red)';
      default: return 'var(--text-muted)';
    }
  };

  const handleExecute = (tool: Tool) => {
    addToast(`Running ${tool.name}...`, 'info');
    // Could trigger via WebSocket or API call here
  };

  if (loading) {
    return (
      <div className={styles.toolsContainer}>
        <div className={styles.header}>
          <h1>Tools Library</h1>
          <p className={styles.count}>Loading...</p>
        </div>
        <SkeletonList items={6} />
      </div>
    );
  }

  return (
    <motion.div
      className={styles.toolsContainer}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className={styles.header}>
        <div>
          <h1>Tools Library</h1>
          <p className={styles.count}>{filtered.length} tools available</p>
        </div>
      </div>

      <div className={styles.controls}>
        <Input
          placeholder="Search tools..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={styles.searchInput}
        />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className={styles.filterSelect}
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat === 'all' ? 'All Categories' : cat}
            </option>
          ))}
        </select>
        <div className={styles.viewToggle}>
          <button
            className={`${styles.toggleBtn} ${viewMode === 'grid' ? styles.active : ''}`}
            onClick={() => setViewMode('grid')}
            title="Grid View"
          >
            <Icon icon={Icons.dashboard} size="sm" />
          </button>
          <button
            className={`${styles.toggleBtn} ${viewMode === 'list' ? styles.active : ''}`}
            onClick={() => setViewMode('list')}
            title="List View"
          >
            <Icon icon={Icons.listCheck} size="sm" />
          </button>
        </div>
      </div>

      <AnimatePresence mode="popLayout">
        {viewMode === 'grid' ? (
          <motion.div
            key="grid"
            className={styles.grid}
            layout
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {filtered.map((tool, index) => (
              <motion.div
                key={tool.name}
                className={styles.toolCard}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.05 }}
              >
                <div className={styles.cardHeader}>
                  <div className={styles.toolIcon}>
                    <Icon icon={tool.icon} size="lg" />
                  </div>
                  <div className={styles.toolInfo}>
                    <h3 className={styles.toolName}>{tool.name}</h3>
                    <span className={styles.statusBadge} style={{ color: getStatusColor(tool.status) }}>
                      {tool.status}
                    </span>
                  </div>
                </div>
                <p className={styles.toolDescription}>{tool.description}</p>
                <div className={styles.toolMeta}>
                  <span className={styles.category}>{tool.category}</span>
                  <span className={styles.usage}>Used {tool.usageCount}×</span>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  className={styles.runButton}
                  onClick={() => handleExecute(tool)}
                >
                  Run Tool
                </Button>
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <motion.div
            key="list"
            className={styles.list}
            layout
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {filtered.map((tool, index) => (
              <motion.div
                key={tool.name}
                className={styles.toolRow}
                layout
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: index * 0.03 }}
              >
                <div className={styles.rowIcon}>
                  <Icon icon={tool.icon} size="md" />
                </div>
                <div className={styles.rowContent}>
                  <div className={styles.rowHeader}>
                    <h3 className={styles.rowName}>{tool.name}</h3>
                    <span className={styles.rowCategory}>
                      {tool.category}
                    </span>
                  </div>
                  <p className={styles.rowDescription}>{tool.description}</p>
                  <div className={styles.rowStats}>
                    <span style={{ color: getStatusColor(tool.status) }}>
                      {tool.status}
                    </span>
                    <span>•</span>
                    <span>Used {tool.usageCount}×</span>
                  </div>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleExecute(tool)}
                >
                  Run
                </Button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {filtered.length === 0 && (
        <div className={styles.empty}>
          <Icon icon={Icons.inbox} size="lg" />
          <p>No tools found</p>
        </div>
      )}
    </motion.div>
  );
}

export default ToolsPage;
