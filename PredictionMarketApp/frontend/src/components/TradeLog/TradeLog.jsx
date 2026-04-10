import React, { useEffect, useState } from 'react';
import TradeLogDay from './TradeLogDay';

export default function TradeLog() {
  const [trades, setTrades] = useState([]);
  const [botFilter, setBotFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchTrades = async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (botFilter) params.set('bot_id', botFilter);
    if (actionFilter) params.set('action', actionFilter);
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    try {
      const res = await fetch(`/api/logs?${params}`);
      const data = await res.json();
      setTrades(data);
    } catch {
      setTrades([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchTrades();
  }, []);

  useEffect(() => {
    const debounce = setTimeout(fetchTrades, 300);
    return () => clearTimeout(debounce);
  }, [botFilter, actionFilter, fromDate, toDate]);

  const clearFilters = () => {
    setBotFilter('');
    setActionFilter('');
    setFromDate('');
    setToDate('');
  };

  const groupedByDay = {};
  trades.forEach((t) => {
    const day = t.logged_at ? t.logged_at.split('T')[0] : t.logged_at?.split(' ')[0] || 'unknown';
    if (!groupedByDay[day]) groupedByDay[day] = [];
    groupedByDay[day].push(t);
  });

  const sortedDays = Object.keys(groupedByDay).sort().reverse();

  return (
    <div className="h-full flex flex-col font-mono">
      <div className="w-full max-w-5xl mx-auto px-3 md:px-4 py-3 border-b border-terminal-border-dim space-y-2 md:space-y-0">
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-none">
          <input
            type="text"
            value={botFilter}
            onChange={(e) => setBotFilter(e.target.value)}
            placeholder="BOT ID..."
            className="input-field text-xs md:text-sm w-20 md:w-24 flex-shrink-0"
          />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="input-field text-xs md:text-sm flex-shrink-0"
          >
            <option value="">ALL</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
            <option value="CLOSE">CLOSE</option>
            <option value="PAPER_BUY">PAPER BUY</option>
            <option value="PAPER_SELL">PAPER SELL</option>
          </select>
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="input-field text-xs md:text-sm flex-shrink-0" />
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="input-field text-xs md:text-sm flex-shrink-0" />
          <button onClick={clearFilters} className="btn-secondary text-xs py-1.5 md:py-1 flex-shrink-0">CLEAR</button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-3 md:px-4">
          {loading && <div className="text-center text-sm text-terminal-amber-dim py-8 uppercase">LOADING...</div>}
          {!loading && trades.length === 0 && (
            <div className="text-center text-sm text-terminal-amber-dim py-12 uppercase">NO TRADES RECORDED YET</div>
          )}
          {sortedDays.map((day) => (
            <TradeLogDay key={day} date={day} trades={groupedByDay[day]} />
          ))}
        </div>
      </div>
    </div>
  );
}
