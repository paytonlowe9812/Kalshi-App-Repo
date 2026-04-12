import React, { useEffect, useState } from 'react';

export default function SnapshotSidebar({ botId, onRestore, open, onClose }) {
  const [snapshots, setSnapshots] = useState([]);
  const [restoring, setRestoring] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [seedingBuiltins, setSeedingBuiltins] = useState(false);

  const fetchSnapshots = async () => {
    if (!botId) return;
    try {
      const res = await fetch(`/api/bots/${botId}/rules/snapshots`);
      setSnapshots(await res.json());
    } catch {}
  };

  useEffect(() => { fetchSnapshots(); }, [botId]);
  useEffect(() => { if (open) fetchSnapshots(); }, [open]);

  const seedBuiltinStrategies = async () => {
    if (!botId) return;
    setSeedingBuiltins(true);
    try {
      const res = await fetch(`/api/bots/${botId}/rules/snapshots/builtin`, { method: 'POST' });
      if (!res.ok) return;
      await fetchSnapshots();
    } finally {
      setSeedingBuiltins(false);
    }
  };

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
    setRestoring(snapId);
    await fetch(`/api/bots/${botId}/rules/snapshots/${snapId}/restore`, { method: 'POST' });
    setRestoring(null);
    onRestore();
    fetchSnapshots();
    onClose();
  };

  const deleteSnapshot = async (snapId, label) => {
    if (!window.confirm(`Delete snapshot "${label}"? This cannot be undone.`)) return;
    setDeleting(snapId);
    try {
      const res = await fetch(`/api/bots/${botId}/rules/snapshots/${snapId}`, { method: 'DELETE' });
      if (!res.ok) return;
      fetchSnapshots();
    } finally {
      setDeleting(null);
    }
  };

  if (!open) return null;

  const ownSnapshots = snapshots.filter((s) => s.bot_id === botId);
  const otherSnapshots = snapshots.filter((s) => s.bot_id !== botId);

  const SnapItem = ({ snap }) => {
    const label = snap.name || `Auto — ${new Date(snap.created_at).toLocaleTimeString()}`;
    const busy = restoring === snap.id || deleting === snap.id;
    return (
      <div className="py-2 border-b border-terminal-border-dim/30">
        <div className="flex items-start justify-between gap-1">
          <div className="min-w-0">
            <div className="text-xs text-terminal-amber font-mono truncate">
              {label}
            </div>
            <div className="text-[10px] text-terminal-amber-dim font-mono">
              {new Date(snap.created_at).toLocaleDateString()}
              {snap.bot_id !== botId && (
                <span className="ml-1 text-terminal-amber-dim/70">· {snap.bot_name || `Bot #${snap.bot_id}`}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0 mt-0.5">
            <button
              type="button"
              onClick={() => deleteSnapshot(snap.id, label)}
              disabled={busy}
              className="text-[10px] text-terminal-red-text/80 hover:text-terminal-red-text font-mono disabled:opacity-40"
              title="Delete snapshot"
            >
              {deleting === snap.id ? '...' : 'DEL'}
            </button>
            <button
              type="button"
              onClick={() => restoreSnapshot(snap.id)}
              disabled={busy}
              className="text-[10px] text-terminal-amber-bright hover:text-terminal-amber font-mono disabled:opacity-40"
            >
              {restoring === snap.id ? '...' : 'APPLY'}
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div className="fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 max-h-[75vh] flex flex-col bg-terminal-bg border border-terminal-amber/60 shadow-glow-sm font-mono">
        <div className="flex items-center justify-between px-3 py-2 border-b border-terminal-border-dim">
          <span className="panel-header">snapshots</span>
          <button onClick={onClose} className="text-terminal-amber-dim hover:text-terminal-amber text-xs">[X]</button>
        </div>
        <div className="px-3 py-2 border-b border-terminal-border-dim space-y-2">
          <button onClick={saveSnapshot} className="btn-secondary text-xs w-full py-1">
            SAVE SNAPSHOT
          </button>
          <button
            type="button"
            onClick={seedBuiltinStrategies}
            disabled={seedingBuiltins}
            className="btn-secondary text-xs w-full py-1 disabled:opacity-40"
            title="Insert or refresh all built-in strategy templates"
          >
            {seedingBuiltins ? 'LOADING...' : 'LOAD BUILT-IN STRATEGIES'}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 min-h-0">
          {/* This bot's snapshots */}
          {ownSnapshots.length > 0 && (
            <>
              <div className="text-[9px] text-terminal-amber-dim font-mono tracking-widest mb-1 mt-1">THIS BOT</div>
              {ownSnapshots.map((snap) => <SnapItem key={snap.id} snap={snap} />)}
            </>
          )}

          {/* Other bots' snapshots */}
          {otherSnapshots.length > 0 && (
            <>
              <div className="text-[9px] text-terminal-amber-dim font-mono tracking-widest mb-1 mt-3">OTHER BOTS</div>
              {otherSnapshots.map((snap) => <SnapItem key={snap.id} snap={snap} />)}
            </>
          )}

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
