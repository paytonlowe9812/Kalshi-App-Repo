import React, { useEffect, useRef, useState, useCallback } from 'react';

const LEVEL_COLOR = {
  INFO:  'text-terminal-green-text',
  WARN:  'text-terminal-amber',
  ERROR: 'text-terminal-red-text',
  DEBUG: 'text-terminal-amber-dim',
};

const EVENT_COLOR = {
  ORDER_PLACED:     'text-terminal-green-text font-bold',
  ORDER_ERROR:      'text-terminal-red-text font-bold',
  SKIPPED_COOLDOWN: 'text-terminal-amber-dim',
  SKIPPED_GUARD:    'text-terminal-amber-dim',
  TICK_FIRED:       'text-terminal-amber',
  TICK_IDLE:        'text-terminal-border-dim',
};

export default function BotDebugLog({ botId }) {
  const [lines, setLines]         = useState([]);
  const [paused, setPaused]       = useState(false);
  const [filter, setFilter]       = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [sinceId, setSinceId]     = useState(0);
  const bottomRef                 = useRef(null);
  const pausedRef                 = useRef(false);
  pausedRef.current               = paused;

  const poll = useCallback(async () => {
    if (pausedRef.current) return;
    try {
      const params = new URLSearchParams({ since_id: sinceId, limit: 200 });
      if (botId) params.set('bot_id', botId);
      const res = await fetch(`/api/logs/bot-events?${params}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.length > 0) {
        setSinceId(data[data.length - 1].id);
        setLines(prev => {
          const next = [...prev, ...data];
          return next.slice(-2000); // keep last 2000 in UI
        });
      }
    } catch {}
  }, [botId, sinceId]);

  useEffect(() => {
    const id = setInterval(poll, 800);
    return () => clearInterval(id);
  }, [poll]);

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines, paused]);

  const visible = lines.filter(l => {
    if (levelFilter !== 'ALL' && l.level !== levelFilter) return false;
    if (filter && !l.message.toLowerCase().includes(filter.toLowerCase()) &&
        !l.bot_name.toLowerCase().includes(filter.toLowerCase()) &&
        !l.event.toLowerCase().includes(filter.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full min-h-0 bg-terminal-bg font-mono">
      {/* toolbar */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-terminal-border-dim shrink-0 flex-wrap">
        <span className="text-[10px] text-terminal-amber-bright tracking-wider">BOT DEBUG LOG</span>
        <input
          type="text"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="filter…"
          className="input-field text-[10px] h-6 w-32 px-1.5 py-0"
        />
        <select
          value={levelFilter}
          onChange={e => setLevelFilter(e.target.value)}
          className="input-field text-[10px] h-6 px-1 py-0"
        >
          {['ALL','INFO','WARN','ERROR','DEBUG'].map(l => <option key={l}>{l}</option>)}
        </select>
        <button
          type="button"
          onClick={() => setPaused(p => !p)}
          className={`text-[10px] border px-2 py-0.5 ${paused ? 'border-terminal-amber text-terminal-amber' : 'border-terminal-border-dim text-terminal-amber-dim hover:text-terminal-amber'}`}
        >
          {paused ? 'RESUME' : 'PAUSE'}
        </button>
        <button
          type="button"
          onClick={() => { setLines([]); setSinceId(0); }}
          className="text-[10px] text-terminal-amber-dim hover:text-terminal-red-text border border-terminal-border-dim px-2 py-0.5"
        >
          CLEAR
        </button>
        <span className="text-[9px] text-terminal-amber-dim ml-auto">{visible.length} lines</span>
      </div>

      {/* log lines */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0 min-h-0">
        {visible.length === 0 && (
          <p className="text-[10px] text-terminal-amber-dim pt-4 text-center">
            Waiting for bot events… start a bot to see live output.
          </p>
        )}
        {visible.map(l => (
          <div key={l.id} className="flex gap-2 text-[10px] leading-5 hover:bg-terminal-amber-faint/10">
            <span className="text-terminal-amber-dim shrink-0 select-none">{l.ts}</span>
            <span className={`shrink-0 w-14 truncate ${LEVEL_COLOR[l.level] || 'text-terminal-amber-dim'}`}>{l.level}</span>
            <span className="text-terminal-amber-dim shrink-0 w-20 truncate">{l.bot_name}</span>
            <span className={`shrink-0 w-28 truncate ${EVENT_COLOR[l.event] || 'text-terminal-amber-dim'}`}>{l.event}</span>
            <span className="text-terminal-amber flex-1 break-all">{l.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
