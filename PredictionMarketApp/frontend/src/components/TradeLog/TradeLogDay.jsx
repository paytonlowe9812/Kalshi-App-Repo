import React, { useState } from 'react';
import TradeLogRow from './TradeLogRow';

export default function TradeLogDay({ date, trades }) {
  const [expanded, setExpanded] = useState(true);

  const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const dateStr = new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div>
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-2 bg-terminal-panel border-b border-terminal-border-dim cursor-pointer active:bg-terminal-amber-faint hover:bg-terminal-amber-faint font-mono"
      >
        <svg
          className={`w-3 h-3 text-terminal-amber-dim transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-xs md:text-sm text-terminal-amber truncate">{dateStr}</span>
        <span className="text-[10px] md:text-xs text-terminal-amber-dim flex-shrink-0">{trades.length}</span>
        <span className={`text-xs font-mono ml-auto font-semibold flex-shrink-0 ${
          totalPnl > 0 ? 'text-terminal-green-text' : totalPnl < 0 ? 'text-terminal-red-text' : 'text-terminal-amber-dim'
        }`}>
          Net: ${totalPnl.toFixed(2)}
        </span>
      </div>
      {expanded && trades.map((trade) => (
        <TradeLogRow key={trade.id} trade={trade} />
      ))}
    </div>
  );
}
