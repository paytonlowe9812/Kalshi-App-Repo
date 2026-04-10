import React from 'react';

const COLOR_MAP = {
  running: 'bg-terminal-green-bright shadow-glow-green',
  stopped: 'bg-terminal-amber-dim',
  error: 'bg-terminal-red shadow-glow-red',
  paused: 'bg-terminal-amber',
};

export default function StatusDot({ status, className = '' }) {
  const color = COLOR_MAP[status] || 'bg-terminal-amber-dim';
  return (
    <span
      className={`inline-block w-2.5 h-2.5 ${color} ${
        status === 'running' ? 'animate-pulse-slow' : ''
      } ${className}`}
      title={status}
    />
  );
}
