import React from 'react';
import useAppStore from '../../store/useAppStore';

export default function TradeLogRow({ trade }) {
  const { setActiveBotId, setActiveTab } = useAppStore();
  const goToLine = () => { if (trade.bot_id) { setActiveBotId(trade.bot_id); setActiveTab('editor'); } };
  const pnl = trade.pnl || 0;
  return (
    <div className={`border-b border-terminal-border-dim/30 ${pnl > 0 ? 'bg-terminal-green/5' : pnl < 0 ? 'bg-terminal-red/5' : ''}`}>
      <div className="hidden md:flex items-center gap-3 px-4 py-2 text-xs font-mono">
        <span className="text-terminal-amber-dim w-16">{trade.logged_at ? new Date(trade.logged_at).toLocaleTimeString() : '--'}</span>
        <span className="text-terminal-amber w-32 truncate">{trade.bot_name || '--'}</span>
        <span className="text-terminal-amber-dim w-28 truncate">{trade.market_ticker || '--'}</span>
        <span className={`w-20 font-semibold ${trade.action?.includes('BUY') ? 'text-terminal-green-text' : trade.action?.includes('SELL') ? 'text-terminal-red-text' : 'text-terminal-amber'}`}>{trade.action}</span>
        <span className="text-terminal-amber w-8 text-right">{trade.contracts || '--'}</span>
        <span className="text-terminal-amber-dim w-20 text-right">{trade.entry_price != null ? `${trade.entry_price}` : '--'}{trade.exit_price != null ? ` > ${trade.exit_price}` : ''}</span>
        <span className={`w-16 text-right font-semibold ${pnl > 0 ? 'text-terminal-green-text' : pnl < 0 ? 'text-terminal-red-text' : 'text-terminal-amber-dim'}`}>{pnl !== 0 ? `$${pnl.toFixed(2)}` : '--'}</span>
        {trade.rule_line && <button onClick={goToLine} className="text-terminal-amber-bright hover:text-terminal-amber text-[10px] font-mono">L{trade.rule_line}</button>}
      </div>
      <div className="md:hidden flex items-center gap-3 px-3 py-2.5 active:bg-terminal-amber-faint/50">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2"><span className={`text-xs font-mono font-semibold ${trade.action?.includes('BUY') ? 'text-terminal-green-text' : trade.action?.includes('SELL') ? 'text-terminal-red-text' : 'text-terminal-amber'}`}>{trade.action}</span><span className="text-[11px] text-terminal-amber-dim font-mono">{trade.contracts || 0}x</span></div>
          <div className="text-[11px] text-terminal-amber-dim font-mono mt-0.5 truncate">{trade.bot_name || '--'} -- {trade.market_ticker || '--'}</div>
        </div>
        <div className="flex flex-col items-end flex-shrink-0"><span className={`text-xs font-mono font-semibold ${pnl > 0 ? 'text-terminal-green-text' : pnl < 0 ? 'text-terminal-red-text' : 'text-terminal-amber-dim'}`}>{pnl !== 0 ? `$${pnl.toFixed(2)}` : '--'}</span><span className="text-[10px] text-terminal-amber-muted font-mono">{trade.logged_at ? new Date(trade.logged_at).toLocaleTimeString() : ''}</span></div>
        {trade.rule_line && <button onClick={goToLine} className="text-terminal-amber-bright active:text-terminal-amber text-[10px] font-mono flex-shrink-0 w-7 h-7 flex items-center justify-center">L{trade.rule_line}</button>}
      </div>
    </div>
  );
}
