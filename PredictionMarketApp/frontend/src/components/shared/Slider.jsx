import React from 'react';

export default function Slider({ label, value, onChange, min = 0, max = 100, step = 1, className = '' }) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {label && (
        <div className="flex items-center justify-between text-xs text-terminal-amber-dim font-mono">
          <span>{label}</span>
          <span className="text-terminal-amber">{value}</span>
        </div>
      )}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-terminal-border-dim appearance-none cursor-pointer touch-none"
        style={{
          accentColor: '#D4A017',
          WebkitAppearance: 'none',
        }}
      />
    </div>
  );
}
