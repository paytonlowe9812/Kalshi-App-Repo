import React, { useEffect, useState, useRef } from 'react';
import useAppStore from '../../store/useAppStore';

const POLL_MS = 1000;

function fmtVal(val) {
  if (typeof val !== 'number' || Number.isNaN(val)) return String(val);
  if (Number.isInteger(val)) return String(val);
  return val.toFixed(2);
}

export default function VarsPanel() {
  const { activeBotId } = useAppStore();
  const [payload, setPayload] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const url = activeBotId
      ? `/api/bots/${activeBotId}/live-variables`
      : '/api/live-variables';

    const tick = async () => {
      const my = ++seq.current;
      setLoading(true);
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const j = await res.json();
        if (cancelled || my !== seq.current) return;
        setPayload(j);
        setErr(null);
      } catch (e) {
        if (!cancelled && my === seq.current) setErr(e.message || 'request failed');
      } finally {
        if (!cancelled && my === seq.current) setLoading(false);
      }
    };

    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [activeBotId]);

  const vars = payload?.variables || {};
  const rows = Object.entries(vars).sort(([a], [b]) => a.localeCompare(b));
  const scope = payload?.scope || (activeBotId ? 'bot' : 'global');
  const showEmptyTable = rows.length === 0 && !err && !loading;

  return (
    <div className="h-full flex flex-col min-h-0">
      <div className="w-full max-w-3xl mx-auto px-3 md:px-4 py-2 border-b border-terminal-border-dim flex flex-wrap items-center gap-2">
        <h2 className="panel-header">LIVE VARIABLES</h2>
        <span className="text-[9px] font-mono text-terminal-amber-dim">
          {activeBotId ? `bot #${activeBotId}` : 'global'}
          {' '}
          | {POLL_MS}ms
        </span>
        {loading && <span className="text-[9px] font-mono text-terminal-amber-muted">sync</span>}
      </div>
      {!activeBotId && (
        <div className="max-w-3xl mx-auto px-3 md:px-4 mt-2 text-[10px] font-mono text-terminal-amber-dim leading-snug">
          Index aggregates and daily P&L (no bot required). Select a bot on BOTS to also load that market, position, resting orders, user vars, and trend fields.
        </div>
      )}
      {payload && !payload.kalshi_client_configured && (
        <div className="max-w-3xl mx-auto px-3 md:px-4 mt-2 text-[10px] font-mono text-terminal-amber border border-terminal-amber/40 px-2 py-1.5 leading-snug">
          No active Kalshi API key. Open CONFIG, add or activate a key so REST market data can load (WebSocket also uses it).
        </div>
      )}
      {err && (
        <div className="max-w-3xl mx-auto px-3 md:px-4 mt-2 text-[10px] font-mono text-terminal-red-text px-2">{err}</div>
      )}
      <div className="flex-1 overflow-auto">
        <table className="w-full max-w-3xl mx-auto px-3 md:px-4 text-left text-[11px] font-mono">
          <thead className="sticky top-0 bg-terminal-bg border-b border-terminal-border-dim z-10">
            <tr>
              <th className="py-1 px-2 text-terminal-amber-dim">NAME</th>
              <th className="py-1 px-2 text-terminal-amber-dim text-right w-28">VALUE</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([name, val]) => (
              <tr key={name} className="border-b border-terminal-border-dim/30 hover:bg-terminal-amber-faint/20">
                <td className="py-1 px-2 text-terminal-amber break-all align-top">{name}</td>
                <td className="py-1 px-2 text-terminal-amber-bright text-right tabular-nums align-top">
                  {fmtVal(val)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {showEmptyTable && (
          <p className="text-xs text-terminal-amber-dim font-mono text-center py-8">NO VARIABLES RETURNED</p>
        )}
      </div>
      {payload?.updated_at && (
        <div className="max-w-3xl mx-auto px-3 md:px-4 py-1 border-t border-terminal-border-dim text-[9px] font-mono text-terminal-amber-muted truncate">
          {scope === 'global' ? 'global · ' : ''}
          {payload.updated_at}
        </div>
      )}
    </div>
  );
}
