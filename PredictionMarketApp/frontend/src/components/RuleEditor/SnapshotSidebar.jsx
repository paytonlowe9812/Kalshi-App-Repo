import React, { useEffect, useState } from 'react';

export default function SnapshotSidebar({ botId, onRestore, open, onClose }) {
  const [snapshots, setSnapshots] = useState([]);

  const fetchSnapshots = async () => {
    if (!botId) return;
    try {
      const res = await fetch(`/api/bots/${botId}/rules/snapshots`);
      setSnapshots(await res.json());
    } catch {}
  };

  useEffect(() => { fetchSnapshots(); }, [botId]);
  useEffect(() => { if (open) fetchSnapshots(); }, [open]);

  const saveSnapshot = async () => {
    const name = prompt('Snapshot name (optional):');
    await fetch(`/api/bots/${botId}/rules/snapshot`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || null }),
    });
    fetchSnapshots();
  };

  const restoreSnapshot = async (snapId) => {
    await fetch(`/api/bots/${botId}/rules/snapshots/${snapId}/restore`, { method: 'POST' });
    onRestore();
    fetchSnapshots();
    onClose();
  };

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Floating panel */}
      <div className="fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 max-h-[70vh] flex flex-col bg-terminal-bg border border-terminal-amber/60 shadow-glow-sm font-mono">
        <div className="flex items-center justify-between px-3 py-2 border-b border-terminal-border-dim">
          <span className="panel-header">RULE HISTORY</span>
          <button
            onClick={onClose}
            className="text-terminal-amber-dim hover:text-terminal-amber text-xs"
            aria-label="Close"
          >
            [X]
          </button>
        </div>
        <div className="px-3 py-2 border-b border-terminal-border-dim">
          <button onClick={saveSnapshot} className="btn-secondary text-xs w-full py-1">
            SAVE SNAPSHOT
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-2">
          {snapshots.map((snap) => (
            <div key={snap.id} className="py-2 border-b border-terminal-border-dim/30">
              <div className="text-xs text-terminal-amber font-mono truncate">
                {snap.name || `Auto — ${new Date(snap.created_at).toLocaleTimeString()}`}
              </div>
              <div className="text-[10px] text-terminal-amber-dim font-mono">
                {new Date(snap.created_at).toLocaleDateString()}
              </div>
              <button
                onClick={() => restoreSnapshot(snap.id)}
                className="text-[10px] text-terminal-amber-bright hover:text-terminal-amber font-mono mt-0.5"
              >
                RESTORE
              </button>
            </div>
          ))}
          {snapshots.length === 0 && (
            <p className="text-[10px] text-terminal-amber-muted font-mono text-center mt-4">
              NO SNAPSHOTS YET
            </p>
          )}
        </div>
      </div>
    </>
  );
}
