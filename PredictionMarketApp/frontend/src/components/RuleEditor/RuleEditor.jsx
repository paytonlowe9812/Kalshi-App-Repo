import React, { useEffect, useState, useCallback, useRef } from 'react';
import useAppStore from '../../store/useAppStore';
import RuleToolbar from './RuleToolbar';
import RuleLine from './RuleLine';
import SnapshotSidebar from './SnapshotSidebar';
import MarketPickerTree from './MarketPickerTree';

function inferSeriesFromMarket(ticker) {
  if (!ticker || typeof ticker !== 'string') return '';
  const part = ticker.split('-')[0];
  return part || '';
}

export default function RuleEditor({ onOpenSimulator }) {
  const { activeBotId, bulkEditIds } = useAppStore();
  const isBulk = bulkEditIds.length > 1;
  const [bulkSaving, setBulkSaving] = useState(false);
  const [bulkSaved, setBulkSaved] = useState(false);
  const [bot, setBot] = useState(null);
  const [rules, setRules] = useState([]);
  const [editingName, setEditingName] = useState(false);
  const [botName, setBotName] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [simResults, setSimResults] = useState({});
  const saveTimeout = useRef(null);

  const fetchBot = useCallback(async () => {
    if (!activeBotId) return;
    const res = await fetch(`/api/bots/${activeBotId}`);
    const data = await res.json();
    setBot(data);
    setBotName(data.name);
    setRules(
      (data.rules || []).map((r) => ({
        ...r, line_number: r.line_number, line_type: r.line_type,
        left_operand: r.left_operand, operator: r.operator, right_operand: r.right_operand,
        action_type: r.action_type, action_params: r.action_params,
        group_id: r.group_id, group_logic: r.group_logic, exec_count: r.exec_count || 0,
      })),
    );
  }, [activeBotId]);

  useEffect(() => { fetchBot(); }, [fetchBot]);

  const buildPayload = (updatedRules) => updatedRules.map((r, i) => ({
    line_number: i + 1, line_type: r.line_type,
    left_operand: r.left_operand || null, operator: r.operator || null,
    right_operand: r.right_operand || null, action_type: r.action_type || null,
    action_params: r.action_params || null, group_id: r.group_id || null,
    group_logic: r.group_logic || null,
  }));

  // Auto-save always goes to the active bot only (single-bot or bulk template).
  const saveRules = useCallback((updatedRules) => {
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    saveTimeout.current = setTimeout(async () => {
      const { activeBotId: bid } = useAppStore.getState();
      if (!bid) return;
      await fetch(`/api/bots/${bid}/rules`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules: buildPayload(updatedRules) }),
      });
    }, 800);
  }, []);

  // Explicit bulk save — writes the current editor rules to every selected bot sequentially.
  const saveBulkAll = async () => {
    const { bulkEditIds: ids, activeBotId: bid } = useAppStore.getState();
    const targets = ids.length > 1 ? ids : [bid];
    const payload = buildPayload(rules);
    setBulkSaving(true);
    setBulkSaved(false);
    for (const id of targets) {
      await fetch(`/api/bots/${id}/rules`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules: payload }),
      });
    }
    setBulkSaving(false);
    setBulkSaved(true);
    setTimeout(() => setBulkSaved(false), 2000);
  };

  const updateRule = (index, updatedRule) => { const n = [...rules]; n[index] = updatedRule; setRules(n); saveRules(n); };
  const addLine = (lineType) => {
    const defaultParams =
      lineType === 'GOTO' ? '{"line":1}' :
      lineType === 'PAUSE' ? '{"ms":500}' :
      lineType === 'CANCEL_STALE' ? '{"max_age_ms":60000}' :
      lineType === 'NOOP' ? '{}' :
      null;
    const newRule = { line_number: rules.length + 1, line_type: lineType,
      left_operand: null, operator: ['IF', 'AND', 'OR'].includes(lineType) ? 'gt' : null,
      right_operand: null, action_type: ['THEN', 'ELSE'].includes(lineType) ? '' : lineType === 'GOTO' ? 'GOTO' : lineType,
      action_params: defaultParams, group_id: null, group_logic: null, exec_count: 0 };
    const n = [...rules, newRule]; setRules(n); saveRules(n);
  };
  const moveUp = (i) => { if (i === 0) return; const n = [...rules]; [n[i - 1], n[i]] = [n[i], n[i - 1]]; n.forEach((r, j) => r.line_number = j + 1); setRules(n); saveRules(n); };
  const moveDown = (i) => { if (i >= rules.length - 1) return; const n = [...rules]; [n[i], n[i + 1]] = [n[i + 1], n[i]]; n.forEach((r, j) => r.line_number = j + 1); setRules(n); saveRules(n); };
  const deleteLine = (i) => { const n = rules.filter((_, j) => j !== i); n.forEach((r, j) => r.line_number = j + 1); setRules(n); saveRules(n); };

  const saveBotName = async () => { setEditingName(false); if (botName !== bot.name) { await fetch(`/api/bots/${activeBotId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: botName }) }); } };
  const assignMarket = async (ticker) => { await fetch(`/api/bots/${activeBotId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ market_ticker: ticker }) }); fetchBot(); };
  const clearMarket = async () => { await fetch(`/api/bots/${activeBotId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ market_ticker: '', series_ticker: '', auto_roll: false }) }); fetchBot(); };
  const effectiveSeries =
    (bot?.series_ticker && String(bot.series_ticker).trim()) || inferSeriesFromMarket(bot?.market_ticker || '');

  const contractSide = (bot?.contract_side || 'yes').toLowerCase() === 'no' ? 'no' : 'yes';

  const setContractSide = async (side) => {
    const s = side === 'no' ? 'no' : 'yes';
    const targets = bulkEditIds.length > 1 ? bulkEditIds : [activeBotId];
    await Promise.all(targets.map((id) =>
      fetch(`/api/bots/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contract_side: s }),
      })
    ));
    fetchBot();
  };

  const toggleAutoRoll = async () => {
    const targets = bulkEditIds.length > 1 ? bulkEditIds : [activeBotId];
    await Promise.all(targets.map((id) =>
      fetch(`/api/bots/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          auto_roll: !bot?.auto_roll,
          ...(effectiveSeries ? { series_ticker: effectiveSeries } : {}),
        }),
      })
    ));
    fetchBot();
  };

  const sideToggleBtn = (active) =>
    `px-1.5 py-0.5 text-[9px] font-mono uppercase border-0 cursor-pointer transition-colors ${
      active
        ? 'bg-terminal-amber-faint text-terminal-amber-bright'
        : 'bg-terminal-panel text-terminal-amber-dim hover:text-terminal-amber'
    }`;

  if (!activeBotId) {
    return <div className="flex items-center justify-center h-full text-terminal-amber-dim text-xs font-mono px-4 text-center">SELECT A BOT FROM THE BOTS TAB TO START EDITING.</div>;
  }

  return (
    <div className="h-full flex">
      <div className="flex-1 flex flex-col min-w-0">
        {isBulk && (
          <div className="border-b border-terminal-amber bg-terminal-amber-faint">
            <div className="max-w-5xl mx-auto px-4 md:px-8 lg:px-16 py-1.5 flex items-center gap-2 text-terminal-amber-bright text-[10px] font-mono">
              <div className="flex-1 min-w-0">
                <span className="font-bold">BULK EDIT</span>
                <span className="text-terminal-amber mx-1">—</span>
                <span>{bulkEditIds.length} bots selected. Edit here, then save to all.</span>
              </div>
              <button
                onClick={saveBulkAll}
                disabled={bulkSaving}
                className="shrink-0 px-2.5 py-1 border border-terminal-amber text-terminal-amber-bright hover:bg-terminal-amber hover:text-terminal-bg font-mono text-[10px] font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {bulkSaving ? 'SAVING...' : bulkSaved ? 'SAVED ✓' : `SAVE TO ALL ${bulkEditIds.length}`}
              </button>
            </div>
          </div>
        )}
        <div className="border-b border-terminal-border-dim">
          <div className="max-w-5xl mx-auto px-4 md:px-8 lg:px-16 flex flex-col md:flex-row md:items-center gap-1.5 md:gap-2 py-1.5 md:py-2">
          <div className="flex items-center gap-1 min-w-0 flex-wrap">
            {editingName ? (
              <input type="text" value={botName} onChange={(e) => setBotName(e.target.value)} onBlur={saveBotName} onKeyDown={(e) => e.key === 'Enter' && saveBotName()} className="input-field text-xs font-semibold flex-1 min-w-[120px]" autoFocus />
            ) : (
              <h2 className="text-xs font-mono font-semibold text-terminal-amber cursor-pointer hover:text-terminal-amber-bright active:text-terminal-amber-bright truncate text-glow-sm max-w-[200px] md:max-w-none" onClick={() => setEditingName(true)}>
                {botName || 'UNTITLED BOT'}
              </h2>
            )}
            <div
              className="flex border border-terminal-border-dim rounded-sm overflow-hidden shrink-0"
              role="group"
              aria-label="Contract side for BUY and SELL actions"
            >
              <button
                type="button"
                className={`${sideToggleBtn(contractSide === 'yes')} rounded-l-sm`}
                onClick={() => setContractSide('yes')}
                title="BUY buys YES contracts; SELL sells YES contracts"
              >
                YES
              </button>
              <button
                type="button"
                className={`${sideToggleBtn(contractSide === 'no')} rounded-r-sm border-l border-terminal-border-dim`}
                onClick={() => setContractSide('no')}
                title="BUY buys NO contracts; SELL sells NO contracts"
              >
                NO
              </button>
            </div>
          </div>
          <div className="flex items-center gap-1 md:ml-auto flex-wrap">
            {bot?.market_ticker ? (
              <>
                <div className="flex items-center gap-1 border border-terminal-border-dim bg-terminal-panel px-1.5 py-1 text-[11px] font-mono">
                  <span className="text-terminal-amber truncate max-w-[120px] md:max-w-[140px]">{bot.market_ticker}</span>
                  <button type="button" onClick={clearMarket} className="text-terminal-amber-dim active:text-terminal-red-text hover:text-terminal-red-text p-0.5">[X]</button>
                </div>
                {effectiveSeries && (
                  <button
                    type="button"
                    onClick={toggleAutoRoll}
                    className={`flex items-center gap-1 border px-1.5 py-1 text-[11px] font-mono cursor-pointer ${
                      bot?.auto_roll
                        ? 'border-terminal-green/50 bg-terminal-green/10 text-terminal-green-text'
                        : 'border-terminal-border-dim bg-terminal-panel text-terminal-amber-dim hover:text-terminal-amber'
                    }`}
                    title={
                      bot?.auto_roll
                        ? `Auto-roll is on. When this contract expires or settles, the bot moves to the next open contract in series ${effectiveSeries}.`
                        : 'Turn on to auto-roll: when this contract expires or settles, continue on the next open contract in the same series (e.g. next BTC 15m window).'
                    }
                  >
                    <span>{bot?.auto_roll ? '[*]' : '[ ]'}</span>
                    <span className="text-left leading-tight">
                      <span className="sm:hidden">AUTO NEXT</span>
                      <span className="hidden sm:inline lg:hidden">AUTO-ROLL</span>
                      <span className="hidden lg:inline">AUTO-ROLL TO NEXT IN SERIES</span>
                    </span>
                    {bot?.auto_roll && <span className="text-[10px] opacity-70 shrink-0">{effectiveSeries}</span>}
                  </button>
                )}
              </>
            ) : (
              <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 flex-1 md:flex-initial min-w-0 w-full md:w-auto">
                <div className="w-full sm:max-w-[180px] md:max-w-[200px] shrink-0" onClick={(e) => e.stopPropagation()}>
                  <MarketPickerTree onPickTicker={assignMarket} />
                </div>
                <span
                  className="text-[9px] font-mono text-terminal-amber-muted shrink-0 border border-dashed border-terminal-border-dim/50 px-1.5 py-1 leading-tight max-w-full sm:max-w-[220px]"
                  title="Pick a market from your saved lists. Series for auto-roll is inferred from the ticker."
                >
                  ASSIGN MARKET FROM SAVED LISTS
                </span>
              </div>
            )}
          </div>
          </div>
        </div>
        <RuleToolbar onAddLine={addLine} onSimulate={onOpenSimulator} onOpenHistory={() => setHistoryOpen(true)} />
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-4 md:px-8 lg:px-16 py-1">
            {rules.length === 0 && <div className="flex items-center justify-center h-32 text-xs text-terminal-amber-dim font-mono px-4 text-center">ADD RULE LINES USING THE TOOLBAR ABOVE</div>}
            {rules.map((rule, i) => (
              <RuleLine key={`${rule.line_type}-${i}`} rule={{ ...rule, line_number: i + 1 }} index={i} onUpdate={(u) => updateRule(i, u)} onMoveUp={() => moveUp(i)} onMoveDown={() => moveDown(i)} onDelete={() => deleteLine(i)} simResult={simResults[i + 1]} isFirst={i === 0} isLast={i === rules.length - 1} />
            ))}
          </div>
        </div>
      </div>
      <SnapshotSidebar botId={activeBotId} onRestore={fetchBot} open={historyOpen} onClose={() => setHistoryOpen(false)} />
    </div>
  );
}
