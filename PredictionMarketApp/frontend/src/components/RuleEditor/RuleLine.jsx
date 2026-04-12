import React from 'react';
import ConditionBuilder from './ConditionBuilder';
import ActionBuilder from './ActionBuilder';

const TYPE_COLORS = {
  IF: 'bg-terminal-amber-faint/50 text-terminal-amber border-terminal-amber/30',
  AND: 'bg-terminal-amber-faint/50 text-terminal-amber border-terminal-amber-dim/30',
  OR: 'bg-terminal-amber-faint/50 text-terminal-amber border-terminal-amber-dim/30',
  ELSE: 'bg-terminal-panel text-terminal-amber-dim border-terminal-border-dim',
  THEN: 'bg-terminal-green/20 text-terminal-green-text border-terminal-green/30',
  GOTO: 'bg-terminal-amber-faint/50 text-terminal-amber border-terminal-amber/30',
  CONTINUE: 'bg-terminal-green/20 text-terminal-green-text border-terminal-green-bright/30',
  STOP: 'bg-terminal-red/20 text-terminal-red-text border-terminal-red/30',
  LOG: 'bg-terminal-panel text-terminal-amber-dim border-terminal-border-dim',
  NOOP: 'bg-terminal-panel text-terminal-amber-dim border-terminal-border-dim',
  PAUSE: 'bg-terminal-amber-faint/50 text-terminal-amber border-terminal-amber-dim/30',
  CANCEL_STALE: 'bg-terminal-red/15 text-terminal-red-text border-terminal-red/25',
  SET_VAR: 'bg-terminal-amber-faint/50 text-terminal-amber border-terminal-amber-dim/30',
  ALERT: 'bg-terminal-amber-faint/50 text-terminal-amber border-terminal-amber/30',
};

export default function RuleLine({
  rule,
  index,
  onUpdate,
  onMoveUp,
  onMoveDown,
  onDelete,
  simResult,
  isFirst,
  isLast,
  draggableEnabled = false,
  isDragging = false,
  onDragStart,
  onDragEnd,
}) {
  const typeColor = TYPE_COLORS[rule.line_type] || TYPE_COLORS.LOG;
  const isCondition = ['IF', 'AND', 'OR'].includes(rule.line_type);
  const isAction = ['THEN', 'ELSE'].includes(rule.line_type);
  const isStandalone = ['GOTO', 'STOP', 'CONTINUE', 'LOG', 'NOOP', 'PAUSE', 'CANCEL_STALE', 'SET_VAR', 'ALERT'].includes(rule.line_type);

  return (
    <div className={`px-1.5 md:px-2 py-2 md:py-1.5 border-b border-terminal-border-dim/30 hover:bg-terminal-amber-faint/30 active:bg-terminal-amber-faint/50 group transition-colors ${
      simResult === 'hit' ? 'bg-terminal-green/10' : simResult === 'skipped' ? 'bg-terminal-panel' : ''
    } ${isDragging ? 'opacity-50' : ''}`}>
      {/* Desktop layout */}
      <div className="hidden md:flex items-center gap-1">
        <div
          draggable={draggableEnabled}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
          className={`text-terminal-amber-dim hover:text-terminal-amber text-xs font-mono cursor-grab active:cursor-grabbing select-none ${
            draggableEnabled ? 'opacity-0 group-hover:opacity-100 transition-opacity' : 'opacity-0'
          }`}
          title="Drag to reorder line"
          aria-label="Drag to reorder line"
        >
          ::
        </div>
        <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={onMoveUp} disabled={isFirst} className="text-terminal-amber-dim hover:text-terminal-amber text-xs font-mono disabled:opacity-20">^</button>
          <button onClick={onMoveDown} disabled={isLast} className="text-terminal-amber-dim hover:text-terminal-amber text-xs font-mono disabled:opacity-20">v</button>
        </div>
        <span className="text-[10px] font-mono text-terminal-amber-muted w-4 text-right">{rule.line_number}</span>
        <span className={`badge border text-[9px] px-1 py-0 font-mono ${typeColor}`}>{rule.line_type}</span>
        <div className="flex-1 min-w-0">
          {isCondition && <ConditionBuilder rule={rule} onUpdate={onUpdate} />}
          {isAction && <ActionBuilder rule={rule} onUpdate={onUpdate} />}
          {isStandalone && <ActionBuilder rule={rule} onUpdate={onUpdate} />}
        </div>
        {rule.exec_count > 0 && <span className="text-[10px] font-mono text-terminal-amber-dim border border-terminal-border-dim px-1">x{rule.exec_count}</span>}
        {simResult && <span className="text-xs font-mono text-terminal-amber">{simResult === 'hit' ? 'V' : simResult === 'skipped' ? '-' : simResult === 'branched' ? '>' : ''}</span>}
        <button onClick={onDelete} className="text-terminal-amber-muted hover:text-terminal-red-text opacity-0 group-hover:opacity-100 transition-all text-xs font-mono">[X]</button>
      </div>

      {/* Mobile layout */}
      <div className="md:hidden">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-terminal-amber-muted w-4 text-right">{rule.line_number}</span>
          <span className={`badge border text-[10px] px-1.5 py-0.5 font-mono ${typeColor}`}>{rule.line_type}</span>
          {rule.exec_count > 0 && <span className="text-[10px] font-mono text-terminal-amber-dim border border-terminal-border-dim px-1">x{rule.exec_count}</span>}
          <div className="flex gap-1 ml-auto">
            <div
              draggable={draggableEnabled}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              className="text-terminal-amber-dim active:text-terminal-amber text-xs font-mono w-6 h-6 flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
              title="Drag to reorder line"
              aria-label="Drag to reorder line"
            >
              ::
            </div>
            <button onClick={onMoveUp} disabled={isFirst} className="text-terminal-amber-dim active:text-terminal-amber text-xs font-mono disabled:opacity-20 w-6 h-6 flex items-center justify-center">^</button>
            <button onClick={onMoveDown} disabled={isLast} className="text-terminal-amber-dim active:text-terminal-amber text-xs font-mono disabled:opacity-20 w-6 h-6 flex items-center justify-center">v</button>
            <button onClick={onDelete} className="text-terminal-amber-muted active:text-terminal-red-text text-xs font-mono w-6 h-6 flex items-center justify-center">[X]</button>
          </div>
        </div>
        <div className="mt-1.5 ml-6 overflow-x-auto">
          {isCondition && <ConditionBuilder rule={rule} onUpdate={onUpdate} />}
          {isAction && <ActionBuilder rule={rule} onUpdate={onUpdate} />}
          {isStandalone && <ActionBuilder rule={rule} onUpdate={onUpdate} />}
        </div>
      </div>
    </div>
  );
}
