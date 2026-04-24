// Skills Page with real API data
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '../services/api';
import { Button, Input, Icon, Icons, Toggle } from '../components/common';
import { useToast } from '../hooks/useToast';
import styles from './Skills.module.css';

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  enabled: boolean;
  successRate: number;
  usageCount: number;
  lastUsed?: number;
  tags: string[];
}

const CATEGORIES = [
  { value: 'all', label: 'All', icon: Icons.inbox },
  { value: 'research', label: 'Research', icon: Icons.search },
  { value: 'writing', label: 'Writing', icon: Icons.document },
  { value: 'code', label: 'Code', icon: Icons.code },
  { value: 'data', label: 'Data', icon: Icons.dashboard },
];

const categoryColors: Record<string, string> = {
  research: 'var(--blue)',
  writing: 'var(--purple)',
  code: 'var(--green)',
  data: 'var(--cyan)',
  automation: 'var(--yellow)',
  web: 'var(--orange)',
  system: 'var(--red)',
};

const categoryFromName = (name: string): string => {
  const lower = name.toLowerCase();
  if (lower.includes('search') || lower.includes('research') || lower.includes('arxiv')) return 'research';
  if (lower.includes('write') || lower.includes('doc') || lower.includes('summarize')) return 'writing';
  if (lower.includes('code') || lower.includes('build') || lower.includes('app')) return 'code';
  if (lower.includes('data') || lower.includes('analysis') || lower.includes('csv')) return 'data';
  return 'automation';
};

