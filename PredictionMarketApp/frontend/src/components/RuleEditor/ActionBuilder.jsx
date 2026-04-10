import React, { useState, useEffect } from 'react';
import useBotAvailableVariables from '../../hooks/useBotAvailableVariables';

const selectClass =
  'input-field text-xs font-mono py-0.5 min-w-0 cursor-pointer bg-terminal-panel text-terminal-amber';

const toggleBtn = (active) =>
  `px-1.5 py-0.5 text-[9px] font-mono uppercase border-0 cursor-pointer transition-colors ${
    active
      ? 'bg-terminal-amber-faint text-terminal-amber-bright'
      : 'bg-terminal-panel text-terminal-amber-dim hover:text-terminal-amber'
  }`;

/**
 * A numeric input that can be toggled to a variable picker.
 * Stores literal in params[paramKey] and variable name in params[varKey].
 */
function VarOrNumeric({
  params,
  paramKey,
  varKey,
  fallback = 1,
  isFloat = false,
  min,
  step,
  inputClass = 'input-field w-16 text-xs py-0.5',
  ariaLabel,
  groups,
  loading,
  onUpdateParams,
}) {
  const varValue = String(params[varKey] || '').trim();
  const isVarMode = varValue !== '' || params[`${paramKey}_mode`] === 'variable';

  // Local display state to allow clearing mid-type
  const [display, setDisplay] = useState(String(params[paramKey] ?? fallback));
  useEffect(() => {
    setDisplay(String(params[paramKey] ?? fallback));
  }, [params[paramKey]]); // eslint-disable-line react-hooks/exhaustive-deps

  const parse = (s) => (isFloat ? parseFloat(s) : parseInt(s, 10));

  const switchToVar = () => {
    onUpdateParams({ [`${paramKey}_mode`]: 'variable', [varKey]: '' });
  };
  const switchToLiteral = () => {
    onUpdateParams({ [`${paramKey}_mode`]: 'literal', [varKey]: '' });
  };

  return (
    <div className="flex items-center gap-1">
      <div
        className="flex border border-terminal-border-dim rounded-sm overflow-hidden shrink-0"
        role="group"
        aria-label={`${ariaLabel || paramKey} type`}
      >
        <button type="button" className={`${toggleBtn(!isVarMode)} rounded-l-sm`} onClick={switchToLiteral}>
          value
        </button>
        <button type="button" className={`${toggleBtn(isVarMode)} rounded-r-sm border-l border-terminal-border-dim`} onClick={switchToVar}>
          var
        </button>
      </div>
      {isVarMode ? (
        varValue ? (
          <div className="flex items-center gap-1 min-w-0 max-w-[180px]">
            <span className="text-terminal-amber-bright truncate text-xs font-mono" title={varValue}>
              {varValue}
            </span>
            <button
              type="button"
              className="shrink-0 text-[9px] font-mono text-terminal-amber-dim hover:text-terminal-amber border border-terminal-border-dim px-1 py-0"
              onClick={() => onUpdateParams({ [varKey]: '' })}
              title="Pick a different variable"
            >
              ×
            </button>
          </div>
        ) : (
          <select
            className={`${selectClass} min-w-[7rem] max-w-[180px]`}
            value=""
            disabled={loading}
            onChange={(e) => onUpdateParams({ [varKey]: e.target.value })}
            aria-label={`${ariaLabel || paramKey} variable`}
          >
            <option value="">{loading ? 'Loading…' : 'choose var'}</option>
            {groups.map((g) => (
              <optgroup key={`${paramKey}-${g.label}`} label={g.label || 'Variables'}>
                {(g.vars || []).map((v) => (
                  <option
                    key={`${paramKey}-${g.label}-${v.name}`}
                    value={v.name}
                    title={[v.ticker, v.desc].filter(Boolean).join(' | ') || v.name}
                  >
                    {v.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        )
      ) : (
        <input
          type="number"
          className={inputClass}
          min={min}
          step={step}
          aria-label={ariaLabel}
          value={display}
          onChange={(e) => {
            setDisplay(e.target.value);
            const n = parse(e.target.value);
            if (!isNaN(n)) onUpdateParams({ [paramKey]: n });
          }}
          onBlur={() => {
            const n = parse(display);
            if (isNaN(n) || display === '') {
              setDisplay(String(fallback));
              onUpdateParams({ [paramKey]: fallback });
            }
          }}
        />
      )}
    </div>
  );
}

export default function ActionBuilder({ rule, onUpdate }) {
  const { groups, loading } = useBotAvailableVariables();
  const actionType = rule.action_type || '';
  let params = {};
  try { params = JSON.parse(rule.action_params || '{}'); } catch { params = {}; }

  const updateParams = (newParams) => {
    onUpdate({ ...rule, action_params: JSON.stringify({ ...params, ...newParams }) });
  };

  const varProps = { groups, loading, onUpdateParams: updateParams };

  switch (actionType) {
    case 'BUY':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-green-text font-semibold">BUY</span>
          <VarOrNumeric params={params} paramKey="contracts" varKey="contracts_var" fallback={1} min={1} ariaLabel="Contract count" {...varProps} />
          <span className="text-terminal-amber-dim">contracts at market</span>
        </div>
      );

    case 'SELL':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-red-text font-semibold">SELL</span>
          <VarOrNumeric params={params} paramKey="contracts" varKey="contracts_var" fallback={1} min={1} ariaLabel="Contract count" {...varProps} />
          <span className="text-terminal-amber-dim">contracts at market</span>
        </div>
      );

    case 'LIMIT':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-amber font-semibold">LIMIT</span>
          <select
            value={params.side || 'yes'}
            onChange={(e) => updateParams({ side: e.target.value })}
            className="input-field text-xs py-0.5"
          >
            <option value="yes">BUY</option>
            <option value="no">SELL</option>
          </select>
          <VarOrNumeric params={params} paramKey="contracts" varKey="contracts_var" fallback={1} min={1} ariaLabel="Contract count" {...varProps} />
          <span className="text-terminal-amber-dim">at</span>
          <VarOrNumeric params={params} paramKey="price" varKey="price_var" fallback={50} isFloat step={1} inputClass="input-field w-14 text-xs py-0.5" ariaLabel="Limit price" {...varProps} />
          <span className="text-terminal-amber-dim">cents</span>
        </div>
      );

    case 'CLOSE':
      return <span className="text-xs text-terminal-amber font-mono font-semibold">CLOSE POSITION</span>;

    case 'SET_VAR':
      return (
        <div className="flex items-center gap-1 text-xs font-mono">
          <span className="text-terminal-amber font-semibold">SET</span>
          <input type="text" value={params.var_name || ''} onChange={(e) => updateParams({ var_name: e.target.value })} className="input-field w-24 text-xs py-0.5" placeholder="var name" />
          <span className="text-terminal-amber-dim">=</span>
          <input type="text" value={params.value || ''} onChange={(e) => updateParams({ value: e.target.value })} className="input-field w-20 text-xs py-0.5" placeholder="value" />
        </div>
      );

    case 'STOP':
      return <span className="text-xs text-terminal-red-text font-mono font-semibold">STOP BOT</span>;

    case 'LOG':
      return (
        <div className="flex items-center gap-1 text-xs font-mono">
          <span className="text-terminal-amber-dim font-semibold">LOG</span>
          <input type="text" value={params.message || ''} onChange={(e) => updateParams({ message: e.target.value })} className="input-field flex-1 text-xs py-0.5" placeholder="Log message..." />
        </div>
      );

    case 'ALERT':
      return (
        <div className="flex items-center gap-1 text-xs font-mono">
          <span className="text-terminal-amber font-semibold">ALERT</span>
          <input type="text" value={params.message || ''} onChange={(e) => updateParams({ message: e.target.value })} className="input-field flex-1 text-xs py-0.5" placeholder="Alert text..." />
        </div>
      );

    case 'GOTO':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-amber font-semibold">GO TO LINE</span>
          <VarOrNumeric params={params} paramKey="line" varKey="line_var" fallback={1} min={1} ariaLabel="Go to line number" {...varProps} />
        </div>
      );

    case 'CONTINUE':
      return <span className="text-xs text-terminal-green-text font-mono font-semibold">CONTINUE</span>;

    default:
      return (
        <select value={actionType} onChange={(e) => onUpdate({ ...rule, action_type: e.target.value })} className="input-field text-xs py-0.5">
          <option value="">Select action...</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="LIMIT">LIMIT</option>
          <option value="CLOSE">CLOSE</option>
          <option value="SET_VAR">SET VAR</option>
          <option value="STOP">STOP</option>
          <option value="LOG">LOG</option>
          <option value="ALERT">ALERT</option>
          <option value="GOTO">GOTO</option>
          <option value="CONTINUE">CONTINUE</option>
        </select>
      );
  }
}
