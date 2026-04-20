// Textarea component with auto-resize
import React, { useState, useRef, useEffect } from 'react';
import styles from './Textarea.module.css';

interface TextareaProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  minRows?: number;
  maxRows?: number;
  maxHeight?: number;
  className?: string;
  autoFocus?: boolean;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

export const Textarea: React.FC<TextareaProps> = ({
  value,
  onChange,
  placeholder,
  disabled = false,
  minRows = 2,
  maxRows = 10,
  maxHeight = 400,
  className = '',
  autoFocus = false,
  onKeyDown,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [height, setHeight] = useState<number | 'auto'>('auto');

  useEffect(() => {
    if (textareaRef.current) {
      const textarea = textareaRef.current;
      textarea.style.height = 'auto';

      const lineHeight = parseInt(getComputedStyle(textarea).lineHeight) || 20;
      const minHeight = minRows * lineHeight;
      const maxHeightPx = Math.min(maxHeight, maxRows * lineHeight);

      const newHeight = Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeightPx);
      textarea.style.height = `${newHeight}px`;
      setHeight(newHeight);
    }
  }, [value, minRows, maxRows, maxHeight]);

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const textarea = e.currentTarget;
    textarea.style.height = 'auto';

    const lineHeight = parseInt(getComputedStyle(textarea).lineHeight) || 20;
    const minHeight = minRows * lineHeight;
    const maxHeightPx = Math.min(maxHeight, maxRows * lineHeight);

    const newHeight = Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeightPx);
    textarea.style.height = `${newHeight}px`;
    setHeight(newHeight);
  };

  return (
    <textarea
      ref={textareaRef}
      className={`${styles.textarea} ${disabled ? styles.disabled : ''} ${className}`}
      value={value}
      onChange={handleChange}
      onInput={handleInput}
      placeholder={placeholder}
      disabled={disabled}
      onKeyDown={onKeyDown}
      rows={minRows}
      style={{ height: height === 'auto' ? undefined : height }}
    />
  );
};

export default Textarea;
