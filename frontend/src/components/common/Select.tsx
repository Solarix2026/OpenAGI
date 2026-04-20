// Select / Dropdown component
import React, { useState, useRef, useEffect } from 'react';
import styles from './Select.module.css';
import { Icon, Icons } from './Icon';

interface SelectOption {
  value: string;
  label: string;
  icon?: string;
}

interface SelectProps {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  disabled = false,
  size = 'md',
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState(placeholder);
  const selectRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const selected = options.find(opt => opt.value === value);
    setSelectedLabel(selected ? selected.label : placeholder);
  }, [value, options, placeholder]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (option: SelectOption) => {
    onChange(option.value);
    setIsOpen(false);
  };

  const sizeClass = {
    sm: styles.sm,
    md: styles.md,
    lg: styles.lg,
  }[size];

  return (
    <div
      ref={selectRef}
      className={`${styles.select} ${sizeClass} ${disabled ? styles.disabled : ''} ${className}`}
    >
      <button
        type="button"
        className={`${styles.trigger} ${isOpen ? styles.open : ''}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
      >
        <span className={styles.selected}>{selectedLabel}</span>
        <Icon icon={Icons.chevronDown} size={size === 'sm' ? 'sm' : 'md'} />
      </button>

      {isOpen && (
        <div className={styles.dropdown}>
          {options.map((option) => (
            <div
              key={option.value}
              className={`${styles.option} ${option.value === value ? styles.selected : ''}`}
              onClick={() => handleSelect(option)}
            >
              {option.icon && <Icon icon={option.icon} size={size === 'sm' ? 'sm' : 'md'} />}
              <span>{option.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Select;
