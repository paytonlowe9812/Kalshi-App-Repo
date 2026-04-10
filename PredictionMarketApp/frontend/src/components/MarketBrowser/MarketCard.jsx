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

export default function MarketCard({ market, isFavorite, onToggleFavorite, onSelect }) {
  const yesPrice = market.yes_bid || market.last_price || '--';
  const noPrice = market.no_bid || (market.yes_bid ? 100 - market.yes_bid : '--');
  const timeLeft = useTimeLeft(market.close_time);
  const timeColor = expiryColor(market.close_time);

  return (
    <div onClick={() => onSelect(market)} className="card cursor-pointer hover:border-terminal-border transition-colors rounded-none">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-xs font-mono font-medium text-terminal-amber line-clamp-2 flex-1">{market.title}</h3>
        <button onClick={(e) => { e.stopPropagation(); onToggleFavorite(market.ticker); }} className={`text-sm ml-2 font-mono ${isFavorite ? 'text-terminal-amber-bright text-glow-sm' : 'text-terminal-amber-muted hover:text-terminal-amber'}`}>*</button>
      </div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] text-terminal-amber-dim font-mono truncate">{market.ticker}</span>
        <span className={`text-[10px] font-mono ${timeColor} ml-auto tabular-nums`}>{timeLeft}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="badge bg-terminal-green/20 text-terminal-green-text border-terminal-green/30 rounded-none">YES {yesPrice}c</span>
        <span className="badge bg-terminal-red/20 text-terminal-red-text border-terminal-red/30 rounded-none">NO {noPrice}c</span>
        <span className="text-[10px] text-terminal-amber-dim ml-auto font-mono">Vol: {market.volume ? `${(market.volume / 1000).toFixed(1)}k` : '--'}</span>
      </div>
    </div>
  );
}
