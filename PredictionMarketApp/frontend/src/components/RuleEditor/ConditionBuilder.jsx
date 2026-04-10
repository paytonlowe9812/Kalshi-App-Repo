import React, { useState } from 'react';
import OperatorPicker, { getOperatorDisplay } from './OperatorPicker';
import useBotAvailableVariables from '../../hooks/useBotAvailableVariables';

function numericish(s) {
  if (s == null || s === '') return false;
  const n = Number(s);
  return !Number.isNaN(n) && Number.isFinite(n);
}

/** Variable mode: empty, known name, or unknown token while still loading. Value mode: non-empty literal number not a variable name. */
function isVariableMode(operand, allNames, loading) {
  if (operand == null || operand === '') return true;
  if (allNames.includes(operand)) return true;
  if (loading && allNames.length === 0 && !numericish(operand)) return true;
  return false;
}

function OperandSide({ label, operandKey, rule, onUpdate, groups, loading, allNames }) {
  const value = rule[operandKey];
  const variableMode = isVariableMode(value, allNames, loading);

  const setVariableMode = () => {
    onUpdate({ ...rule, [operandKey]: null });
  };

  const setValueMode = () => {
    const v = value;
    const keep =
      v != null &&
      v !== '' &&
      !allNames.includes(v) &&
      numericish(v)
        ? v
        : '0';
    onUpdate({ ...rule, [operandKey]: keep });
  };

  const toggleBtn = (active) =>
    `px-1.5 py-0.5 text-[9px] font-mono uppercase border-0 cursor-pointer transition-colors ${
      active
        ? 'bg-terminal-amber-faint text-terminal-amber-bright'
        : 'bg-terminal-panel text-terminal-amber-dim hover:text-terminal-amber'
    }`;

  const selectClass =
    'input-field text-xs font-mono py-1 min-w-0 flex-1 cursor-pointer bg-terminal-panel text-terminal-amber';

  return (
    <div className="flex items-center gap-1 min-w-0 flex-1 basis-[112px] md:basis-auto">
      <div
        className="flex border border-terminal-border-dim rounded-sm overflow-hidden shrink-0"
        role="group"
        aria-label={`${label} operand type`}
      >
        <button
          type="button"
          className={`${toggleBtn(variableMode)} rounded-l-sm`}
          onClick={setVariableMode}
        >
          variable
        </button>
        <button
          type="button"
          className={`${toggleBtn(!variableMode)} rounded-r-sm border-l border-terminal-border-dim`}
          onClick={setValueMode}
        >
          value
        </button>
      </div>
      {variableMode ? (
        <select
          className={selectClass}
          value={value || ''}
          disabled={loading}
          onChange={(e) => onUpdate({ ...rule, [operandKey]: e.target.value || null })}
          aria-label={`${label} variable`}
        >
          <option value="">{loading ? 'Loading…' : 'choose variable'}</option>
          {groups.map((g) => (
            <optgroup key={`${label}-${g.label || 'vars'}`} label={g.label || 'Variables'}>
              {(g.vars || []).map((v) => (
                <option
                  key={`${label}-${g.label}-${v.name}-${v.ticker || ''}`}
                  value={v.name}
                  title={[v.ticker, v.desc].filter(Boolean).join(' | ') || v.name}
                >
                  {v.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      ) : (
        <input
          type="number"
          step="any"
          className={`${selectClass} w-20 md:flex-1 md:min-w-[5rem] md:max-w-[160px]`}
          value={value ?? ''}
          onChange={(e) => onUpdate({ ...rule, [operandKey]: e.target.value })}
          aria-label={`${label} numeric value`}
        />
      )}
    </div>
  );
}

export default function ConditionBuilder({ rule, onUpdate }) {
  const { groups, loading, allNames } = useBotAvailableVariables();
  const [showOpPicker, setShowOpPicker] = useState(false);

  return (
    <div className="flex items-center gap-1 flex-wrap md:flex-nowrap">
      <OperandSide
        label="Left"
        operandKey="left_operand"
        rule={rule}
        onUpdate={onUpdate}
        groups={groups}
        loading={loading}
        allNames={allNames}
      />

      <div className="relative flex-shrink-0">
        <button
          type="button"
          onClick={() => setShowOpPicker(!showOpPicker)}
          className="px-1.5 py-0.5 border border-terminal-border-dim bg-terminal-panel hover:bg-terminal-amber-faint text-[11px] font-mono text-terminal-amber-bright min-w-[24px]"
        >
          {getOperatorDisplay(rule.operator)}
        </button>
        {showOpPicker && (
          <OperatorPicker
            value={rule.operator}
            onChange={(v) => onUpdate({ ...rule, operator: v })}
            onClose={() => setShowOpPicker(false)}
          />
        )}
      </div>

      <OperandSide
        label="Right"
        operandKey="right_operand"
        rule={rule}
        onUpdate={onUpdate}
        groups={groups}
        loading={loading}
        allNames={allNames}
      />
    </div>
  );
}
