// Skeleton Loading Component Library
// Provides visual placeholders while content loads
import styles from './Skeleton.module.css';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
}

export function Skeleton({
  className = '',
  width,
  height,
  borderRadius,
}: SkeletonProps) {
  return (
    <div
      className={`${styles.skeleton} ${className}`}
      style={{
        width,
        height,
        borderRadius,
      }}
    />
  );
}

// Skeleton Card - for card placeholders
export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`${styles.skeletonCard} ${className}`}>
      <div className={styles.skeletonHeader}>
        <Skeleton width={40} height={40} borderRadius="8px" />
        <div className={styles.skeletonTitle}>
          <Skeleton width="60%" height={16} />
          <Skeleton width="40%" height={12} />
        </div>
      </div>
      <div className={styles.skeletonContent}>
        <Skeleton width="100%" height={12} />
        <Skeleton width="90%" height={12} />
        <Skeleton width="75%" height={12} />
      </div>
    </div>
  );
}

// Skeleton Text - for text content
export function SkeletonText({
  lines = 3,
  className = '',
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`${styles.skeletonText} ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 ? '60%' : '100%'}
          height={12}
          className={styles.skeletonLine}
        />
      ))}
    </div>
  );
}

// Skeleton Avatar - for profile/user placeholders
export function SkeletonAvatar({
  size = 40,
  className = '',
}: {
  size?: number;
  className?: string;
}) {
  return (
    <Skeleton
      width={size}
      height={size}
      borderRadius="50%"
      className={className}
    />
  );
}

// Skeleton Table - for table rows
export function SkeletonTable({
  rows = 5,
  columns = 4,
  className = '',
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`${styles.skeletonTable} ${className}`}>
      {/* Header */}
      <div className={styles.skeletonRow}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton
            key={`header-${i}`}
            width="80%"
            height={14}
            className={styles.skeletonCell}
          />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowI) => (
        <div key={`row-${rowI}`} className={styles.skeletonRow}>
          {Array.from({ length: columns }).map((_, colI) => (
            <Skeleton
              key={`cell-${rowI}-${colI}`}
              width={colI === 0 ? '60%' : '80%'}
              height={12}
              className={styles.skeletonCell}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// Skeleton Chart - for chart placeholders
export function SkeletonChart({ className = '' }: { className?: string }) {
  return (
    <div className={`${styles.skeletonChart} ${className}`}>
      <div className={styles.skeletonChartGrid}>
        <div className={styles.skeletonChartLines}>
          <div className={styles.skeletonChartLine} />
          <div className={styles.skeletonChartLine} />
          <div className={styles.skeletonChartLine} />
          <div className={styles.skeletonChartLine} />
          <div className={styles.skeletonChartLine} />
        </div>
        <div className={styles.skeletonChartBars}>
          <Skeleton width={30} height="40%" borderRadius="4px" />
          <Skeleton width={30} height="60%" borderRadius="4px" />
          <Skeleton width={30} height="80%" borderRadius="4px" />
          <Skeleton width={30} height="50%" borderRadius="4px" />
          <Skeleton width={30} height="70%" borderRadius="4px" />
        </div>
      </div>
    </div>
  );
}

// Skeleton List - for list items
export function SkeletonList({
  items = 5,
  className = '',
}: {
  items?: number;
  className?: string;
}) {
  return (
    <div className={`${styles.skeletonList} ${className}`}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className={styles.skeletonListItem}>
          <SkeletonAvatar size={36} />
          <div className={styles.skeletonListContent}>
            <Skeleton width="40%" height={14} />
            <Skeleton width="70%" height={12} />
          </div>
        </div>
      ))}
    </div>
  );
}

// Skeleton Dashboard - complete dashboard skeleton
export function SkeletonDashboard() {
  return (
    <div className={styles.skeletonDashboard}>
      <div className={styles.skeletonHeader}>
        <Skeleton width={150} height={24} />
        <Skeleton width={80} height={16} />
      </div>
      <div className={styles.skeletonGrid}>
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <div className={styles.skeletonRowLarge}>
        <SkeletonCard className={styles.skeletonChartCard} />
        <SkeletonCard className={styles.skeletonActivityCard} />
      </div>
    </div>
  );
}

// Skeleton Chat - chat page skeleton
export function SkeletonChat() {
  return (
    <div className={styles.skeletonChat}>
      <div className={styles.skeletonMessageArea}>
        <SkeletonList items={6} />
      </div>
      <div className={styles.skeletonInput}>
        <Skeleton width="100%" height={56} borderRadius="28px" />
      </div>
    </div>
  );
}

// Skeleton Progress - for progress indicators
export function SkeletonProgress({
  progress = 0,
  className = '',
}: {
  progress?: number;
  className?: string;
}) {
  return (
    <div className={`${styles.skeletonProgress} ${className}`}>
      <div
        className={styles.skeletonProgressBar}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

// Export all skeleton components
export const SkeletonComponents = {
  Skeleton,
  SkeletonCard,
  SkeletonText,
  SkeletonAvatar,
  SkeletonTable,
  SkeletonChart,
  SkeletonList,
  SkeletonDashboard,
  SkeletonChat,
  SkeletonProgress,
};
