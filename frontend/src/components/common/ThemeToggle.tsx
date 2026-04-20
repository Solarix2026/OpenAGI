// Theme Toggle component
import React from 'react';
import { useTheme } from '../../context/ThemeContext';
import { Icon, Icons } from './Icon';
import styles from './ThemeToggle.module.css';

export const ThemeToggle: React.FC = () => {
  const { theme, setTheme } = useTheme();

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return Icons.sun;
      case 'dark':
        return Icons.moon;
      case 'auto':
        return Icons.auto;
      default:
        return Icons.moon;
    }
  };

  const getNextTheme = (): 'light' | 'dark' | 'auto' => {
    if (theme === 'light') return 'dark';
    if (theme === 'dark') return 'auto';
    return 'light';
  };

  const handleToggle = () => {
    setTheme(getNextTheme());
  };

  return (
    <button
      className={styles.toggleBtn}
      onClick={handleToggle}
      title={`Theme: ${theme}`}
    >
      <Icon icon={getThemeIcon()} size="md" />
      <span className={styles.themeLabel}>{theme}</span>
    </button>
  );
};

export default ThemeToggle;
