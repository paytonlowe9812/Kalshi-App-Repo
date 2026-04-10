import React from 'react';

const RESULT_ICONS = {
  hit: { icon: 'V', color: 'text-terminal-green-text' },
  skipped: { icon: '-', color: 'text-terminal-amber-dim' },
  branched: { icon: '>', color: 'text-terminal-amber' },
  stopped: { icon: 'X', color: 'text-terminal-red-text' },
};

export default function SimResultPanel({ steps, finalAction, variablesAfter }) {
  if (!steps || steps.length === 0) {
    return <div className="text-xs text-terminal-amber-dim font-mono text-center py-4">RUN OR STEP THROUGH THE SIMULATION TO SEE RESULTS</div>;
  }
  return (
    <div className="space-y-3">
      <h3 className="panel-header">RESULTS</h3>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {steps.map((step, i) => {
          const display = RESULT_ICONS[step.result] || RESULT_ICONS.skipped;
          return (
            <div key={i} className="flex items-start gap-2 text-xs py-0.5 font-mono">
              <span className={`w-4 ${display.color}`}>{display.icon}</span>
              <span className="text-terminal-amber-dim w-6">L{step.line_number}</span>
              <span className="text-terminal-amber flex-1">{step.reason}</span>
              {step.action_fired && <span className="text-terminal-green-text">{step.action_fired.type}</span>}
            </div>
          );
        })}
      </div>
      <div className="border-t border-terminal-border-dim pt-2">
        {finalAction ? (
          <div className="text-xs font-mono"><span className="text-terminal-amber-dim">Action fired: </span><span className="text-terminal-green-text font-semibold">{finalAction.type} {finalAction.contracts ? `${finalAction.contracts} contracts` : ''}</span></div>
        ) : (<div className="text-xs text-terminal-amber-dim font-mono">NO ACTION FIRED</div>)}
      </div>
      {variablesAfter && Object.keys(variablesAfter).length > 0 && (
        <div className="border-t border-terminal-border-dim pt-2">
          <h4 className="text-[10px] text-terminal-amber-dim uppercase font-mono mb-1">VARIABLES AFTER</h4>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {Object.entries(variablesAfter).slice(0, 10).map(([k, v]) => (
              <div key={k} className="flex justify-between text-[10px] font-mono"><span className="text-terminal-amber-dim truncate">{k}</span><span className="text-terminal-amber">{v}</span></div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
