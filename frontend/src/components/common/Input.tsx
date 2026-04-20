// Input 组件
import React from 'react';
import styles from './Input.module.css';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', icon, error, ...props }, ref) => {
    return (
      <div className={styles.wrapper}>
        {icon && <span className={styles.icon}>{icon}</span>}
        <input ref={ref} className={`${styles.input} ${icon ? styles.withIcon : ''} ${error ? styles.error : ''} ${className}`} {...props} />
        {error && <span className={styles.errorText}>{error}</span>}
      </div>
    );
  }
);

Input.displayName = 'Input';
