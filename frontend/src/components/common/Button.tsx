// Button 组件
import React from 'react';
import styles from './Button.module.css';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'primary', size = 'md', icon, loading, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`${styles.button} ${styles[variant]} ${styles[size]} ${className}`}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <span className={styles.spinner} />}
        {icon && !loading && <span className={styles.icon}>{icon}</span>}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
