import React from 'react';

export default function ActionBuilder({ rule, onUpdate }) {
  const actionType = rule.action_type || '';
  let params = {};
  try { params = JSON.parse(rule.action_params || '{}'); } catch { params = {}; }
  const updateParams = (newParams) => { onUpdate({ ...rule, action_params: JSON.stringify({ ...params, ...newParams }) }); };

  switch (actionType) {
    case 'BUY':
      return (<div className="flex items-center gap-1 text-xs font-mono"><span className="text-terminal-green-text font-semibold">BUY</span><input type="number" value={params.contracts || 1} onChange={(e) => updateParams({ contracts: parseInt(e.target.value) || 1 })} className="input-field w-16 text-xs py-0.5" min={1} /><span className="text-terminal-amber-dim">contracts at market</span></div>);
    case 'SELL':
      return (<div className="flex items-center gap-1 text-xs font-mono"><span className="text-terminal-red-text font-semibold">SELL</span><input type="number" value={params.contracts || 1} onChange={(e) => updateParams({ contracts: parseInt(e.target.value) || 1 })} className="input-field w-16 text-xs py-0.5" min={1} /><span className="text-terminal-amber-dim">contracts at market</span></div>);
    case 'LIMIT':
      return (<div className="flex items-center gap-1 text-xs font-mono"><span className="text-terminal-amber font-semibold">LIMIT</span><select value={params.side || 'yes'} onChange={(e) => updateParams({ side: e.target.value })} className="input-field text-xs py-0.5"><option value="yes">BUY</option><option value="no">SELL</option></select><input type="number" value={params.contracts || 1} onChange={(e) => updateParams({ contracts: parseInt(e.target.value) || 1 })} className="input-field w-16 text-xs py-0.5" min={1} /><span className="text-terminal-amber-dim">at</span><input type="number" value={params.price || 50} onChange={(e) => updateParams({ price: parseFloat(e.target.value) || 50 })} className="input-field w-16 text-xs py-0.5" step={1} /><span className="text-terminal-amber-dim">cents</span></div>);
    case 'CLOSE':
      return <span className="text-xs text-terminal-amber font-mono font-semibold">CLOSE POSITION</span>;
    case 'SET_VAR':
      return (<div className="flex items-center gap-1 text-xs font-mono"><span className="text-terminal-amber font-semibold">SET</span><input type="text" value={params.var_name || ''} onChange={(e) => updateParams({ var_name: e.target.value })} className="input-field w-24 text-xs py-0.5" placeholder="var name" /><span className="text-terminal-amber-dim">=</span><input type="text" value={params.value || ''} onChange={(e) => updateParams({ value: e.target.value })} className="input-field w-20 text-xs py-0.5" placeholder="value" /></div>);
    case 'STOP':
      return <span className="text-xs text-terminal-red-text font-mono font-semibold">STOP BOT</span>;
    case 'LOG':
      return (<div className="flex items-center gap-1 text-xs font-mono"><span className="text-terminal-amber-dim font-semibold">LOG</span><input type="text" value={params.message || ''} onChange={(e) => updateParams({ message: e.target.value })} className="input-field flex-1 text-xs py-0.5" placeholder="Log message..." /></div>);
    case 'ALERT':
      return (<div className="flex items-center gap-1 text-xs font-mono"><span className="text-terminal-amber font-semibold">ALERT</span><input type="text" value={params.message || ''} onChange={(e) => updateParams({ message: e.target.value })} className="input-field flex-1 text-xs py-0.5" placeholder="Alert text..." /></div>);
    case 'GOTO':
      return (<div className="flex items-center gap-1 text-xs font-mono"><span className="text-terminal-amber font-semibold">GO TO LINE</span><input type="number" value={params.line || 1} onChange={(e) => updateParams({ line: parseInt(e.target.value) || 1 })} className="input-field w-16 text-xs py-0.5" min={1} /></div>);
    case 'CONTINUE':
      return <span className="text-xs text-terminal-green-text font-mono font-semibold">CONTINUE</span>;
    default:
      return (<select value={actionType} onChange={(e) => onUpdate({ ...rule, action_type: e.target.value })} className="input-field text-xs py-0.5"><option value="">Select action...</option><option value="BUY">BUY</option><option value="SELL">SELL</option><option value="LIMIT">LIMIT</option><option value="CLOSE">CLOSE</option><option value="SET_VAR">SET VAR</option><option value="STOP">STOP</option><option value="LOG">LOG</option><option value="ALERT">ALERT</option><option value="GOTO">GOTO</option><option value="CONTINUE">CONTINUE</option></select>);
  }
}
