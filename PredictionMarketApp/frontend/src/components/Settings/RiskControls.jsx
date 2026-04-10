import React from 'react';
import Toggle from '../shared/Toggle';

export default function RiskControls({ settings, onUpdate, onPanic }) {
  const s = settings || {};
  return (
    <div className="card space-y-5 font-mono">
      <h3 className="panel-header">GLOBAL RISK CONTROLS</h3>
      <div className="space-y-2">
        <Toggle checked={s.daily_loss_limit_enabled === 'true'} onChange={(v) => onUpdate('daily_loss_limit_enabled', v ? 'true' : 'false')} label="DAILY LOSS LIMIT" />
        {s.daily_loss_limit_enabled === 'true' && (<div className="flex items-center gap-2 ml-13 text-xs font-mono"><span className="text-terminal-amber-dim">Stop all bots when daily P&L drops below $</span><input type="number" value={s.daily_loss_limit_amount || 100} onChange={(e) => onUpdate('daily_loss_limit_amount', e.target.value)} className="input-field w-20 text-xs" /></div>)}
      </div>
      <div className="space-y-2">
        <Toggle checked={s.max_open_positions_enabled === 'true'} onChange={(v) => onUpdate('max_open_positions_enabled', v ? 'true' : 'false')} label="MAX OPEN POSITIONS" />
        {s.max_open_positions_enabled === 'true' && (<div className="flex items-center gap-2 ml-13 text-xs font-mono"><span className="text-terminal-amber-dim">Never hold more than</span><input type="number" value={s.max_open_positions || 10} onChange={(e) => onUpdate('max_open_positions', e.target.value)} className="input-field w-16 text-xs" /><span className="text-terminal-amber-dim">open positions</span></div>)}
      </div>
      <div className="space-y-2">
        <Toggle checked={s.window_exposure_cap_enabled === 'true'} onChange={(v) => onUpdate('window_exposure_cap_enabled', v ? 'true' : 'false')} label="WINDOW EXPOSURE CAP" />
        {s.window_exposure_cap_enabled === 'true' && (<div className="space-y-1"><div className="flex items-center gap-2 ml-13 text-xs font-mono"><span className="text-terminal-amber-dim">Max</span><input type="number" value={s.window_exposure_cap_contracts || 30} onChange={(e) => onUpdate('window_exposure_cap_contracts', e.target.value)} className="input-field w-16 text-xs" /><span className="text-terminal-amber-dim">contracts in a 15-min window</span></div><p className="text-[10px] text-terminal-amber-muted ml-13 font-mono">Prevents over-exposure when multiple coins move at once</p></div>)}
      </div>
      <div className="space-y-2">
        <Toggle checked={s.circuit_breaker_enabled === 'true'} onChange={(v) => onUpdate('circuit_breaker_enabled', v ? 'true' : 'false')} label="CIRCUIT BREAKER" />
        {s.circuit_breaker_enabled === 'true' && (<div className="space-y-2 ml-13"><p className="text-[10px] text-terminal-amber-muted font-mono">Blocks pending entries when a position reverses sharply or settles as a loss in the same 15-min window</p><Toggle checked={s.circuit_breaker_force_close === 'true'} onChange={(v) => onUpdate('circuit_breaker_force_close', v ? 'true' : 'false')} label="Force-close open positions when tripped" /></div>)}
      </div>
      <div className="border-t border-terminal-border-dim pt-4">
        <button type="button" onClick={onPanic} className="w-full py-3 border border-terminal-red text-terminal-red-text bg-transparent hover:bg-terminal-red/20 font-mono font-semibold text-sm transition-colors shadow-glow-red">EMERGENCY STOP -- CLOSE ALL POSITIONS & STOP ALL BOTS</button>
      </div>
    </div>
  );
}
