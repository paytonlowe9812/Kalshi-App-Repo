import React, { useState, useMemo, useRef, useEffect } from 'react';
import BotRow from './BotRow';

export default function BotGroup({
  group,
  onSelectBot,
  onStartBot,
  onStopBot,
  onCopyBot,
  onDeleteBot,
  onStartAll,
  onStopAll,
  onRequestDeleteGroup,
  onMoveToGroup,
  availableGroups,
  selectedIds,
  onToggleSelect,
  onToggleSelectGroup,
}) {
  const storageKey = `botgroup-expanded-${group.id}`;
  const [expanded, setExpanded] = useState(() => {
    const saved = localStorage.getItem(storageKey);
    return saved === null ? true : saved === 'true';
  });

  const toggleExpanded = (next) => {
    setExpanded(next);
    localStorage.setItem(storageKey, String(next));
  };
  const groupCheckboxRef = useRef(null);

  const groupBotIds = useMemo(() => (group.bots || []).map((b) => b.id), [group.bots]);
  const groupAllSelected = groupBotIds.length > 0 && groupBotIds.every((id) => selectedIds?.includes(id));
  const groupSomeSelected = groupBotIds.some((id) => selectedIds?.includes(id));

  useEffect(() => {
    const el = groupCheckboxRef.current;
    if (el) el.indeterminate = groupSomeSelected && !groupAllSelected;
  }, [groupSomeSelected, groupAllSelected]);

  return (
    <div className="border-b border-terminal-border-dim">
      <div
        className="flex items-center gap-1 px-2 py-1.5 bg-terminal-panel cursor-pointer hover:bg-terminal-amber-faint active:bg-terminal-amber-faint transition-colors"
        onClick={() => toggleExpanded(!expanded)}
      >
        <label
          className="flex items-center justify-center w-5 shrink-0 cursor-pointer md:w-5 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0 -ml-1 md:ml-0"
          onClick={(e) => e.stopPropagation()}
          title={groupBotIds.length === 0 ? 'No bots in this folder' : 'Select all bots in this folder'}
        >
          <input
            ref={groupCheckboxRef}
            type="checkbox"
            checked={groupAllSelected}
            disabled={groupBotIds.length === 0}
            onChange={() => onToggleSelectGroup?.(group)}
            className="w-3.5 h-3.5 border-terminal-border-dim rounded-sm disabled:opacity-30"
            style={{ accentColor: '#D4A017' }}
            aria-label={`Select all bots in folder ${group.name}`}
          />
        </label>
        <span className={`text-terminal-amber-dim font-mono text-xs transition-transform shrink-0 ${expanded ? 'rotate-90' : ''}`}>
          &gt;
        </span>
        <span className="text-terminal-amber font-mono text-xs shrink-0">[DIR]</span>
        <span className="text-xs font-mono font-medium text-terminal-amber flex-1">{group.name}</span>
        <div className="flex gap-0.5 flex-wrap justify-end" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            onClick={() => onStartAll(group.id)}
            className="text-[9px] font-mono px-1.5 py-0.5 text-terminal-green-text border border-terminal-green/50 hover:border-terminal-green-bright"
            title="Start all bots in this group"
          >
            START ALL
          </button>
          <button
            type="button"
            onClick={() => onStopAll(group.id)}
            className="text-[9px] font-mono px-1.5 py-0.5 text-terminal-red-text border border-terminal-red/50 hover:border-terminal-red-bright"
            title="Stop all bots in this group"
          >
            STOP ALL
          </button>
          <button
            type="button"
            onClick={() => onRequestDeleteGroup?.()}
            className="text-[9px] font-mono px-1.5 py-0.5 text-terminal-red-text border border-terminal-red/40 hover:border-terminal-red-bright"
            title="Delete this folder; bots move to ungrouped"
          >
            DEL DIR
          </button>
        </div>
      </div>
      {expanded && group.bots?.map((bot) => (
        <div key={bot.id} className="pl-5">
          <BotRow
            bot={bot}
            onSelect={onSelectBot}
            onStart={onStartBot}
            onStop={onStopBot}
            onCopy={onCopyBot}
            onDelete={onDeleteBot}
            onMoveToGroup={onMoveToGroup}
            availableGroups={availableGroups}
            selected={selectedIds?.includes(bot.id)}
            onToggleSelect={onToggleSelect}
          />
        </div>
      ))}
    </div>
  );
}
