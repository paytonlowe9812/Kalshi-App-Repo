import React, { useState, useEffect, useCallback } from 'react';

export default function SavedListsSection() {
  const [lists, setLists] = useState([]);
  const [newName, setNewName] = useState('');
  const [expanded, setExpanded] = useState(() => new Set());
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');

  const refresh = useCallback(async () => {
    try {
      const res = await fetch('/api/market-lists');
      const data = await res.json();
      setLists(Array.isArray(data) ? data : []);
    } catch {
      setLists([]);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const h = () => refresh();
    window.addEventListener('market-lists-changed', h);
    return () => window.removeEventListener('market-lists-changed', h);
  }, [refresh]);

  const createList = async () => {
    const n = newName.trim();
    if (!n) return;
    await fetch('/api/market-lists', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: n }),
    });
    setNewName('');
    refresh();
  };

  const deleteList = async (id) => {
    if (!window.confirm('Delete this list and all tickers in it?')) return;
    await fetch(`/api/market-lists/${id}`, { method: 'DELETE' });
    refresh();
  };

  const removeItem = async (listId, ticker) => {
    await fetch(`/api/market-lists/${listId}/items/${encodeURIComponent(ticker)}`, { method: 'DELETE' });
    refresh();
  };

  const saveRename = async (id) => {
    const n = editName.trim();
    if (!n) return;
    await fetch(`/api/market-lists/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: n }),
    });
    setEditingId(null);
    refresh();
  };

  const toggleList = (id) => {
    setExpanded((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  };

  return (
    <div className="border-b border-terminal-border-dim">
      <div className="px-3 md:px-4 py-2 bg-terminal-panel/80 border-b border-terminal-border-dim/50">
        <div className="text-[10px] font-mono text-terminal-amber-bright uppercase tracking-wider mb-2">Saved lists</div>
        <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New list name..."
            className="input-field text-xs flex-1 min-w-0"
            onKeyDown={(e) => e.key === 'Enter' && createList()}
          />
          <button type="button" onClick={createList} className="btn-primary text-xs py-1.5 px-3 shrink-0">
            CREATE LIST
          </button>
        </div>
      </div>
      {lists.length === 0 && (
        <p className="text-[10px] font-mono text-terminal-amber-dim px-4 py-3">No saved lists yet. Create one above, then add markets from a market&apos;s detail panel.</p>
      )}
      {lists.map((list) => (
        <div key={list.id} className="border-b border-terminal-border-dim/40">
          <div className="flex items-center gap-2 px-3 py-2 bg-terminal-panel hover:bg-terminal-amber-faint/20">
            <button
              type="button"
              onClick={() => toggleList(list.id)}
              className="text-terminal-amber-dim font-mono text-xs w-6 shrink-0"
              aria-expanded={expanded.has(list.id)}
            >
              {expanded.has(list.id) ? 'v' : '>'}
            </button>
            {editingId === list.id ? (
              <>
                <input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="input-field text-xs flex-1 min-w-0"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && saveRename(list.id)}
                />
                <button type="button" onClick={() => saveRename(list.id)} className="text-[10px] font-mono text-terminal-green-text px-2">
                  OK
                </button>
                <button type="button" onClick={() => setEditingId(null)} className="text-[10px] font-mono text-terminal-amber-dim px-2">
                  X
                </button>
              </>
            ) : (
              <>
                <span className="text-xs font-mono text-terminal-amber flex-1 truncate">{list.name}</span>
                <span className="text-[10px] font-mono text-terminal-amber-dim shrink-0">({list.items?.length || 0})</span>
                <button
                  type="button"
                  onClick={() => {
                    setEditingId(list.id);
                    setEditName(list.name);
                  }}
                  className="text-[10px] font-mono text-terminal-amber-dim hover:text-terminal-amber px-1"
                >
                  RENAME
                </button>
                <button
                  type="button"
                  onClick={() => deleteList(list.id)}
                  className="text-[10px] font-mono text-terminal-red-text hover:text-terminal-red-bright px-1"
                >
                  DEL
                </button>
              </>
            )}
          </div>
          {expanded.has(list.id) && (
            <div className="pl-8 pr-2 pb-2 space-y-0.5">
              {(list.items || []).length === 0 && (
                <p className="text-[10px] font-mono text-terminal-amber-dim py-1">Empty -- add from market detail.</p>
              )}
              {(list.items || []).map((it) => (
                <div key={it.ticker} className="flex items-center gap-2 py-1 border-b border-terminal-border-dim/20 last:border-0">
                  <span className="text-[10px] font-mono text-terminal-amber truncate flex-1 min-w-0" title={it.title || it.ticker}>
                    {it.ticker}
                  </span>
                  {it.title && (
                    <span className="text-[10px] font-mono text-terminal-amber-dim truncate max-w-[40%] hidden sm:inline">
                      {it.title}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => removeItem(list.id, it.ticker)}
                    className="text-[10px] font-mono text-terminal-red-text shrink-0 px-1"
                  >
                    [X]
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
