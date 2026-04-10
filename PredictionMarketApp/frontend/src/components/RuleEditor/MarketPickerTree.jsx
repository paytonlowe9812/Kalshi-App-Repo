import React, { useState, useEffect, useCallback } from 'react';

export default function MarketPickerTree({ onPickTicker }) {
  const [lists, setLists] = useState([]);
  const [expanded, setExpanded] = useState(() => new Set());
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/market-lists');
      const data = await res.json();
      setLists(Array.isArray(data) ? data : []);
    } catch {
      setLists([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const h = () => load();
    window.addEventListener('market-lists-changed', h);
    return () => window.removeEventListener('market-lists-changed', h);
  }, [load]);

  const toggle = (id) => {
    setExpanded((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  };

  if (loading && lists.length === 0) {
    return (
      <div className="text-[10px] font-mono text-terminal-amber-dim py-1 border border-dashed border-terminal-border-dim/50 px-2 rounded-sm">
        Loading saved lists...
      </div>
    );
  }

  if (lists.length === 0) {
    return (
      <div className="text-[10px] font-mono text-terminal-amber-dim py-1.5 border border-dashed border-terminal-border-dim/50 px-2 rounded-sm leading-snug">
        No saved lists. Create named lists on the Markets tab, add tickers from market details, then pick one here.
      </div>
    );
  }

  return (
    <div className="border border-terminal-border-dim/60 bg-terminal-panel/40 rounded-sm max-h-48 overflow-y-auto text-left w-full min-w-0">
      <div className="flex items-center justify-between gap-1 text-[9px] font-mono text-terminal-amber-dim uppercase tracking-wide px-1.5 py-0.5 border-b border-terminal-border-dim/40 sticky top-0 bg-terminal-panel/90">
        <span>Saved lists</span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            load();
          }}
          className="text-terminal-amber hover:text-terminal-amber-bright normal-case shrink-0"
        >
          refresh
        </button>
      </div>
      {lists.map((list) => (
        <div key={list.id} className="border-b border-terminal-border-dim/30 last:border-0">
          <button
            type="button"
            onClick={() => toggle(list.id)}
            className="w-full flex items-center gap-1 px-1.5 py-1 text-left text-[11px] font-mono text-terminal-amber hover:bg-terminal-amber-faint/40"
          >
            <span className="text-terminal-amber-dim w-4 shrink-0">{expanded.has(list.id) ? 'v' : '>'}</span>
            <span className="truncate flex-1">{list.name}</span>
            <span className="text-[10px] text-terminal-amber-dim shrink-0">{list.items?.length || 0}</span>
          </button>
          {expanded.has(list.id) && (
            <div className="pl-5 pr-1 pb-1 space-y-0.5">
              {(list.items || []).map((it) => (
                <button
                  key={it.ticker}
                  type="button"
                  onClick={() => onPickTicker(it.ticker)}
                  className="w-full text-left px-2 py-1 text-[10px] font-mono text-terminal-amber-bright hover:bg-terminal-amber-faint/50 truncate rounded-sm"
                  title={it.title || it.ticker}
                >
                  {it.ticker}
                </button>
              ))}
              {(list.items || []).length === 0 && (
                <p className="text-[10px] font-mono text-terminal-amber-dim px-2 py-1">(empty)</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
