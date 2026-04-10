import React from 'react';

const LINE_TYPES = [
  { type: 'IF', color: 'border-terminal-amber bg-terminal-amber-faint active:bg-terminal-amber/20', key: 'I' },
  { type: 'AND', color: 'border-terminal-amber-dim bg-terminal-amber-faint active:bg-terminal-amber/20', key: 'A' },
  { type: 'OR', color: 'border-terminal-amber-dim bg-terminal-amber-faint active:bg-terminal-amber/20', key: 'O' },
  { type: 'ELSE', color: 'border-terminal-border-dim bg-terminal-panel active:bg-terminal-amber-faint', key: 'E' },
  { type: 'THEN', color: 'border-terminal-green bg-terminal-green/20 active:bg-terminal-green/30', key: 'T' },
  { type: 'GOTO', color: 'border-terminal-amber bg-terminal-amber-faint active:bg-terminal-amber/20', key: 'G' },
  { type: 'CONT', color: 'border-terminal-green-bright/50 bg-terminal-green/20 active:bg-terminal-green/30', key: 'C', fullType: 'CONTINUE' },
  { type: 'STOP', color: 'border-terminal-red bg-terminal-red/20 active:bg-terminal-red/30', key: 'S' },
  { type: 'LOG', color: 'border-terminal-border-dim bg-terminal-panel active:bg-terminal-amber-faint', key: 'L' },
  { type: 'VAR', color: 'border-terminal-amber-dim bg-terminal-amber-faint active:bg-terminal-amber/20', key: 'V', fullType: 'SET_VAR' },
  { type: 'ALERT', color: 'border-terminal-amber bg-terminal-amber-faint active:bg-terminal-amber/20', key: '!' },
];

export default function RuleToolbar({ onAddLine, onSimulate }) {
  return (
    <div className="flex items-center gap-0.5 md:gap-1 px-1.5 md:px-2 py-1.5 border-b border-terminal-border-dim bg-terminal-panel overflow-x-auto scrollbar-none">
      {LINE_TYPES.map((lt) => (
        <button
          key={lt.type}
          onClick={() => onAddLine(lt.fullType || lt.type)}
          className={`${lt.color} text-terminal-amber text-[10px] md:text-[11px] px-1.5 md:px-2 py-1 md:py-1 font-mono font-medium transition-colors whitespace-nowrap flex-shrink-0 select-none border`}
          title={`Add ${lt.fullType || lt.type} line (${lt.key})`}
        >
          {lt.type}
        </button>
      ))}
      <div className="flex-shrink-0 w-1 md:flex-1" />
      <button
        onClick={onSimulate}
        className="bg-terminal-amber-faint border border-terminal-amber text-terminal-amber-bright active:bg-terminal-amber/20 text-[10px] md:text-[11px] px-2 py-1 font-mono font-medium transition-colors flex-shrink-0 select-none shadow-glow-sm"
      >
        SIM
      </button>
    </div>
  );
}
