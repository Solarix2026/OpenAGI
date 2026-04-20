// Toggle / Switch component
import React from 'react';
import styles from './Toggle.module.css';

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

export const Toggle: React.FC<ToggleProps> = ({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  label,
  className = '',
}) => {
  const handleToggle = () => {
    if (!disabled) {
      onChange(!checked);
    }
  };

  const sizeClass = {
    sm: styles.sm,
    md: styles.md,
    lg: styles.lg,
  }[size];

  return (
    <div className={`${styles.container} ${className}`}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-disabled={disabled}
        onClick={handleToggle}
        className={`${styles.toggle} ${sizeClass} ${checked ? styles.on : styles.off} ${disabled ? styles.disabled : ''}`}
      >
        <span className={styles.slider} />
      </button>
      {label && <span className={styles.label}>{label}</span>}
    </div>
  );
};

export default Toggle;
