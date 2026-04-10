import React from 'react';

export default function Toggle({ checked, onChange, label, className = '' }) {
  return (
    <label className={`flex items-center gap-3 cursor-pointer min-h-[44px] select-none ${className}`}>
      <div className="relative flex-shrink-0">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div
          className={`w-11 h-6 transition-all ${
            checked
              ? 'bg-terminal-amber-faint border-terminal-amber shadow-glow-sm'
              : 'bg-terminal-bg border-terminal-border-dim'
          }`}
          style={{ border: '1px solid' }}
        />
        <div
          className={`absolute top-0.5 left-0.5 w-5 h-5 transition-transform ${
            checked
              ? 'translate-x-5 bg-terminal-amber shadow-glow-sm'
              : 'translate-x-0 bg-terminal-amber-dim'
          }`}
        />
      </div>
      {label && <span className="text-sm text-terminal-amber font-mono">{label}</span>}
    </label>
  );
}
