// Enhanced Interactive Radar Chart using Recharts
// Supports hover tooltips, click interactions, and animated transitions
import { useState, useCallback } from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import styles from './InteractiveRadar.module.css';

interface CapabilityData {
  subject: string;
  value: number;
  fullMark: number;
  color: string;
  description: string;
}

interface InteractiveRadarProps {
  data: Record<string, number>;
  onDimensionClick?: (dimension: string, value: number) => void;
}

// Color mapping for capabilities
const capabilityColors: Record<string, string> = {
  'Reasoning': 'var(--blue)',
  'Knowledge': 'var(--purple)',
  'Execution': 'var(--green)',
  'Memory': 'var(--cyan)',
  'Learning': 'var(--yellow)',
  'Vision': 'var(--red)',
  'Autonomy': 'var(--pink)',
};

// Descriptions for each capability
const capabilityDescriptions: Record<string, string> = {
  'Reasoning': 'Logical analysis and problem-solving depth',
  'Knowledge': 'Domain coverage and factual accuracy',
  'Execution': 'Tool use efficiency and reliability',
  'Memory': 'Context retention and recall capability',
  'Learning': 'Adaptation and skill acquisition rate',
  'Vision': 'Image understanding and visual analysis',
  'Autonomy': 'Self-directed action and goal pursuit',
};

export function InteractiveRadar({ data, onDimensionClick }: InteractiveRadarProps) {
  const [hoveredDimension, setHoveredDimension] = useState<string | null>(null);
  const [selectedDimension, setSelectedDimension] = useState<string | null>(null);

  // Transform data for Recharts
  const chartData: CapabilityData[] = Object.entries(data).map(([subject, value]) => ({
    subject,
    value,
    fullMark: 100,
    color: capabilityColors[subject] || 'var(--blue)',
    description: capabilityDescriptions[subject] || '',
  }));

  const handleClick = useCallback((dataPoint: any) => {
    if (dataPoint && dataPoint.subject) {
      setSelectedDimension(dataPoint.subject);
      onDimensionClick?.(dataPoint.subject, dataPoint.value);
    }
  }, [onDimensionClick]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className={styles.tooltip}
        >
          <div className={styles.tooltipHeader} style={{ borderColor: data.color }}>
            <span className={styles.tooltipTitle}>{data.subject}</span>
            <span className={styles.tooltipValue} style={{ color: data.color }}>
              {data.value}%
            </span>
          </div>
          <p className={styles.tooltipDesc}>{data.description}</p>
          <span className={styles.tooltipHint}>Click for details</span>
        </motion.div>
      );
    }
    return null;
  };

  return (
    <div className={styles.container}>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart
          cx="50%"
          cy="50%"
          outerRadius="70%"
          data={chartData}
          onMouseMove={(e) => {
            if (e.activePayload) {
              setHoveredDimension(e.activePayload[0]?.payload?.subject);
            }
          }}
          onMouseLeave={() => setHoveredDimension(null)}
          onClick={handleClick}
        >
          <PolarGrid
            stroke="var(--border)"
            strokeWidth={1}
            gridType="polygon"
          />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fill: 'var(--text-dim)', fontSize: 9 }}
            tickCount={6}
            stroke="var(--border)"
          />
          <Radar
            name="Capabilities"
            dataKey="value"
            stroke="var(--blue)"
            strokeWidth={2}
            fill="url(#radarGradient)"
            fillOpacity={0.5}
          />
          <defs>
            <linearGradient id="radarGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--blue)" stopOpacity={0.4} />
              <stop offset="100%" stopColor="var(--purple)" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>

      {/* Capability Legend */}
      <div className={styles.legend}>
        {chartData.map((item) => (
          <motion.button
            key={item.subject}
            className={`${styles.legendItem} ${
              selectedDimension === item.subject ? styles.legendItemActive : ''
            }`}
            onClick={() => handleClick({ subject: item.subject, value: item.value })}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <span
              className={styles.legendDot}
              style={{ backgroundColor: item.color }}
            />
            <span className={styles.legendLabel}>{item.subject}</span>
            <span className={styles.legendValue} style={{ color: item.color }}>
              {item.value}%
            </span>
          </motion.button>
        ))}
      </div>

      {/* Selected Dimension Detail */}
      <AnimatePresence>
        {selectedDimension && (
          <motion.div
            initial={{ opacity: 0, y: 10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            className={styles.detailPanel}
          >
            <div className={styles.detailHeader}>
              <h4>{selectedDimension}</h4>
              <button
                className={styles.closeBtn}
                onClick={() => setSelectedDimension(null)}
              >
                ×
              </button>
            </div>
            <p className={styles.detailDesc}>
              {capabilityDescriptions[selectedDimension]}
            </p>
            <div className={styles.detailMetrics}>
              <div className={styles.detailMetric}>
                <span className={styles.detailMetricLabel}>Score</span>
                <span className={styles.detailMetricValue}>
                  {data[selectedDimension]}%
                </span>
              </div>
              <div className={styles.detailMetric}>
                <span className={styles.detailMetricLabel}>Status</span>
                <span className={`${styles.detailMetricValue} ${
                  data[selectedDimension] >= 70 ? styles.statusHigh :
                  data[selectedDimension] >= 40 ? styles.statusMedium :
                  styles.statusLow
                }`}>
                  {data[selectedDimension] >= 70 ? 'Strong' :
                   data[selectedDimension] >= 40 ? 'Developing' : 'Limited'}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Mini radar for tooltips/popovers
export function MiniRadar({
  data,
  size = 80,
}: {
  data: Record<string, number>;
  size?: number;
}) {
  const chartData = Object.entries(data).map(([subject, value]) => ({
    subject,
    value,
    fullMark: 100,
  }));

  return (
    <div className={styles.miniRadar} style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="60%" data={chartData}>
          <PolarGrid stroke="var(--border)" strokeWidth={0.5} />
          <Radar
            dataKey="value"
            stroke="var(--blue)"
            fill="var(--blue)"
            fillOpacity={0.3}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
