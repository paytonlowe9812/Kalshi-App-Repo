import React, { useState, useCallback, useRef, useEffect } from 'react';
import useAppStore from '../../store/useAppStore';
import VariableSliders from './VariableSliders';
import PlaybackControls from './PlaybackControls';
import SimResultPanel from './SimResultPanel';

const CORE_DEFAULTS = {
  YES_price: 50,
  NO_price: 50,
  PositionSize: 0,
  RestingLimitCount: 0,
  OldestRestingLimitAgeSec: 0,
};

function buildSimVariablesFromGroups(groups) {
  const next = { ...CORE_DEFAULTS };
  for (const g of groups || []) {
    const gl = g.label || '';
    for (const v of g.vars || []) {
      const n = v.name;
      if (Object.prototype.hasOwnProperty.call(next, n)) continue;
      if (gl.includes('USER')) {
        const m = (v.desc || '').match(/=\s*([-\d.]+)/);
        next[n] = m ? parseFloat(m[1]) || 0 : 0;
      } else {
        next[n] = 50;
      }
    }
  }
  return next;
}

export default function SimulatorPanel({ open, onClose }) {
  const { activeBotId } = useAppStore();
  const [variables, setVariables] = useState({ ...CORE_DEFAULTS });
  const variablesSnapshotRef = useRef(null);
  const [steps, setSteps] = useState([]);
  const [finalAction, setFinalAction] = useState(null);
  const [variablesAfter, setVariablesAfter] = useState({});
  const [speed, setSpeed] = useState('fast');
  const [running, setRunning] = useState(false);
  const [visibleSteps, setVisibleSteps] = useState([]);
  const intervalRef = useRef(null);

  const runSim = useCallback(async () => {
    if (!activeBotId) return;
    try { const res = await fetch('/api/simulator/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bot_id: activeBotId, variable_overrides: variables }) }); const data = await res.json(); setSteps(data.steps || []); setFinalAction(data.final_action); setVariablesAfter(data.variables_after || {}); return data.steps || []; } catch { return []; }
  }, [activeBotId, variables]);

  const handleRun = async () => { const allSteps = await runSim(); if (speed === 'fast') { setVisibleSteps(allSteps); return; } setRunning(true); setVisibleSteps([]); const delay = speed === 'slow' ? 1000 : speed === 'medium' ? 333 : 100; let i = 0; intervalRef.current = setInterval(() => { if (i >= allSteps.length) { clearInterval(intervalRef.current); setRunning(false); return; } setVisibleSteps((prev) => [...prev, allSteps[i]]); i++; }, delay); };
  const handleStep = async () => { if (steps.length === 0) await runSim(); setVisibleSteps((prev) => { const nextIdx = prev.length; if (nextIdx < steps.length) return [...prev, steps[nextIdx]]; return prev; }); };
  const handleStop = () => { if (intervalRef.current) clearInterval(intervalRef.current); setRunning(false); };
  const handleVarChange = (name, value) => { setVariables((prev) => ({ ...prev, [name]: value })); };
  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current); }, []);

  useEffect(() => {
    if (!open || !activeBotId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/bots/${activeBotId}/available-variables`);
        const data = await res.json();
        const next = buildSimVariablesFromGroups(data.groups);
        if (!cancelled) {
          variablesSnapshotRef.current = next;
          setVariables({ ...next });
        }
      } catch {
        if (!cancelled) {
          variablesSnapshotRef.current = { ...CORE_DEFAULTS };
          setVariables({ ...CORE_DEFAULTS });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, activeBotId]);

  useEffect(() => { if (speed !== 'manual' && activeBotId) { const d = setTimeout(() => runSim(), 300); return () => clearTimeout(d); } }, [variables]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-30 md:static md:z-auto md:w-96 border-l-0 md:border-l border-terminal-border-dim bg-terminal-bg md:bg-terminal-surface flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-terminal-border-dim">
        <h2 className="panel-header">SIMULATOR</h2>
        <button onClick={onClose} className="text-terminal-amber-dim active:text-terminal-amber hover:text-terminal-amber w-8 h-8 flex items-center justify-center font-mono text-xs">[X]</button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 pb-20 md:pb-4">
        <VariableSliders
          variables={variables}
          onChange={handleVarChange}
          onReset={() =>
            setVariables({ ...(variablesSnapshotRef.current || CORE_DEFAULTS) })
          }
        />
        <PlaybackControls onRun={handleRun} onStep={handleStep} speed={speed} onSpeedChange={setSpeed} running={running} onStop={handleStop} />
        <SimResultPanel steps={visibleSteps.length > 0 ? visibleSteps : steps} finalAction={finalAction} variablesAfter={variablesAfter} />
      </div>
    </div>
  );
}
