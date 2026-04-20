// Loading State Manager with Progress Illusions
// Provides optimistic UI feedback and progress indicators
import { useState, useEffect, useCallback } from 'react';
import styles from './LoadingState.module.css';

interface ProgressConfig {
  fastStart: number; // percentage to reach quickly
  slowEnd: number; // percentage to slow down
  duration: number; // total expected duration in ms
}

// Progress Illusion Hook - creates perceived faster loading
export function useProgressIllusion(
  isLoading: boolean,
  config: ProgressConfig = {
    fastStart: 30,
    slowEnd: 90,
    duration: 3000,
  }
): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setProgress(100);
      const timer = setTimeout(() => setProgress(0), 300);
      return () => clearTimeout(timer);
    }

    setProgress(0);
    let currentProgress = 0;
    const { fastStart, slowEnd, duration } = config;

    // Phase 1: Fast growth to fastStart
    const phase1Duration = duration * 0.2;
    const phase1Target = fastStart;
    const phase1Steps = 10;
    const phase1Interval = phase1Duration / phase1Steps;

    const phase1Timer = setInterval(() => {
      currentProgress += phase1Target / phase1Steps;
      if (currentProgress >= phase1Target) {
        clearInterval(phase1Timer);

        // Phase 2: Slow growth to slowEnd
        const phase2Duration = duration * 0.7;
        const phase2Target = slowEnd;
        const remaining = phase2Target - currentProgress;
        const phase2Steps = 30;
        const phase2Interval = phase2Duration / phase2Steps;

        const phase2Timer = setInterval(() => {
          // Exponential decay for slower growth
          const remainingProgress = phase2Target - currentProgress;
          const increment = remainingProgress * 0.1;
          currentProgress += increment;

          if (currentProgress >= phase2Target - 1) {
            clearInterval(phase2Timer);
            currentProgress = slowEnd;
          }

          setProgress(Math.min(currentProgress, slowEnd));
        }, phase2Interval);
      } else {
        setProgress(currentProgress);
      }
    }, phase1Interval);

    return () => clearInterval(phase1Timer);
  }, [isLoading, config]);

  return progress;
}

// Optimistic Update Hook
export function useOptimistic<T>(
  actualValue: T,
  updater: (value: T) => Promise<void>
): [T, (optimisticValue: T) => void, boolean, string | null] {
  const [optimisticValue, setOptimisticValue] = useState<T>(actualValue);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync with actual value when it changes externally
  useEffect(() => {
    if (!isUpdating) {
      setOptimisticValue(actualValue);
    }
  }, [actualValue, isUpdating]);

  const update = useCallback(
    async (newValue: T) => {
      const previousValue = optimisticValue;
      setOptimisticValue(newValue);
      setIsUpdating(true);
      setError(null);

      try {
        await updater(newValue);
      } catch (err) {
        setOptimisticValue(previousValue);
        setError(err instanceof Error ? err.message : 'Update failed');
      } finally {
        setIsUpdating(false);
      }
    },
    [optimisticValue, updater]
  );

  return [optimisticValue, update, isUpdating, error];
}

// Progress Bar Component
export function ProgressBar({
  progress,
  label,
  showPercentage = true,
  variant = 'default',
}: {
  progress: number;
  label?: string;
  showPercentage?: boolean;
  variant?: 'default' | 'indeterminate' | 'stepped';
}) {
  const clampedProgress = Math.min(Math.max(progress, 0), 100);

  return (
    <div className={styles.progressContainer}>
      {label && <span className={styles.progressLabel}>{label}</span>}
      <div className={`${styles.progressBar} ${styles[variant]}`}>
        <div
          className={styles.progressFill}
          style={{ width: `${clampedProgress}%` }}
        >
          {showPercentage && clampedProgress > 20 && (
            <span className={styles.progressText}>{Math.round(clampedProgress)}%</span>
          )}
        </div>
        {variant === 'indeterminate' && (
          <div className={styles.progressIndeterminate} />
        )}
      </div>
    </div>
  );
}

// Multi-step Progress
export function StepProgress({
  steps,
  currentStep,
  stepLabels,
}: {
  steps: number;
  currentStep: number;
  stepLabels?: string[];
}) {
  return (
    <div className={styles.stepProgress}>
      {Array.from({ length: steps }).map((_, index) => (
        <div
          key={index}
          className={`${styles.step} ${
            index < currentStep
              ? styles.completed
              : index === currentStep
              ? styles.active
              : styles.pending
          }`}
        >
          <div className={styles.stepIndicator}>
            {index < currentStep ? '✓' : index + 1}
          </div>
          {stepLabels && index < stepLabels.length && (
            <span className={styles.stepLabel}>{stepLabels[index]}</span>
          )}
          {index < steps - 1 && <div className={styles.stepConnector} />}
        </div>
      ))}
    </div>
  );
}

