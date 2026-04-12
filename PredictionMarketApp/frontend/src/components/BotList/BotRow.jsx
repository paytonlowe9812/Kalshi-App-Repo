import React from 'react';
import StatusDot from '../shared/StatusDot';
import BotActions from './BotActions';

function StartStopButton({ status, onStart, onStop }) {
  const isRunning = status === 'running';
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        isRunning ? onStop() : onStart();
      }}
      title={isRunning ? 'Pause bot' : 'Start bot'}
      className={`flex items-center justify-center w-7 h-7 shrink-0 border font-mono transition-colors ${
        isRunning
          ? 'border-terminal-amber text-terminal-amber hover:bg-terminal-amber/10 active:bg-terminal-amber/20'
          : 'border-terminal-green-text text-terminal-green-text hover:bg-terminal-green/10 active:bg-terminal-green/20'
      }`}
      aria-label={isRunning ? 'Stop bot' : 'Start bot'}
    >
      {isRunning ? (
        /* Pause icon — two vertical bars */
        <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
          <rect x="1.5" y="1" width="2.5" height="8" />
          <rect x="6" y="1" width="2.5" height="8" />
        </svg>
      ) : (
        /* Play icon — right-pointing triangle */
        <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
          <polygon points="2,1 9,5 2,9" />
        </svg>
      )}
    </button>
  );
}

export default function BotRow({ bot, onSelect, onStart, onStop, onCopy, onDelete, onMoveToGroup, availableGroups, selected, onToggleSelect }) {
  return (
    <div
      onClick={() => onSelect(bot)}
      className={`border-b border-terminal-border-dim/50 cursor-pointer transition-colors active:bg-terminal-amber-faint hover:bg-terminal-amber-faint/50 ${
        selected ? 'bg-terminal-amber-faint/25' : ''
      }`}
    >
      {/* Desktop row */}
      <div className="hidden md:flex items-center gap-2 px-2 md:px-3 py-2 group">
        <label
          className="flex items-center justify-center w-5 shrink-0 cursor-pointer"
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={!!selected}
            onChange={() => onToggleSelect?.(bot.id)}
            className="registry-checkbox w-3.5 h-3.5 border border-terminal-amber bg-terminal-bg rounded-sm"
            style={{ accentColor: '#D4A017' }}
            aria-label={`Select ${bot.name}`}
          />
        </label>
        <StatusDot status={bot.status} />
        <span className="text-xs font-mono font-medium text-terminal-amber flex-1 truncate">{bot.name}</span>
        <span className="text-[10px] text-terminal-amber-dim font-mono w-24 shrink-0 truncate">
          {bot.market_ticker || '--'}
          {bot.auto_roll && <span className="text-terminal-green-text ml-1" title={`Auto-roll: ${bot.series_ticker || 'on'}`}>[R]</span>}
        </span>
        <span className={`text-[10px] font-mono w-14 shrink-0 text-right truncate ${
          bot.status === 'running' ? 'text-terminal-green-text' : bot.status === 'error' ? 'text-terminal-red-text' : 'text-terminal-amber-dim'
        }`}>
          {bot.status}
        </span>
        <span className="text-[10px] text-terminal-amber-dim font-mono w-10 shrink-0 text-right tabular-nums">{bot.run_count || 0}</span>
        <StartStopButton
          status={bot.status}
          onStart={() => onStart(bot.id)}
          onStop={() => onStop(bot.id)}
        />
        <BotActions
          bot={bot}
          groups={availableGroups}
          onMoveToGroup={(groupId) => onMoveToGroup?.(bot.id, groupId)}
          onEdit={() => onSelect(bot)}
          onStart={() => onStart(bot.id)}
          onStop={() => onStop(bot.id)}
          onCopy={() => onCopy(bot.id)}
          onDelete={() => onDelete(bot.id)}
        />
      </div>

      {/* Mobile card row */}
      <div className="md:hidden flex items-center gap-2 px-3 py-2.5">
        <label
          className="flex items-center justify-center w-9 shrink-0 cursor-pointer min-h-[44px] min-w-[44px] -ml-1"
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={!!selected}
            onChange={() => onToggleSelect?.(bot.id)}
            className="registry-checkbox w-4 h-4 border border-terminal-amber bg-terminal-bg rounded-sm"
            style={{ accentColor: '#D4A017' }}
            aria-label={`Select ${bot.name}`}
          />
        </label>
        <StatusDot status={bot.status} className="flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono font-medium text-terminal-amber truncate">{bot.name}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-terminal-amber-dim font-mono truncate">
              {bot.market_ticker || 'NO MARKET'}
              {bot.auto_roll && <span className="text-terminal-green-text ml-1">[R]</span>}
            </span>
            <span className={`text-[10px] font-mono ${
              bot.status === 'running' ? 'text-terminal-green-text' : bot.status === 'error' ? 'text-terminal-red-text' : 'text-terminal-amber-dim'
            }`}>
              {bot.status}
            </span>
          </div>
        </div>
        <StartStopButton
          status={bot.status}
          onStart={() => onStart(bot.id)}
          onStop={() => onStop(bot.id)}
        />
        <BotActions
          bot={bot}
          groups={availableGroups}
          onMoveToGroup={(groupId) => onMoveToGroup?.(bot.id, groupId)}
          onEdit={() => onSelect(bot)}
          onStart={() => onStart(bot.id)}
          onStop={() => onStop(bot.id)}
          onCopy={() => onCopy(bot.id)}
          onDelete={() => onDelete(bot.id)}
        />
      </div>
    </div>
  );
}
