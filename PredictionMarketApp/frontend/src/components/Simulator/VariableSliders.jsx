import React from 'react';
import Slider from '../shared/Slider';

const VAR_RANGES = {
  YES_price: { min: 0, max: 100, step: 1 },
  NO_price: { min: 0, max: 100, step: 1 },
  PositionSize: { min: -100, max: 100, step: 1 },
};

const DEFAULT_RANGE = { min: 0, max: 100, step: 1 };

export default function VariableSliders({ variables, onChange, onReset }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="panel-header">VARIABLES</h3>
        <button onClick={onReset} className="text-[10px] text-terminal-amber-bright hover:text-terminal-amber font-mono">RESET</button>
      </div>
      {Object.entries(variables).map(([name, value]) => {
        const range = VAR_RANGES[name] || DEFAULT_RANGE;
        return (
          <div key={name} className="flex items-center gap-2">
            <Slider label={name} value={value} onChange={(val) => onChange(name, val)} min={range.min} max={range.max} step={range.step} className="flex-1" />
            <input type="number" value={value} onChange={(e) => onChange(name, parseFloat(e.target.value) || 0)} className="input-field w-16 text-xs py-0.5 text-right" />
          </div>
        );
      })}
    </div>
  );
}
