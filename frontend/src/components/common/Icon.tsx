// Font Awesome Icon wrapper component
import React from 'react';

interface IconProps {
  icon: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  onClick?: () => void;
}

const sizeMap = {
  sm: '10px',
  md: '14px',
  lg: '18px',
  xl: '24px',
};

export const Icon: React.FC<IconProps> = ({ icon, size = 'md', className = '', onClick }) => {
  return (
    <i
      className={`fa ${icon} ${className}`}
      style={{ fontSize: sizeMap[size], cursor: onClick ? 'pointer' : 'default' }}
      onClick={onClick}
    />
  );
};

// Common icons used throughout the app
export const Icons = {
  // Navigation
  chat: 'fa-comment-dots',
  dashboard: 'fa-chart-line',
  history: 'fa-clock-rotate-left',
  channels: 'fa-satellite',
  tools: 'fa-wrench',
  skills: 'fa-puzzle-piece',
  goals: 'fa-bullseye',
  logs: 'fa-terminal',
  memory: 'fa-brain',
  settings: 'fa-gear',

  // Actions
  send: 'fa-paper-plane',
  microphone: 'fa-microphone',
  search: 'fa-magnifying-glass',
  close: 'fa-xmark',
  check: 'fa-check',
  copy: 'fa-copy',
  reply: 'fa-reply',
  regenerate: 'fa-rotate-right',
  more: 'fa-ellipsis',
  edit: 'fa-pen',
  delete: 'fa-trash',

  // UI
  bolt: 'fa-bolt',
  code: 'fa-code',
  brain: 'fa-brain',
  flask: 'fa-flask',
  listCheck: 'fa-list-check',
  sun: 'fa-sun',
  globe: 'fa-globe',
  dna: 'fa-dna',
  robot: 'fa-robot',
  user: 'fa-user',
  document: 'fa-file-lines',
  image: 'fa-image',
  download: 'fa-download',
  upload: 'fa-upload',
  link: 'fa-link',
  external: 'fa-arrow-up-right-from-square',

  // Controls
  chevronDown: 'fa-chevron-down',
  chevronRight: 'fa-chevron-right',
  spinner: 'fa-spinner',
  refresh: 'fa-rotate',
  trash: 'fa-trash',
  eye: 'fa-eye',
  inbox: 'fa-inbox',
  toolCount: 'fa-screwdriver-wrench',

  // Status
  checkCircle: 'fa-circle-check',
  warning: 'fa-circle-exclamation',
  error: 'fa-circle-xmark',
  info: 'fa-circle-info',
  star: 'fa-star',
  heart: 'fa-heart',
  zap: 'fa-bolt',

  // Settings Tabs
  route: 'fa-route',
  keyboard: 'fa-keyboard',
  warningTriangle: 'fa-triangle-exclamation',

  // Theme
  moon: 'fa-moon',
  sunTheme: 'fa-sun',
  auto: 'fa-circle-half-stroke',

  // Other
  timer: 'fa-hourglass-half',
  expand: 'fa-expand',
  compress: 'fa-compress',
} as const;