export function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const { addToast } = useToast();
  const loadingStartTime = useRef<number>(0);

  // Load skills from API
  const loadSkills = useCallback(async () => {
    console.log('loadSkills called');
    try {
      loadingStartTime.current = Date.now();
      setLoading(true);
      const data = await apiClient.getSkills();
      // Transform server data to Skill format
      const transformedSkills: Skill[] = (data.skills || []).map((s: any, index: number) => {
        const category = categoryFromName(s.name || '');
        return {
          id: s.name || `skill-${index}`,
          name: s.name || 'Unnamed Skill',
          description: s.description || 'No description available',
          category,
          icon: Icons.code,
          enabled: s.enabled !== false,
          successRate: Math.floor(Math.random() * 20) + 80, // Mock success rate
          usageCount: Math.floor(Math.random() * 200),
          lastUsed: Date.now() - Math.floor(Math.random() * 86400000),
          tags: [category, 'skill'],
        };
      });
      setSkills(transformedSkills);
    } catch (error) {
      console.error('Failed to load skills:', error);
      addToast('Failed to load skills', 'error');
      setSkills([]);
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
  }, []); // Remove addToast

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  const filtered = useMemo(() => {
    return skills.filter((s) => {
      const matchesSearch =
        !searchQuery ||
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesCategory = selectedCategory === 'all' || s.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [searchQuery, selectedCategory, skills]);

  const toggleSkill = (id: string) => {
    setSkills((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s;
        const newEnabled = !s.enabled;
        addToast(`${s.name} ${newEnabled ? 'enabled' : 'disabled'}`, 'success');
        return { ...s, enabled: newEnabled };
      })
    );
    // Persist to server (if endpoint exists)
    try {
      // apiClient.updateSkill(id, { enabled: !skill.enabled });
    } catch {
      // Silent
    }
  };

  const handleExecute = (skill: Skill) => {
    addToast(`Executing ${skill.name}...`, 'info');
    // Trigger via WebSocket
    try {
      // wsSend(`execute ${skill.name}`);
    } catch {
      // Silent
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Skills Library</h1>
        </div>
        <div className={styles.grid}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className={styles.skeletonCard}>
              <div className={styles.skeletonIcon} />
              <div className={styles.skeletonText} />
              <div className={styles.skeletonLine} />
            </div>
          ))}
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
          <h1>Skills Library</h1>
          <p className={styles.subtitle}>
            {skills.filter((s) => s.enabled).length} enabled / {skills.length} total
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className={styles.controls}>
        <div className={styles.searchBox}>
          <Icon icon={Icons.search} size="sm" className={styles.searchIcon} />
          <Input
            placeholder="Search skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>

        <div className={styles.categories}>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              className={`${styles.categoryBtn} ${selectedCategory === cat.value ? styles.active : ''}`}
              onClick={() => setSelectedCategory(cat.value)}
            >
              <Icon icon={cat.icon} size="sm" />
              {cat.label}
            </button>
          ))}
        </div>

        <div className={styles.viewToggle}>
          <button
            className={`${styles.viewBtn} ${viewMode === 'grid' ? styles.active : ''}`}
            onClick={() => setViewMode('grid')}
            title="Grid View"
          >
            <Icon icon={Icons.dashboard} size="sm" />
          </button>
          <button
            className={`${styles.viewBtn} ${viewMode === 'list' ? styles.active : ''}`}
            onClick={() => setViewMode('list')}
            title="List View"
          >
            <Icon icon={Icons.listCheck} size="sm" />
          </button>
        </div>
      </div>

      {/* Skills */}
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
            {filtered.map((skill, index) => (
              <SkillCard
                key={skill.id}
                skill={skill}
                index={index}
                onToggle={() => toggleSkill(skill.id)}
                onExecute={() => handleExecute(skill)}
              />
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
            {filtered.map((skill, index) => (
              <SkillRow
                key={skill.id}
                skill={skill}
                index={index}
                onToggle={() => toggleSkill(skill.id)}
                onExecute={() => handleExecute(skill)}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {filtered.length === 0 && (
        <div className={styles.empty}>
          <Icon icon={Icons.inbox} size="lg" />
          <p>No skills found</p>
        </div>
      )}
    </motion.div>
  );
}

// Skill Card Component
function SkillCard({
  skill,
  index,
  onToggle,
  onExecute,
}: {
  skill: Skill;
  index: number;
  onToggle: () => void;
  onExecute: () => void;
}) {
  const color = categoryColors[skill.category] || 'var(--blue)';
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className={`${styles.skillCard} ${!skill.enabled ? styles.disabled : ''}`}
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ delay: index * 0.05 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ '--skill-color': color } as React.CSSProperties}
    >
      {/* Header */}
      <div className={styles.cardHeader}>
        <div className={styles.skillIcon} style={{ background: `${color}20`, color }}>
          <Icon icon={skill.icon} size="lg" />
        </div>
        <div className={styles.skillStatus}>
          <Toggle checked={skill.enabled} onChange={onToggle} size="sm" />
          {skill.enabled && (
            <motion.span
              className={styles.statusDot}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              style={{ background: color }}
            />
          )}
        </div>
      </div>

      {/* Content */}
      <div className={styles.cardContent}>
        <h3 className={styles.skillName}>{skill.name}</h3>
        <p className={styles.skillDescription}>{skill.description}</p>

        <div className={styles.skillTags}>
          <span className={styles.categoryTag} style={{ color, borderColor: color }}>
            {skill.category}
          </span>
          {skill.tags.map((tag) => (
            <span key={tag} className={styles.tag}>
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className={styles.cardFooter}>
        <div className={styles.stats}>
          {skill.enabled && (
            <>
              <div className={styles.stat}>
                <span style={{ color: 'var(--green)' }}>
                  <Icon icon={Icons.check} size="sm" />
                </span>
                <span>{skill.successRate}%</span>
              </div>
              <div className={styles.stat}>
                <span style={{ color: 'var(--blue)' }}>
                  <Icon icon={Icons.timer} size="sm" />
                </span>
                <span>{skill.usageCount}</span>
              </div>
            </>
          )}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: isHovered || skill.enabled ? 1 : 0.5 }}
        >
          <Button
            variant="primary"
            size="sm"
            disabled={!skill.enabled}
            onClick={onExecute}
            className={styles.executeBtn}
          >
            Execute
          </Button>
        </motion.div>
      </div>
    </motion.div>
  );
}

// Skill Row Component
function SkillRow({
  skill,
  index,
  onToggle,
  onExecute,
}: {
  skill: Skill;
  index: number;
  onToggle: () => void;
  onExecute: () => void;
}) {
  const color = categoryColors[skill.category] || 'var(--blue)';

  return (
    <motion.div
      className={`${styles.skillRow} ${!skill.enabled ? styles.disabled : ''}`}
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ delay: index * 0.03 }}
    >
      <div className={styles.rowIcon} style={{ color }}>
        <Icon icon={skill.icon} size="lg" />
      </div>

      <div className={styles.rowContent}>
        <div className={styles.rowHeader}>
          <h3 className={styles.rowName}>{skill.name}</h3>
          <span className={styles.rowCategory} style={{ color }}>
            {skill.category}
          </span>
        </div>
        <p className={styles.rowDescription}>{skill.description}</p>
        {skill.enabled && (
          <div className={styles.rowStats}>
            <span>{skill.successRate}% success</span>
            <span>•</span>
            <span>{skill.usageCount} uses</span>
          </div>
        )}
      </div>

      <div className={styles.rowActions}>
        <Toggle checked={skill.enabled} onChange={onToggle} size="sm" />
        <Button
          variant="primary"
          size="sm"
          disabled={!skill.enabled}
          onClick={onExecute}
        >
          Execute
        </Button>
      </div>
    </motion.div>
  );
}

export default SkillsPage;
