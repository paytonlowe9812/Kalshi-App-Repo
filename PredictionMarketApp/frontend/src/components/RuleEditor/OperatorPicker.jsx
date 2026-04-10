import React from 'react';

const OPERATORS = [
  { value: 'eq', label: '=' },
  { value: 'neq', label: '!=' },
  { value: 'gt', label: '>' },
  { value: 'lt', label: '<' },
  { value: 'gte', label: '>=' },
  { value: 'lte', label: '<=' },
];

const OP_DISPLAY = { eq: '=', neq: '!=', gt: '>', lt: '<', gte: '>=', lte: '<=' };

export function getOperatorDisplay(op) { return OP_DISPLAY[op] || op || '?'; }

export default function OperatorPicker({ value, onChange, onClose }) {
  return (
    <div className="absolute z-50 mt-1 bg-terminal-surface border border-terminal-border shadow-glow py-1 w-20">
      {OPERATORS.map((op) => (
        <button key={op.value} onClick={() => { onChange(op.value); onClose(); }} className={`block w-full text-center px-2 py-1 text-sm font-mono hover:bg-terminal-amber-faint ${value === op.value ? 'text-terminal-amber-bright text-glow-sm' : 'text-terminal-amber'}`}>
          {op.label}
        </button>
      ))}
    </div>
  );
}
