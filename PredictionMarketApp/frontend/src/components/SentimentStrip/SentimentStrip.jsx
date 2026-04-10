import React, { useEffect, useMemo, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import useIndexStore from '../../store/useIndexStore';
import IndexDropdown from './IndexDropdown';
import CoinTile from './CoinTile';
import Modal from '../shared/Modal';
import { defaultIndexLabel } from '../../utils/indexMarketLabel';

export default function SentimentStrip() {
  const { activeIndexId, setActiveIndexId, indexQuoteMode, setIndexQuoteMode } = useAppStore();
  const { indexes, liveData, fetchIndexes, fetchLiveData } = useIndexStore();
  const [showIndexModal, setShowIndexModal] = useState(false);
  const [editingIndexId, setEditingIndexId] = useState(null);
  const [newName, setNewName] = useState('');
  const [newMarkets, setNewMarkets] = useState([]);
  const [savedLists, setSavedLists] = useState([]);

  useEffect(() => {
    fetchIndexes();
  }, []);

  useEffect(() => {
    if (indexes.length > 0 && !activeIndexId) {
      setActiveIndexId(indexes[0].id);
    }
  }, [indexes, activeIndexId]);

  useEffect(() => {
    if (!activeIndexId) return;
    fetchLiveData(activeIndexId);
    const interval = setInterval(() => fetchLiveData(activeIndexId), 5000);
    return () => clearInterval(interval);
  }, [activeIndexId]);

  useEffect(() => {
    if (!showIndexModal) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/market-lists');
        const data = await res.json();
        if (!cancelled) setSavedLists(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setSavedLists([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showIndexModal]);

  const uniqueCoins = useMemo(() => {
    const coins = liveData?.coins;
    if (!Array.isArray(coins)) return [];
    const seen = new Set();
    return coins.filter((c) => {
      const t = (c.ticker || '').trim();
      if (!t || seen.has(t)) return false;
      seen.add(t);
      return true;
    });
  }, [liveData]);

  const addMarketsFromSavedList = (list) => {
    const items = list.items || [];
    setNewMarkets((prev) => {
      const seen = new Set(prev.map((m) => m.ticker));
      const merged = [...prev];
      for (const it of items) {
        const t = (it.ticker || '').trim();
        if (!t || seen.has(t)) continue;
        seen.add(t);
        merged.push({ ticker: t, label: defaultIndexLabel(t, it.title || '').slice(0, 64) });
      }
      return merged;
    });
  };

  const openCreateModal = () => {
    setEditingIndexId(null);
    setNewName('');
    setNewMarkets([]);
    setShowIndexModal(true);
  };

  const openEditModal = () => {
    if (!activeIndexId) return;
    const idx = indexes.find((i) => i.id === activeIndexId);
    if (!idx) return;
    setEditingIndexId(activeIndexId);
    setNewName(idx.name || '');
    setNewMarkets(
      (idx.markets || []).map((m) => {
        const t = m.ticker || '';
        const stored = (m.label || '').trim();
        const lb = stored || defaultIndexLabel(t, '');
        return { ticker: t, label: lb.slice(0, 64) };
      }),
    );
    setShowIndexModal(true);
  };

  const closeIndexModal = () => {
    setShowIndexModal(false);
    setEditingIndexId(null);
    setNewName('');
    setNewMarkets([]);
    setSavedLists([]);
  };

  const saveIndex = async () => {
    if (!newName.trim()) return;
    const marketsPayload = newMarkets.map((m) => ({
      ticker: m.ticker,
      label: String(m.label || m.ticker || '').slice(0, 64) || m.ticker,
    }));
    const editedId = editingIndexId;
    if (editedId != null) {
      await fetch(`/api/indexes/${editedId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), markets: marketsPayload }),
      });
    } else {
      await fetch('/api/indexes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), markets: marketsPayload }),
      });
    }
    closeIndexModal();
    await fetchIndexes();
    if (editedId != null && activeIndexId === editedId) {
      fetchLiveData(activeIndexId);
    }
  };

  return (
    <div className="bg-terminal-surface border-b border-terminal-border-dim px-1.5 py-1 md:py-0 md:min-h-0 md:h-8 md:flex md:items-center gap-1">
      <div className="flex items-center gap-1 shrink-0">
        <IndexDropdown onCreateNew={openCreateModal} onEditIndex={openEditModal} />

        <button
          type="button"
          onClick={openEditModal}
          disabled={!activeIndexId}
          title="Edit selected index"
          className="flex-shrink-0 px-1 h-[22px] border border-terminal-border-dim hover:border-terminal-border text-terminal-amber-dim hover:text-terminal-amber items-center justify-center text-[8px] font-mono transition-colors disabled:opacity-30 disabled:pointer-events-none"
        >
          EDIT
        </button>
        <button
          type="button"
          onClick={openCreateModal}
          title="Create new index"
          className="flex-shrink-0 w-[22px] h-[22px] border border-terminal-border-dim hover:border-terminal-border text-terminal-amber-dim hover:text-terminal-amber items-center justify-center text-[11px] font-mono transition-colors"
        >
          +
        </button>

        {liveData && (
          <div className="flex items-center gap-0.5 text-[9px] leading-none font-mono px-1 py-0.5 border border-terminal-border-dim">
            <span className="text-terminal-green-text">{liveData.bull_count}</span>
            <span className="text-terminal-amber-dim">/</span>
            <span className="text-terminal-red-text">{liveData.bear_count}</span>
          </div>
        )}

        {liveData && (
          <div
            className="flex items-center border border-terminal-border-dim rounded-sm overflow-hidden shrink-0"
            role="group"
            aria-label="Index quote display mode"
          >
            <button
              type="button"
              onClick={() => setIndexQuoteMode('prices')}
              className={`px-1.5 py-0.5 text-[8px] font-mono uppercase ${
                indexQuoteMode === 'prices'
                  ? 'bg-terminal-amber-faint text-terminal-amber-bright'
                  : 'text-terminal-amber-dim hover:text-terminal-amber'
              }`}
              title="Bid and ask on each side (cents), like Kalshi prices view"
            >
              price
            </button>
            <button
              type="button"
              onClick={() => setIndexQuoteMode('odds')}
              className={`px-1 py-0.5 text-[7px] font-mono uppercase border-l border-terminal-border-dim ${
                indexQuoteMode === 'odds'
                  ? 'bg-terminal-amber-faint text-terminal-amber-bright'
                  : 'text-terminal-amber-dim hover:text-terminal-amber'
              }`}
              title="Implied % from last trade or mid of spread (math), not raw bid/ask"
            >
              odds
            </button>
          </div>
        )}
      </div>

      {liveData && (
        <div className="flex items-center gap-0.5 overflow-x-auto flex-1 min-w-0 py-0.5 md:py-0 -mx-0.5 px-0.5 scrollbar-none">
          {uniqueCoins.map((coin) => (
            <CoinTile
              key={coin.ticker}
              label={coin.label}
              quoteMode={indexQuoteMode}
              yesBid={coin.yes_bid}
              yesAsk={coin.yes_ask}
              noBid={coin.no_bid}
              noAsk={coin.no_ask}
              yesOdds={coin.yes_odds}
              noOdds={coin.no_odds}
              ticker={coin.ticker}
            />
          ))}
        </div>
      )}

      {!liveData && !activeIndexId && (
        <span className="text-[10px] text-terminal-amber-dim font-mono py-0.5 md:py-0">NO INDEX SELECTED</span>
      )}

      <Modal
        open={showIndexModal}
        onClose={closeIndexModal}
        title={editingIndexId != null ? 'EDIT SENTIMENT INDEX' : 'CREATE SENTIMENT INDEX'}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-terminal-amber-dim font-mono mb-1">INDEX NAME</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. CryptoIndex"
              className="input-field w-full"
            />
          </div>
          <div>
            <label className="block text-xs text-terminal-amber-dim font-mono mb-1">FROM SAVED LIST</label>
            <p className="text-[10px] text-terminal-amber-muted font-mono mb-2 leading-snug">
              Lists are created on the Markets tab. Click a list to add all of its tickers to this index (duplicates skipped).
            </p>
            {savedLists.length === 0 ? (
              <p className="text-xs text-terminal-amber-dim font-mono border border-dashed border-terminal-border-dim px-3 py-4 text-center">
                No saved lists yet. Open Markets, create a list, add tickers from market details, then return here.
              </p>
            ) : (
              <div className="bg-terminal-bg border border-terminal-border-dim max-h-48 overflow-y-auto">
                {savedLists.map((list) => {
                  const n = (list.items || []).length;
                  return (
                    <button
                      key={list.id}
                      type="button"
                      onClick={() => addMarketsFromSavedList(list)}
                      className="block w-full text-left px-3 py-2.5 text-xs font-mono text-terminal-amber hover:bg-terminal-amber-faint border-b border-terminal-border-dim/30 last:border-0"
                    >
                      <span className="text-terminal-amber-bright">{list.name}</span>
                      <span className="text-terminal-amber-dim ml-2">
                        ({n} {n === 1 ? 'market' : 'markets'})
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          {(newMarkets.length > 0 || editingIndexId != null) && (
            <div className="space-y-2">
              <label className="block text-xs text-terminal-amber-dim font-mono">MARKETS IN INDEX</label>
              {newMarkets.length === 0 && editingIndexId != null && (
                <p className="text-[10px] text-terminal-amber-muted font-mono">No markets yet. Add from a saved list above.</p>
              )}
              {newMarkets.map((m, i) => (
                <div key={`${m.ticker}-${i}`} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={m.label}
                    onChange={(e) => {
                      const updated = [...newMarkets];
                      updated[i] = { ...m, label: e.target.value };
                      setNewMarkets(updated);
                    }}
                    className="input-field w-20"
                  />
                  <span className="text-xs text-terminal-amber-dim font-mono flex-1 truncate">{m.ticker}</span>
                  <button
                    type="button"
                    onClick={() => setNewMarkets(newMarkets.filter((_, j) => j !== i))}
                    className="text-terminal-red-text hover:text-terminal-red-bright text-sm font-mono"
                  >
                    [X]
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={closeIndexModal} className="btn-secondary">CANCEL</button>
            <button type="button" onClick={saveIndex} className="btn-primary">
              {editingIndexId != null ? 'SAVE CHANGES' : 'SAVE'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
