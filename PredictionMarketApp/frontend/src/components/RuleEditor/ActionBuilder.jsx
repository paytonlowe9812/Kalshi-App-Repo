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
  /** Short label before value/var (e.g. Qty, Price) */
  fieldLabel,
  /** When set, var mode shows a signed cents delta applied after resolving the variable (e.g. LastTraded - 5). */
  offsetKey,
  offsetAriaLabel,
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
    const patch = { [`${paramKey}_mode`]: 'literal', [varKey]: '' };
    if (offsetKey) patch[offsetKey] = 0;
    onUpdateParams(patch);
  };

  return (
    <div className="flex items-center gap-1 flex-wrap sm:flex-nowrap">
      {fieldLabel ? (
        <span
          className="text-[9px] font-mono uppercase tracking-wide text-terminal-amber-dim shrink-0 select-none"
          title={ariaLabel || fieldLabel}
        >
          {fieldLabel}
        </span>
      ) : null}
      <div className="flex items-center gap-1 min-w-0">
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
        <div className="flex items-center gap-1 min-w-0 flex-wrap">
          {varValue ? (
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
          )}
          {offsetKey ? (
            <div className="flex items-center gap-0.5 shrink-0" title="Added to the variable value (cents). Use negative to subtract (e.g. -5 under LastTraded).">
              <span className="text-[9px] font-mono text-terminal-amber-dim">+c</span>
              <input
                type="number"
                step={1}
                className="input-field w-11 text-[11px] font-mono py-0.5 px-1"
                value={params[offsetKey] === 0 || params[offsetKey] == null ? '' : params[offsetKey]}
                onChange={(e) => {
                  const t = e.target.value;
                  if (t === '' || t === '-') {
                    onUpdateParams({ [offsetKey]: 0 });
                    return;
                  }
                  const n = parseInt(t, 10);
                  if (!Number.isNaN(n)) onUpdateParams({ [offsetKey]: n });
                }}
                onBlur={() => {
                  if (params[offsetKey] == null || params[offsetKey] === '' || Number.isNaN(Number(params[offsetKey]))) {
                    onUpdateParams({ [offsetKey]: 0 });
                  }
                }}
                aria-label={offsetAriaLabel || `${ariaLabel || paramKey} cents offset`}
              />
            </div>
          ) : null}
        </div>
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

  const hasExplicitLimitAction =
    typeof params.order_action === 'string' && String(params.order_action).trim() !== '';
  const hasLegacyLimitSide = params.side === 'yes' || params.side === 'no';
  const isLegacyLimitDirection = actionType === 'LIMIT' && hasLegacyLimitSide && !hasExplicitLimitAction;
  const rawLimitAction = String(
    hasExplicitLimitAction
      ? params.order_action
      : (isLegacyLimitDirection ? (params.side === 'no' ? 'sell' : 'buy') : 'buy')
  ).toLowerCase();
  const normalizedLimitAction = rawLimitAction === 'sell' ? 'sell' : 'buy';
  const normalizedLimitSide =
    isLegacyLimitDirection ? '' : (params.side === 'yes' || params.side === 'no' ? params.side : '');

  const updateLimitParams = (patch) => {
    if (isLegacyLimitDirection) {
      updateParams({ order_action: normalizedLimitAction, side: '', ...patch });
      return;
    }
    updateParams(patch);
  };

  const varProps = { groups, loading, onUpdateParams: updateParams };
  const limitVarProps = { groups, loading, onUpdateParams: updateLimitParams };

  switch (actionType) {
    case 'BUY':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-green-text font-semibold">BUY</span>
          <VarOrNumeric params={params} paramKey="contracts" varKey="contracts_var" fallback={1} min={1} fieldLabel="Qty" ariaLabel="Contract count" {...varProps} />
          <span className="text-terminal-amber-dim">contracts at market</span>
        </div>
      );

    case 'SELL':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-red-text font-semibold">SELL</span>
          <VarOrNumeric params={params} paramKey="contracts" varKey="contracts_var" fallback={1} min={1} fieldLabel="Qty" ariaLabel="Contract count" {...varProps} />
          <span className="text-terminal-amber-dim">contracts at market</span>
        </div>
      );

    case 'LIMIT':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-amber font-semibold">LIMIT</span>
          <select
            value={normalizedLimitAction}
            onChange={(e) => updateLimitParams({ order_action: e.target.value })}
            className="input-field text-xs py-0.5"
          >
            <option value="buy">BUY</option>
            <option value="sell">SELL</option>
          </select>
          <span className="text-terminal-amber-dim">side</span>
          <select
            value={normalizedLimitSide}
            onChange={(e) => updateLimitParams({ side: e.target.value })}
            className="input-field text-xs py-0.5"
            title="Contract side override (empty uses bot contract side)"
          >
            <option value="">BOT</option>
            <option value="yes">YES</option>
            <option value="no">NO</option>
          </select>
          <VarOrNumeric params={params} paramKey="contracts" varKey="contracts_var" fallback={1} min={1} fieldLabel="Qty" ariaLabel="Contract count" {...limitVarProps} />
          <span className="text-terminal-amber-dim">at</span>
          <VarOrNumeric
            params={params}
            paramKey="price"
            varKey="price_var"
            fallback={50}
            isFloat
            step={1}
            inputClass="input-field w-14 text-xs py-0.5"
            fieldLabel="Price"
            ariaLabel="Limit price (cents)"
            offsetKey="price_offset"
            offsetAriaLabel="Cents to add after variable (negative subtracts)"
            {...limitVarProps}
          />
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
          <VarOrNumeric params={params} paramKey="line" varKey="line_var" fallback={1} min={1} fieldLabel="Line" ariaLabel="Go to line number" {...varProps} />
        </div>
      );

    case 'NOOP':
      return <span className="text-xs text-terminal-amber-dim font-mono font-semibold">NO OP</span>;

    case 'PAUSE':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-amber font-semibold">PAUSE</span>
          <VarOrNumeric
            params={params}
            paramKey="ms"
            varKey="ms_var"
            fallback={500}
            min={0}
            step={1}
            inputClass="input-field w-20 text-xs py-0.5"
            fieldLabel="Ms"
            ariaLabel="Pause duration in milliseconds"
            {...varProps}
          />
        </div>
      );

    case 'CANCEL_STALE':
      return (
        <div className="flex flex-wrap items-center gap-1 text-xs font-mono">
          <span className="text-terminal-red-text font-semibold">CXL STALE</span>
          <VarOrNumeric
            params={params}
            paramKey="max_age_ms"
            varKey="max_age_ms_var"
            fallback={60000}
            min={0}
            step={1000}
            inputClass="input-field w-24 text-xs py-0.5"
            fieldLabel="Max ms"
            ariaLabel="Cancel resting limits at least this old (ms)"
            {...varProps}
          />
          <span className="text-terminal-amber-dim">rest limit</span>
        </div>
      );

    case 'CONTINUE':
      return <span className="text-xs text-terminal-green-text font-mono font-semibold">CONTINUE</span>;

    default:
      return (
        <select
          value={actionType}
          onChange={(e) => {
            const v = e.target.value;
            let next = { ...rule, action_type: v };
            if (v === 'PAUSE') next = { ...next, action_params: JSON.stringify({ ms: 500 }) };
            if (v === 'NOOP') next = { ...next, action_params: JSON.stringify({}) };
            if (v === 'CANCEL_STALE') next = { ...next, action_params: JSON.stringify({ max_age_ms: 60000 }) };
            onUpdate(next);
          }}
          className="input-field text-xs py-0.5"
        >
          <option value="">Select action...</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="LIMIT">LIMIT</option>
          <option value="CLOSE">CLOSE</option>
          <option value="SET_VAR">SET VAR</option>
          <option value="STOP">STOP</option>
          <option value="LOG">LOG</option>
          <option value="ALERT">ALERT</option>
          <option value="NOOP">NO OP</option>
          <option value="PAUSE">PAUSE</option>
          <option value="CANCEL_STALE">CANCEL STALE LIMITS</option>
          <option value="GOTO">GOTO</option>
          <option value="CONTINUE">CONTINUE</option>
        </select>
      );
  }
}
