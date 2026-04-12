import React, { useEffect, useState, useRef } from 'react';
import useAppStore from '../../store/useAppStore';

const POLL_MS = 1000;
const FETCH_TIMEOUT_MS = 22000;

function fmtVal(val) {
  if (typeof val !== 'number' || Number.isNaN(val)) return String(val);
  if (Number.isInteger(val)) return String(val);
  return val.toFixed(2);
}

async function fetchLiveJson(url) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    if (!res.ok) {
      const msg = res.status === 504 ? 'Server timeout (live-variables too slow)' : `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return res.json();
  } catch (e) {
    if (e.name === 'AbortError') throw new Error('Request timed out — try again');
    throw e;
  } finally {
    clearTimeout(t);
  }
}

export default function VarsPanel() {
  const { activeBotId } = useAppStore();
  const [payload, setPayload] = useState(null);
  const [err, setErr] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const hadSuccessRef = useRef(false);

  useEffect(() => {
    const url = activeBotId
      ? `/api/bots/${activeBotId}/live-variables`
      : '/api/live-variables';

    let cancelled = false;
    let timeoutId = null;

    hadSuccessRef.current = false;
    setInitialLoading(true);
    setPayload(null);
    setErr(null);

    const scheduleNext = () => {
      if (cancelled) return;
      timeoutId = setTimeout(run, POLL_MS);
    };

    const run = async () => {
      if (cancelled) return;
      const firstEver = !hadSuccessRef.current;
      if (firstEver) setInitialLoading(true);
      else setRefreshing(true);
      try {
        const j = await fetchLiveJson(url);
        if (cancelled) return;
        setPayload(j);
        setErr(null);
        hadSuccessRef.current = true;
      } catch (e) {
        if (!cancelled) {
          setErr(e.message || 'request failed');
          if (!hadSuccessRef.current) setPayload(null);
        }
      } finally {
        if (!cancelled) {
          setInitialLoading(false);
          setRefreshing(false);
          scheduleNext();
        }
      }
    };

    run();

    return () => {
      cancelled = true;
      if (timeoutId != null) clearTimeout(timeoutId);
    };
  }, [activeBotId]);

  const vars = payload?.variables || {};
  const rows = Object.entries(vars).sort(([a], [b]) => a.localeCompare(b));
  const scope = payload?.scope || (activeBotId ? 'bot' : 'global');
  const showEmptyTable = rows.length === 0 && !err && !initialLoading;
  const botTicker = payload?.market_ticker || '';
  const botSide = String(payload?.contract_side || '').toUpperCase();

  return (
    <div className="h-full flex flex-col min-h-0">
      <div className="w-full max-w-3xl mx-auto px-3 md:px-4 py-2 border-b border-terminal-border-dim flex flex-wrap items-center gap-2">
        <h2 className="panel-header">LIVE VARIABLES</h2>
        <span className="text-[9px] font-mono text-terminal-amber-dim">
          {activeBotId ? `bot #${activeBotId}` : 'global'}
          {activeBotId && botTicker ? ` | ${botSide || '?'} | ${botTicker}` : ''}
          {' '}
          | poll after each response (~{POLL_MS}ms min)
        </span>
        {initialLoading && <span className="text-[9px] font-mono text-terminal-amber-muted">loading</span>}
        {refreshing && !initialLoading && (
          <span className="text-[9px] font-mono text-terminal-amber-muted/80">refresh</span>
        )}
      </div>
      {!activeBotId && (
        <div className="max-w-3xl mx-auto px-3 md:px-4 mt-2 text-[10px] font-mono text-terminal-amber-dim leading-snug">
          Index aggregates and daily P&L (no bot required). Select a bot on BOTS to also load that market, position, resting orders, user vars, and trend fields.
        </div>
      )}
      {activeBotId && botTicker && (
        <div className="max-w-3xl mx-auto px-3 md:px-4 mt-2 text-[10px] font-mono text-terminal-amber-dim leading-snug">
          Bid/Ask/LastTraded are for this bot market ticker and side. Index rows (for example ETH.YES) can come from a different ticker.
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
