// Interactive Metric Card with animations and sparklines
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import styles from './MetricCard.module.css';
import { Icon } from '../common';

interface MetricCardProps {
  title: string;
  value: string | number;
  subvalue?: string;
  icon: string;
  color?: 'blue' | 'green' | 'cyan' | 'purple' | 'yellow' | 'red';
  sparklineData?: number[];
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  onClick?: () => void;
}

export function MetricCard({
  title,
  value,
  subvalue,
  icon,
  color = 'blue',
  sparklineData,
  trend,
  trendValue,
  onClick,
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const numericValue = typeof value === 'number' ? value : parseInt(value.toString().replace(/[^0-9]/g, ''));

  // Animate value on mount
  useEffect(() => {
    if (!isNaN(numericValue) && numericValue > 0) {
      const duration = 1000;
      const steps = 30;
      const increment = numericValue / steps;
      let current = 0;

      const timer = setInterval(() => {
        current += increment;
        if (current >= numericValue) {
          setDisplayValue(numericValue);
          clearInterval(timer);
        } else {
          setDisplayValue(Math.floor(current));
        }
      }, duration / steps);

      return () => clearInterval(timer);
    } else {
      setDisplayValue(numericValue || 0);
    }
  }, [numericValue]);

  const displayString = typeof value === 'string' && value.includes('h')
    ? value // Keep string format for uptime
    : typeof value === 'string' && value.includes('%')
    ? `${displayValue}%`
    : typeof value === 'string' && value.includes('ms')
    ? `${displayValue}ms`
    : typeof value === 'string' && value.includes('MB')
    ? `${displayValue}MB`
    : displayValue;

  return (
    <motion.div
      className={`${styles.card} ${onClick ? styles.clickable : ''} ${styles[color]}`}
      onClick={onClick}
      whileHover={{ scale: 1.02, y: -4 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
    >
      <div className={styles.header}>
        <div className={`${styles.icon} ${styles[`icon${color}`]}`}>
          <Icon icon={icon} size="md" />
        </div>
        {trend && (
          <div className={`${styles.trend} ${styles[`trend${trend}`]}`}>
            <span className={styles.trendIcon}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
            </span>
            {trendValue && <span className={styles.trendValue}>{trendValue}</span>}
          </div>
        )}
      </div>

      <div className={styles.content}>
        <motion.span
          className={styles.value}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          {displayString}
        </motion.span>
        {subvalue && (
          <span className={styles.subvalue}>{subvalue}</span>
        )}
      </div>

      <div className={styles.footer}>
        <span className={styles.title}>{title}</span>
        {sparklineData && (
          <Sparkline data={sparklineData} color={color} />
        )}
      </div>
    </motion.div>
  );
}

// Mini Sparkline component
function Sparkline({
  data,
  color,
}: {
  data: number[];
  color: string;
}) {
  const width = 60;
  const height = 20;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data.map((value, index) => ({
    x: (index / (data.length - 1)) * width,
    y: height - ((value - min) / range) * height,
  }));

  const pathD = points
    .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
    .join(' ');

  const colorMap: Record<string, string> = {
    blue: 'var(--blue)',
    green: 'var(--green)',
    cyan: 'var(--cyan)',
    purple: 'var(--purple)',
    yellow: 'var(--yellow)',
    red: 'var(--red)',
  };

  return (
    <svg
      className={styles.sparkline}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      <motion.path
        d={pathD}
        fill="none"
        stroke={colorMap[color] || colorMap.blue}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1, ease: 'easeOut' }}
      />
    </svg>
  );
}

// Animated ring progress
export function RingProgress({
  value,
  size = 60,
  strokeWidth = 4,
  color = 'var(--blue)',
  label,
}: {
  value: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  label?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className={styles.ringProgress} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          className={styles.ringBackground}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          className={styles.ringProgressCircle}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </svg>
      <div className={styles.ringLabel}>
        <span>{Math.round(value)}%</span>
        {label && <small>{label}</small>}
      </div>
    </div>
  );
}

// Quick stat card for mini metrics
export function QuickStat({
  icon,
  value,
  label,
  color = 'blue',
}: {
  icon: string;
  value: string | number;
  label: string;
  color?: string;
}) {
  return (
    <div className={`${styles.quickStat} ${styles[color]}`}>
      <div className={styles.quickStatIcon}>
        <Icon icon={icon} size="md" />
      </div>
      <div className={styles.quickStatContent}>
        <span className={styles.quickStatValue}>{value}</span>
        <span className={styles.quickStatLabel}>{label}</span>
      </div>
    </div>
  );
}
