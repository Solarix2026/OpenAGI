// Card 组件
import React from 'react';
import styles from './Card.module.css';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  interactive?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', title, subtitle, interactive = false, children, ...props }, ref) => {
    return (
      <div ref={ref} className={`${styles.card} ${interactive ? styles.interactive : ''} ${className}`} {...props}>
        {title && (
          <div className={styles.header}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
        )}
        <div className={styles.content}>{children}</div>
      </div>
    );
  }
);

Card.displayName = 'Card';