// Loading Spinner with pulse
export function LoadingSpinner({
  size = 'md',
  text,
}: {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}) {
  return (
    <div className={`${styles.spinnerContainer} ${styles[size]}`}>
      <div className={styles.spinner}>
        <div className={styles.spinnerRing} />
        <div className={styles.spinnerRing} />
        <div className={styles.spinnerRing} />
      </div>
      {text && <span className={styles.spinnerText}>{text}</span>}
    </div>
  );
}

// Skeleton with Progress
export function SkeletonWithProgress({
  children,
  isLoading,
  progress,
  fallback,
}: {
  children: React.ReactNode;
  isLoading: boolean;
  progress?: number;
  fallback?: React.ReactNode;
}) {
  if (isLoading) {
    return (
      <div className={styles.skeletonWrapper}>
        {fallback}
        {progress !== undefined && progress < 100 && (
          <ProgressBar progress={progress} variant="indeterminate" />
        )}
      </div>
    );
  }

  return <>{children}</>;
}

// Page Transition Loading
export function PageTransition({
  isTransitioning,
  children,
}: {
  isTransitioning: boolean;
  children: React.ReactNode;
}) {
  const progress = useProgressIllusion(isTransitioning, {
    fastStart: 40,
    slowEnd: 85,
    duration: 500,
  });

  return (
    <div
      className={`${styles.pageTransition} ${
        isTransitioning ? styles.transitioning : ''
      }`}
    >
      {isTransitioning && (
        <div className={styles.pageTransitionOverlay}>
          <LoadingSpinner size="lg" />
          <ProgressBar progress={progress} showPercentage={false} />
        </div>
      )}
      <div
        className={`${styles.pageContent} ${
          isTransitioning ? styles.pageContentHidden : ''
        }`}
      >
        {children}
      </div>
    </div>
  );
}

// Fast Start Screen
export function FastStartScreen({
  onComplete,
  brandName = 'OpenAGI',
  tagline = 'Autonomous Intelligence System',
}: {
  onComplete: () => void;
  brandName?: string;
  tagline?: string;
}) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('Initializing...');

  useEffect(() => {
    const stages = [
      { progress: 20, status: 'Loading core modules...', delay: 200 },
      { progress: 40, status: 'Establishing WebSocket connection...', delay: 400 },
      { progress: 60, status: 'Synchronizing memory...', delay: 600 },
      { progress: 80, status: 'Preparing user interface...', delay: 800 },
      { progress: 100, status: 'Ready!', delay: 1000 },
    ];

    stages.forEach(({ progress, status, delay }) => {
      setTimeout(() => {
        setProgress(progress);
        setStatus(status);
        if (progress === 100) {
          setTimeout(onComplete, 300);
        }
      }, delay);
    });
  }, [onComplete]);

  return (
    <div className={styles.fastStart}>
      <div className={styles.fastStartContent}>
        <div className={styles.fastStartBrand}>
          <div className={styles.fastStartLogo}>
            <svg viewBox="0 0 64 64" className={styles.logoSvg}>
              <defs>
                <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="var(--blue)" />
                  <stop offset="100%" stopColor="var(--purple)" />
                </linearGradient>
              </defs>
              <circle cx="32" cy="32" r="28" fill="none" stroke="url(#logoGradient)" strokeWidth="3" />
              <path
                d="M20 32 L28 40 L44 24"
                fill="none"
                stroke="url(#logoGradient)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={progress > 50 ? styles.logoCheck : ''}
              />
            </svg>
          </div>
          <h1 className={styles.fastStartTitle}>{brandName}</h1>
          <p className={styles.fastStartTagline}>{tagline}</p>
        </div>
        <div className={styles.fastStartProgress}>
          <ProgressBar progress={progress} showPercentage={false} />
          <span className={styles.fastStartStatus}>{status}</span>
        </div>
      </div>
    </div>
  );
}

// Loading State Context Provider
export function useLoadingState(delay = 200) {
  const [isLoading, setIsLoading] = useState(false);
  const [delayedLoading, setDelayedLoading] = useState(false);

  useEffect(() => {
    if (isLoading) {
      const timer = setTimeout(() => setDelayedLoading(true), delay);
      return () => clearTimeout(timer);
    } else {
      setDelayedLoading(false);
    }
  }, [isLoading, delay]);

  const progress = useProgressIllusion(isLoading);

  return {
    isLoading,
    setIsLoading,
    delayedLoading,
    progress,
    startLoading: useCallback(() => setIsLoading(true), []),
    stopLoading: useCallback(() => setIsLoading(false), []),
  };
}
