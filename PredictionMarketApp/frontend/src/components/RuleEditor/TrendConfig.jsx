import React, { useEffect, useState } from 'react';

const PRICE_SOURCES = ['YES_price', 'NO_price', 'Bid', 'Ask', 'LastTraded'];
const POLL_OPTIONS = [
  { label: '500ms', value: 500 },
  { label: '1s',    value: 1000 },
  { label: '2s',    value: 2000 },
  { label: '5s',    value: 5000 },
  { label: '10s',   value: 10000 },
  { label: '30s',   value: 30000 },
];

export default function TrendConfig({ botId, bot, onSave }) {
  const [pollMs, setPollMs]           = useState(1000);
  const [confirmCount, setConfirmCount] = useState(3);
  const [priceSource, setPriceSource] = useState('YES_price');
  const [countInput, setCountInput]   = useState('3');

  useEffect(() => {
    if (!bot) return;
    setPollMs(bot.trend_poll_ms ?? 1000);
    setConfirmCount(bot.trend_confirm_count ?? 3);
    setCountInput(String(bot.trend_confirm_count ?? 3));
    setPriceSource(bot.trend_price_source || 'YES_price');
  }, [bot?.id]);

  const save = (patch) => {
    if (!botId) return;
    fetch(`/api/bots/${botId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (onSave) onSave(patch);
  };

  const handlePollChange = (e) => {
    const v = parseInt(e.target.value);
    setPollMs(v);
    save({ trend_poll_ms: v });
  };

  const handleSourceChange = (e) => {
    setPriceSource(e.target.value);
    save({ trend_price_source: e.target.value });
  };

  const handleCountBlur = () => {
    const v = Math.max(1, parseInt(countInput) || 1);
    setConfirmCount(v);
    setCountInput(String(v));
    save({ trend_confirm_count: v });
  };

  return (
    <div className="flex items-center gap-3 flex-wrap py-0.5">
      <span className="text-[10px] font-mono font-bold text-terminal-amber-dim tracking-wider shrink-0">
        TREND
      </span>

      <div className="flex items-center gap-1 shrink-0">
        <span className="text-[9px] text-terminal-amber-dim font-mono">WATCH</span>
        <select
          value={priceSource}
          onChange={handleSourceChange}
          className="input-field text-[10px] py-0"
        >
          {PRICE_SOURCES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <span className="text-[9px] text-terminal-amber-dim font-mono">EVERY</span>
        <select
          value={pollMs}
          onChange={handlePollChange}
          className="input-field text-[10px] py-0"
        >
          {POLL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <span className="text-[9px] text-terminal-amber-dim font-mono">CONFIRM AFTER</span>
        <input
          type="number"
          value={countInput}
          min={1}
          max={999}
          onChange={(e) => setCountInput(e.target.value)}
          onBlur={handleCountBlur}
          className="input-field text-[10px] py-0 w-12 text-center"
        />
        <span className="text-[9px] text-terminal-amber-dim font-mono">IN A ROW</span>
      </div>

      <span className="text-[9px] text-terminal-amber-dim/60 font-mono shrink-0">
        → TrendUp / TrendDown / ConsecutiveUp / ConsecutiveDown
      </span>
    </div>
  );
}
