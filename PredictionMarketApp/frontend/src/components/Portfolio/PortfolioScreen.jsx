import React, { useEffect, useState } from 'react';
import StatsRow from './StatsRow';
import PnLChart from './PnLChart';

export default function PortfolioScreen() {
  const [summary, setSummary] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [chartType, setChartType] = useState('line');
  const [range, setRange] = useState('today');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  useEffect(() => { const f = async () => { try { setSummary(await (await fetch('/api/portfolio/summary')).json()); } catch {} }; f(); }, []);
  useEffect(() => { const f = async () => { const params = new URLSearchParams({ range }); if (range === 'custom' && fromDate && toDate) { params.set('from_date', fromDate); params.set('to_date', toDate); } try { setChartData(await (await fetch(`/api/portfolio/chart?${params}`)).json()); } catch { setChartData([]); } }; f(); }, [range, fromDate, toDate]);

  return (
    <div className="h-full overflow-y-auto pb-4">
      <StatsRow summary={summary} />
      <div className="px-3 md:px-4 py-3">
        <div className="card rounded-none">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-4">
            <div className="flex gap-2">
              <button onClick={() => setChartType('line')} className={`text-xs px-3 py-1.5 md:py-1 font-mono select-none border rounded-none ${chartType === 'line' ? 'border-terminal-amber text-terminal-amber-bright bg-terminal-amber-faint shadow-glow-sm' : 'border-terminal-border-dim text-terminal-amber-dim'}`}>LINE</button>
              <button onClick={() => setChartType('bar')} className={`text-xs px-3 py-1.5 md:py-1 font-mono select-none border rounded-none ${chartType === 'bar' ? 'border-terminal-amber text-terminal-amber-bright bg-terminal-amber-faint shadow-glow-sm' : 'border-terminal-border-dim text-terminal-amber-dim'}`}>BAR</button>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto scrollbar-none">
              <button onClick={() => setRange('today')} className={`text-xs px-3 py-1.5 md:py-1 font-mono flex-shrink-0 select-none border rounded-none ${range === 'today' ? 'border-terminal-amber text-terminal-amber-bright bg-terminal-amber-faint' : 'border-terminal-border-dim text-terminal-amber-dim'}`}>TODAY</button>
              <button onClick={() => setRange('custom')} className={`text-xs px-3 py-1.5 md:py-1 font-mono flex-shrink-0 select-none border rounded-none ${range === 'custom' ? 'border-terminal-amber text-terminal-amber-bright bg-terminal-amber-faint' : 'border-terminal-border-dim text-terminal-amber-dim'}`}>CUSTOM</button>
              {range === 'custom' && (<><input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="input-field text-xs flex-shrink-0" /><input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="input-field text-xs flex-shrink-0" /></>)}
            </div>
          </div>
          <PnLChart data={chartData} chartType={chartType} />
          {summary && (
            <div className="flex flex-col md:flex-row gap-2 md:gap-6 mt-4 pt-3 border-t border-terminal-border-dim">
              {summary.best_day && (<div className="text-xs font-mono"><span className="text-terminal-amber-dim">Best Day: </span><span className="text-terminal-green-text font-semibold">+${summary.best_day.pnl?.toFixed(2)}</span><span className="text-terminal-amber-muted ml-1">({summary.best_day.date})</span></div>)}
              {summary.worst_day && (<div className="text-xs font-mono"><span className="text-terminal-amber-dim">Worst Day: </span><span className="text-terminal-red-text font-semibold">${summary.worst_day.pnl?.toFixed(2)}</span><span className="text-terminal-amber-muted ml-1">({summary.worst_day.date})</span></div>)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
