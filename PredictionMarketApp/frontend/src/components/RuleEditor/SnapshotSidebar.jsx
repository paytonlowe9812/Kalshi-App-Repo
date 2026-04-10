import React, { useEffect, useState } from 'react';

export default function SnapshotSidebar({ botId, onRestore, collapsed, onToggle }) {
  const [snapshots, setSnapshots] = useState([]);
  const fetchSnapshots = async () => { if (!botId) return; try { const res = await fetch(`/api/bots/${botId}/rules/snapshots`); setSnapshots(await res.json()); } catch {} };
  useEffect(() => { fetchSnapshots(); }, [botId]);
  const saveSnapshot = async () => { const name = prompt('Snapshot name (optional):'); await fetch(`/api/bots/${botId}/rules/snapshot`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name || null }) }); fetchSnapshots(); };
  const restoreSnapshot = async (snapId) => { await fetch(`/api/bots/${botId}/rules/snapshots/${snapId}/restore`, { method: 'POST' }); onRestore(); fetchSnapshots(); };

  if (collapsed) {
    return (
      <div className="w-7 border-l border-terminal-border-dim bg-terminal-panel flex items-start justify-center pt-3">
        <button onClick={onToggle} className="text-terminal-amber-dim hover:text-terminal-amber text-xs font-mono [writing-mode:vertical-lr]">HISTORY</button>
      </div>
    );
  }

  return (
    <div className="w-44 border-l border-terminal-border-dim bg-terminal-panel flex flex-col">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-terminal-border-dim">
        <span className="panel-header">HISTORY</span>
        <button onClick={onToggle} className="text-terminal-amber-dim hover:text-terminal-amber text-xs font-mono">{'<<'}</button>
      </div>
      <div className="px-2 py-1.5">
        <button onClick={saveSnapshot} className="btn-secondary text-xs w-full py-1">SAVE SNAPSHOT</button>
      </div>
      <div className="flex-1 overflow-y-auto px-2">
        {snapshots.map((snap) => (
          <div key={snap.id} className="py-1.5 border-b border-terminal-border-dim/30">
            <div className="text-xs text-terminal-amber font-mono truncate">{snap.name || `Auto - ${new Date(snap.created_at).toLocaleTimeString()}`}</div>
            <div className="text-[10px] text-terminal-amber-dim font-mono">{new Date(snap.created_at).toLocaleDateString()}</div>
            <button onClick={() => restoreSnapshot(snap.id)} className="text-[10px] text-terminal-amber-bright hover:text-terminal-amber font-mono mt-0.5">RESTORE</button>
          </div>
        ))}
        {snapshots.length === 0 && <p className="text-[10px] text-terminal-amber-muted font-mono text-center mt-4">NO SNAPSHOTS YET</p>}
      </div>
    </div>
  );
}
