import React, { useState } from 'react';

export default function ExportHistory() {
  const today = new Date().toISOString().split('T')[0];
  const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
  const [fromDate, setFromDate] = useState(thirtyDaysAgo);
  const [toDate, setToDate] = useState(today);
  const exportFile = (format) => { window.open(`/api/export/trades?format=${format}&from_date=${fromDate}&to_date=${toDate}`, '_blank'); };
  return (
    <div className="card font-mono">
      <h3 className="panel-header mb-3">EXPORT TRADE HISTORY</h3>
      <div className="flex items-center gap-3 mb-3">
        <div><label className="block text-[10px] text-terminal-amber-dim font-mono mb-0.5">START</label><input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="input-field text-xs" /></div>
        <div><label className="block text-[10px] text-terminal-amber-dim font-mono mb-0.5">END</label><input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="input-field text-xs" /></div>
      </div>
      <div className="flex gap-2">
        <button type="button" onClick={() => exportFile('csv')} className="btn-primary text-xs">EXPORT CSV</button>
        <button type="button" onClick={() => exportFile('json')} className="btn-secondary text-xs">EXPORT JSON</button>
      </div>
      <p className="text-[10px] text-terminal-amber-muted font-mono mt-2">CSV includes: Fills, P&L by Market, Open Positions. JSON includes same as single file.</p>
    </div>
  );
}
