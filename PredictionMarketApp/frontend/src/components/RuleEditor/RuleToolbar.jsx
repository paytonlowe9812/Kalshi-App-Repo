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
  { type: 'NOOP', color: 'border-terminal-border-dim bg-terminal-panel active:bg-terminal-amber-faint', key: 'N' },
  { type: 'PAUSE', color: 'border-terminal-amber-dim bg-terminal-amber-faint active:bg-terminal-amber/20', key: 'Z' },
  { type: 'CX', color: 'border-terminal-red/40 bg-terminal-red/10 active:bg-terminal-red/20', key: 'X', fullType: 'CANCEL_STALE' },
  { type: 'VAR', color: 'border-terminal-amber-dim bg-terminal-amber-faint active:bg-terminal-amber/20', key: 'V', fullType: 'SET_VAR' },
  { type: 'ALERT', color: 'border-terminal-amber bg-terminal-amber-faint active:bg-terminal-amber/20', key: '!' },
];

export default function RuleToolbar({ onAddLine, onSimulate, onOpenHistory }) {
  return (
    <div className="border-b border-terminal-border-dim bg-terminal-panel">
      {/* Top row: actions and utilities */}
      <div className="border-b border-terminal-border-dim/50">
        <div className="max-w-5xl mx-auto px-4 md:px-8 lg:px-16 flex items-center gap-1 py-1">
          <button
            onClick={onOpenHistory}
            className="text-[10px] md:text-[11px] px-2 py-0.5 font-mono border border-terminal-border-dim bg-terminal-panel text-terminal-amber-dim hover:text-terminal-amber hover:border-terminal-amber/50 transition-colors flex-shrink-0"
            title="View and restore rule snapshots"
          >
            HISTORY
          </button>
          <div className="flex-1" />
          <button
            onClick={onSimulate}
            className="bg-terminal-amber-faint border border-terminal-amber text-terminal-amber-bright active:bg-terminal-amber/20 text-[10px] md:text-[11px] px-2 py-0.5 font-mono font-medium transition-colors flex-shrink-0 select-none shadow-glow-sm"
          >
            SIM
          </button>
        </div>
      </div>
      {/* Bottom row: line type buttons */}
      <div className="max-w-5xl mx-auto px-4 md:px-8 lg:px-16 flex items-center gap-0.5 md:gap-1 py-1.5 overflow-x-auto scrollbar-none">
        {LINE_TYPES.map((lt) => (
          <button
            key={lt.type}
            onClick={() => onAddLine(lt.fullType || lt.type)}
            className={`${lt.color} text-terminal-amber text-[10px] md:text-[11px] px-1.5 md:px-2 py-1 font-mono font-medium transition-colors whitespace-nowrap flex-shrink-0 select-none border`}
            title={`Add ${lt.fullType || lt.type} line (${lt.key})`}
          >
            {lt.type}
          </button>
        ))}
      </div>
    </div>
  );
}
