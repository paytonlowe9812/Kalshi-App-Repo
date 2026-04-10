import React, { useEffect, useState } from 'react';
import useBotStore from '../../store/useBotStore';

export default function MarketDetail({ market, onClose }) {
  const { bots } = useBotStore();
  const [detail, setDetail] = useState(null);
  const [assignBotId, setAssignBotId] = useState('');
  const [savedLists, setSavedLists] = useState([]);
  const [addToListId, setAddToListId] = useState('');

  useEffect(() => {
    const f = async () => {
      try {
        const res = await fetch(`/api/markets/${encodeURIComponent(market.ticker)}`);
        const j = await res.json();
        setDetail(j.market || j);
      } catch {
        setDetail(null);
      }
    };
    f();
  }, [market.ticker]);

  useEffect(() => {
    const f = async () => {
      try {
        const res = await fetch('/api/market-lists');
        const data = await res.json();
        setSavedLists(Array.isArray(data) ? data : []);
      } catch {
        setSavedLists([]);
      }
    };
    f();
  }, [market.ticker]);

  const assignToBot = async () => {
    if (!assignBotId) return;
    await fetch(`/api/bots/${assignBotId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ market_ticker: market.ticker }),
    });
    setAssignBotId('');
  };

  const addToSavedList = async () => {
    if (!addToListId) return;
    const d = detail || market;
    const title = (d.title || d.subtitle || '').trim() || null;
    await fetch(`/api/market-lists/${addToListId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker: market.ticker, title }),
    });
    setAddToListId('');
    window.dispatchEvent(new Event('market-lists-changed'));
  };

  const d = detail || market;
  return (
    <div className="bg-terminal-panel border-t border-terminal-border-dim p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-xs font-mono font-semibold text-terminal-amber text-glow-sm">{d.title}</h3>
          <p className="text-[10px] font-mono text-terminal-amber-dim mt-0.5">{d.ticker}</p>
        </div>
        <button type="button" onClick={onClose} className="text-terminal-amber-dim hover:text-terminal-amber text-xs font-mono">
          [X]
        </button>
      </div>
      {d.subtitle && <p className="text-xs text-terminal-amber-dim font-mono mb-3">{d.subtitle}</p>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="text-center">
          <div className="text-[10px] text-terminal-amber-dim uppercase font-mono">YES</div>
          <div className="text-sm font-mono text-terminal-green-text">{d.yes_bid || d.last_price || '--'}c</div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-terminal-amber-dim uppercase font-mono">NO</div>
          <div className="text-sm font-mono text-terminal-red-text">{d.no_bid || '--'}c</div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-terminal-amber-dim uppercase font-mono">VOL</div>
          <div className="text-sm font-mono text-terminal-amber">{d.volume || '--'}</div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-terminal-amber-dim uppercase font-mono">STATUS</div>
          <div className="text-sm font-mono text-terminal-amber">{d.status || '--'}</div>
        </div>
      </div>
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 mb-3">
        <span className="text-xs text-terminal-amber-dim font-mono shrink-0">ADD TO LIST:</span>
        <select
          value={addToListId}
          onChange={(e) => setAddToListId(e.target.value)}
          className="input-field text-xs py-1 flex-1 min-w-0"
        >
          <option value="">Choose a saved list...</option>
          {savedLists.map((L) => (
            <option key={L.id} value={L.id}>
              {L.name}
            </option>
          ))}
        </select>
        <button type="button" onClick={addToSavedList} disabled={!addToListId} className="btn-secondary text-xs py-1 px-2 shrink-0">
          ADD
        </button>
      </div>
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 mb-3">
        <span className="text-xs text-terminal-amber-dim font-mono shrink-0">ASSIGN BOT:</span>
        <select value={assignBotId} onChange={(e) => setAssignBotId(e.target.value)} className="input-field text-xs py-1 flex-1 min-w-0">
          <option value="">Select bot...</option>
          {bots.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <button type="button" onClick={assignToBot} disabled={!assignBotId} className="btn-primary text-xs py-1 px-2 shrink-0">
          ASSIGN
        </button>
      </div>
      <a
        href={`https://kalshi.com/markets/${market.ticker}`}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-terminal-amber-bright hover:text-terminal-amber font-mono"
      >
        OPEN ON KALSHI.COM &gt;
      </a>
    </div>
  );
}
