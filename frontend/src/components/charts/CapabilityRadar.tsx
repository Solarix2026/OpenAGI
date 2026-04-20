// Capability Radar Chart Component
import { useMemo } from 'react';
import styles from './CapabilityRadar.module.css';
import type { Capabilities } from '../../types';

interface CapabilityRadarProps {
  capabilities: Capabilities | Record<string, number>;
}

export const CapabilityRadar: React.FC<CapabilityRadarProps> = ({ capabilities }) => {
  // Define function BEFORE useMemo that uses it
  const getCapabilityColor = (value: number): string => {
    if (value >= 80) return 'var(--green)';
    if (value >= 60) return 'var(--blue)';
    if (value >= 40) return 'var(--yellow)';
    return 'var(--red)';
  };

  const capabilityData = useMemo(() => {
    return Object.entries(capabilities).map(([key, value]) => ({
      name: key.charAt(0).toUpperCase() + key.slice(1),
      value,
      color: getCapabilityColor(value),
    }));
  }, [capabilities]);

  const maxValue = 100;
  const levels = 5;

  return (
    <div className={styles.radarContainer}>
      <div className={styles.radarChart}>
        {/* Grid lines */}
        <svg className={styles.radarSvg} viewBox="0 0 200 200">
          {/* Concentric circles */}
          {Array.from({ length: levels }).map((_, i) => {
            const radius = ((i + 1) / levels) * 80;
            return (
              <circle
                key={`grid-${i}`}
                cx="100"
                cy="100"
                r={radius}
                className={styles.gridCircle}
              />
            );
          })}

          {/* Axes */}
          {capabilityData.map((_, index) => {
            const angle = (index * 2 * Math.PI) / capabilityData.length - Math.PI / 2;
            const x = 100 + Math.cos(angle) * 90;
            const y = 100 + Math.sin(angle) * 90;
            return (
              <g key={`axis-${index}`}>
                <line
                  x1="100"
                  y1="100"
                  x2={x}
                  y2={y}
                  className={styles.axisLine}
                />
              </g>
            );
          })}

          {/* Data polygon */}
          {capabilityData.length > 0 && (
            <polygon
              points={capabilityData
                .map((cap, index) => {
                  const angle = (index * 2 * Math.PI) / capabilityData.length - Math.PI / 2;
                  const radius = (cap.value / maxValue) * 80;
                  const x = 100 + Math.cos(angle) * radius;
                  const y = 100 + Math.sin(angle) * radius;
                  return `${x},${y}`;
                })
                .join(' ')}
              className={styles.dataPolygon}
              fill="rgba(59, 130, 246, 0.3)"
              stroke="rgba(59, 130, 246, 0.8)"
              strokeWidth="2"
            />
          )}

          {/* Data points */}
          {capabilityData.map((cap, index) => {
            const angle = (index * 2 * Math.PI) / capabilityData.length - Math.PI / 2;
            const radius = (cap.value / maxValue) * 80;
            const x = 100 + Math.cos(angle) * radius;
            const y = 100 + Math.sin(angle) * radius;
            return (
              <circle
                key={`point-${index}`}
                cx={x}
                cy={y}
                r="3"
                fill={cap.color}
              />
            );
          })}
        </svg>

        {/* Labels */}
        <div className={styles.labelsContainer}>
          {capabilityData.map((cap, index) => {
            const angle = (index * 2 * Math.PI) / capabilityData.length - Math.PI / 2;
            const radius = 85;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            const align =
              Math.abs(x) < 10 ? 'center' : x > 0 ? 'left' : 'right';
            return (
              <div
                key={`label-${index}`}
                className={styles.label}
                style={{
                  left: `calc(50% + ${x}px)`,
                  top: `calc(50% + ${y}px)`,
                  textAlign: align as any,
                  transform:
                    align === 'center'
                      ? 'translate(-50%, -50%)'
                      : `translate(${x > 0 ? '-100%' : '0'}, -50%)`,
                }}
              >
                <div>{cap.name}</div>
                <div className={styles.percentage}>{cap.value}%</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CapabilityRadar;