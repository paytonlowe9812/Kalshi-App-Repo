import React from 'react';
import Toggle from '../shared/Toggle';
import useAppStore from '../../store/useAppStore';

export default function AppSettings({ settings, onUpdate }) {
  const { theme, setTheme } = useAppStore();
  const s = settings || {};
  const toggleTheme = () => { const next = theme === 'dark' ? 'light' : 'dark'; setTheme(next); onUpdate('theme', next); };
  const exportBots = async () => { const res = await fetch('/api/bots'); const bots = await res.json(); const blob = new Blob([JSON.stringify(bots, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'bots_backup.json'; a.click(); URL.revokeObjectURL(url); };
  const importBots = (e) => { const file = e.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = async (ev) => { try { const bots = JSON.parse(ev.target.result); for (const bot of bots) { await fetch('/api/bots', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: bot.name, market_ticker: bot.market_ticker }) }); } } catch {} }; reader.readAsText(file); };
  return (
    <div className="card space-y-4 font-mono">
      <h3 className="panel-header">APP CONFIG</h3>
      <Toggle checked={theme === 'dark'} onChange={toggleTheme} label={`THEME: ${theme === 'dark' ? 'DARK' : 'LIGHT'}`} />
      <div className="flex items-center gap-3"><span className="text-xs text-terminal-amber-dim font-mono">LOOP INTERVAL:</span><select value={s.loop_interval_ms || '500'} onChange={(e) => onUpdate('loop_interval_ms', e.target.value)} className="input-field text-xs"><option value="500">500ms</option><option value="1000">1s</option><option value="5000">5s</option><option value="10000">10s</option><option value="30000">30s</option><option value="60000">60s</option></select></div>
      <div className="flex items-center gap-3"><span className="text-xs text-terminal-amber-dim font-mono">MAX BOTS:</span><input type="number" value={s.max_simultaneous_bots || 10} onChange={(e) => onUpdate('max_simultaneous_bots', e.target.value)} className="input-field w-20 text-xs" min={1} /></div>
      <div className="flex gap-2 pt-2 border-t border-terminal-border-dim">
        <button type="button" onClick={exportBots} className="btn-secondary text-xs">EXPORT BOTS</button>
        <label className="btn-secondary text-xs cursor-pointer">IMPORT BOTS<input type="file" accept=".json" onChange={importBots} className="hidden" /></label>
      </div>
    </div>
  );
}
