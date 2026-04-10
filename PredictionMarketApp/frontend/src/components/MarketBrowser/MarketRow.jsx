import React, { useState, useEffect } from 'react';

function formatTimeLeft(closeTime) {
  if (!closeTime) return '--';
  const now = Date.now();
  const close = new Date(closeTime).getTime();
  let diff = close - now;
  if (diff <= 0) return 'EXPIRED';

  const days = Math.floor(diff / 86400000);
  diff %= 86400000;
  const hours = Math.floor(diff / 3600000);
  diff %= 3600000;
  const mins = Math.floor(diff / 60000);
  diff %= 60000;
  const secs = Math.floor(diff / 1000);

  if (days > 365) return `${Math.floor(days / 365)}y ${Math.floor((days % 365) / 30)}mo`;
  if (days > 30) return `${Math.floor(days / 30)}mo ${days % 30}d`;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  if (mins > 0) return `${mins}m ${secs}s`;
  return `${secs}s`;
}

function useTimeLeft(closeTime) {
  const [label, setLabel] = useState(() => formatTimeLeft(closeTime));
  useEffect(() => {
    setLabel(formatTimeLeft(closeTime));
    const id = setInterval(() => setLabel(formatTimeLeft(closeTime)), 1000);
    return () => clearInterval(id);
  }, [closeTime]);
  return label;
}

function expiryColor(closeTime) {
  if (!closeTime) return 'text-terminal-amber-dim';
  const diff = new Date(closeTime).getTime() - Date.now();
  if (diff <= 0) return 'text-terminal-red-text';
  if (diff < 3600000) return 'text-terminal-red-text';
  if (diff < 86400000) return 'text-terminal-amber-bright';
  return 'text-terminal-amber-dim';
}

export default function MarketRow({ market, isFavorite, onToggleFavorite, onSelect, selected }) {
  const yesPrice = market.yes_bid || market.last_price || '--';
  const noPrice = market.no_bid || (market.yes_bid ? 100 - market.yes_bid : '--');
  const timeLeft = useTimeLeft(market.close_time);
  const timeColor = expiryColor(market.close_time);

  return (
    <div onClick={() => onSelect(market)} className={`border-b border-terminal-border-dim/50 cursor-pointer transition-colors active:bg-terminal-amber-faint ${selected ? 'bg-terminal-amber-faint/50' : 'hover:bg-terminal-amber-faint/30'}`}>
      <div className="hidden md:flex items-center gap-3 px-4 py-2.5">
        <button onClick={(e) => { e.stopPropagation(); onToggleFavorite(market.ticker); }} className={`text-sm font-mono ${isFavorite ? 'text-terminal-amber-bright text-glow-sm' : 'text-terminal-amber-muted hover:text-terminal-amber'}`}>*</button>
        <span className="text-[10px] font-mono text-terminal-amber-dim w-32 truncate">{market.ticker}</span>
        <span className="text-xs font-mono text-terminal-amber flex-1 truncate">{market.title}</span>
        <span className={`text-[10px] font-mono ${timeColor} w-20 text-right tabular-nums`}>{timeLeft}</span>
        <span className="text-xs font-mono text-terminal-green-text w-14 text-right">{yesPrice}c</span>
        <span className="text-xs font-mono text-terminal-red-text w-14 text-right">{noPrice}c</span>
        <span className="text-[10px] font-mono text-terminal-amber-dim w-16 text-right">{market.volume ? `${(market.volume / 1000).toFixed(1)}k` : '--'}</span>
      </div>
      <div className="md:hidden flex items-center gap-3 px-3 py-3">
        <button onClick={(e) => { e.stopPropagation(); onToggleFavorite(market.ticker); }} className={`text-lg flex-shrink-0 w-8 h-8 flex items-center justify-center font-mono ${isFavorite ? 'text-terminal-amber-bright' : 'text-terminal-amber-muted'}`}>*</button>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono text-terminal-amber line-clamp-1">{market.title}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] font-mono text-terminal-amber-dim truncate">{market.ticker}</span>
            <span className={`text-[10px] font-mono ${timeColor} tabular-nums`}>{timeLeft}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-0.5 flex-shrink-0">
          <div className="flex gap-2"><span className="text-xs font-mono text-terminal-green-text">{yesPrice}c</span><span className="text-xs font-mono text-terminal-red-text">{noPrice}c</span></div>
          <span className="text-[10px] font-mono text-terminal-amber-dim">{market.volume ? `${(market.volume / 1000).toFixed(1)}k vol` : ''}</span>
        </div>
      </div>
    </div>
  );
}
