import React from 'react';

export default function StatsRow({ summary }) {
  if (!summary) return null;
  const cards = [
    { label: 'TOTAL VALUE', value: `$${(summary.total_value || 0).toFixed(2)}`, color: 'text-terminal-amber-bright text-glow-sm' },
    { label: "TODAY P&L", value: `$${(summary.today_pnl || 0).toFixed(2)}`, color: summary.today_pnl >= 0 ? 'text-terminal-green-text' : 'text-terminal-red-text' },
    { label: 'WIN RATE', value: `${summary.win_rate || 0}%`, sub: `${summary.wins || 0} / ${summary.total_trades || 0}`, color: 'text-terminal-amber' },
    { label: 'TRADES', value: summary.total_trades || 0, color: 'text-terminal-amber' },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 px-3 md:px-4 py-3">
      {cards.map((c) => (
        <div key={c.label} className="card text-center rounded-none">
          <div className="text-[10px] text-terminal-amber-dim uppercase tracking-wider font-mono mb-1">{c.label}</div>
          <div className={`text-lg md:text-xl font-semibold font-mono ${c.color}`}>{c.value}</div>
          {c.sub && <div className="text-[10px] text-terminal-amber-dim font-mono mt-0.5">{c.sub}</div>}
        </div>
      ))}
    </div>
  );
}
