// Command Palette / Quick Action Menu
import React, { useState, useEffect, useRef } from 'react';
import styles from './CommandPalette.module.css';
import { Icon, Icons } from './Icon';

interface Command {
  id: string;
  icon: string;
  label: string;
  shortcut?: string;
  group: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute: (command: string) => void;
}

const commands: Command[] = [
  // Actions
  { id: 'morning', icon: Icons.sun, label: 'Morning briefing', group: 'Actions', action: () => {} },
  { id: 'status', icon: Icons.dashboard, label: 'System status', group: 'Actions', action: () => {} },
  { id: 'world', icon: Icons.globe, label: 'World events', group: 'Actions', action: () => {} },
  { id: 'evolve', icon: Icons.dna, label: 'Run evolution cycle', group: 'Actions', action: () => {} },
  { id: 'invent', icon: Icons.tools, label: 'Invent a tool', shortcut: '⌘I', group: 'Actions', action: () => {} },

  // Modes
  { id: 'mode-auto', icon: Icons.bolt, label: 'Switch to Auto mode', shortcut: '⌘1', group: 'Modes', action: () => {} },
  { id: 'mode-code', icon: Icons.code, label: 'Switch to Code mode', shortcut: '⌘2', group: 'Modes', action: () => {} },
  { id: 'mode-reason', icon: Icons.brain, label: 'Switch to Reason mode', shortcut: '⌘3', group: 'Modes', action: () => {} },
  { id: 'mode-plan', icon: Icons.listCheck, label: 'Switch to Plan mode', shortcut: '⌘4', group: 'Modes', action: () => {} },
  { id: 'mode-research', icon: Icons.flask, label: 'Switch to Research mode', shortcut: '⌘5', group: 'Modes', action: () => {} },

  // Memory
  { id: 'goals', icon: Icons.goals, label: 'Show my goals', group: 'Memory', action: () => {} },
  { id: 'recall', icon: Icons.memory, label: 'Search memory...', shortcut: '⌘R', group: 'Memory', action: () => {} },

  // Settings
  { id: 'settings', icon: Icons.settings, label: 'Open settings', shortcut: '⌘,', group: 'Settings', action: () => {} },
];

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, onExecute }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(query.toLowerCase()) ||
      cmd.group.toLowerCase().includes(query.toLowerCase())
  );

  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.group]) acc[cmd.group] = [];
    acc[cmd.group].push(cmd);
    return acc;
  }, {} as Record<string, Command[]>);

  const allCommands = Object.values(groupedCommands).flat();

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => (prev + 1) % allCommands.length);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => (prev - 1 + allCommands.length) % allCommands.length);
          break;
        case 'Enter':
          e.preventDefault();
          if (allCommands[selectedIndex]) {
            handleExecute(allCommands[selectedIndex]);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, allCommands, onClose]);

  const handleExecute = (cmd: Command) => {
    onExecute(cmd.id);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.container} onClick={(e) => e.stopPropagation()}>
        <div className={styles.searchRow}>
          <Icon icon={Icons.search} size="md" className={styles.searchIcon} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command or search..."
            className={styles.input}
          />
          {query && (
            <button className={styles.clearBtn} onClick={() => setQuery('')}>
              <Icon icon={Icons.close} size="sm" />
            </button>
          )}
          <kbd className={styles.kbd}>Esc</kbd>
        </div>

        <div className={styles.results}>
          {allCommands.length === 0 ? (
            <div className={styles.empty}>
              <Icon icon={Icons.search} size="lg" />
              <p>No commands found</p>
            </div>
          ) : (
            Object.entries(groupedCommands).map(([group, cmds]) => (
              <div key={group} className={styles.group}>
                <div className={styles.groupHeader}>{group}</div>
                {cmds.map((cmd) => {
                  const globalIndex = allCommands.indexOf(cmd);
                  const isSelected = globalIndex === selectedIndex;
                  return (
                    <div
                      key={cmd.id}
                      className={`${styles.item} ${isSelected ? styles.selected : ''}`}
                      onClick={() => handleExecute(cmd)}
                      onMouseEnter={() => setSelectedIndex(globalIndex)}
                    >
                      <Icon icon={cmd.icon} size="md" />
                      <span className={styles.label}>{cmd.label}</span>
                      {cmd.shortcut && <kbd className={styles.shortcut}>{cmd.shortcut}</kbd>}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className={styles.footer}>
          <div className={styles.hint}>
            <kbd>↑↓</kbd> Navigate <kbd>↵</kbd> Select <kbd>Esc</kbd> Close
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
