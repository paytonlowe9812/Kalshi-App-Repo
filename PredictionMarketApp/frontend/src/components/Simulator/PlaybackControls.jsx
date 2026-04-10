import React from 'react';

export default function PlaybackControls({ onRun, onStep, speed, onSpeedChange, running, onStop }) {
  return (
    <div className="flex items-center gap-2 py-2 flex-wrap">
      {running ? (
        <button onClick={onStop} className="btn-danger text-xs py-2 md:py-1 px-4 md:px-3">STOP</button>
      ) : (
        <>
          <button onClick={onRun} className="btn-primary text-xs py-2 md:py-1 px-4 md:px-3">RUN</button>
          <button onClick={onStep} className="btn-secondary text-xs py-2 md:py-1 px-4 md:px-3">STEP</button>
        </>
      )}
      <div className="ml-auto flex items-center gap-2">
        <span className="text-[10px] text-terminal-amber-dim font-mono">SPEED:</span>
        <select value={speed} onChange={(e) => onSpeedChange(e.target.value)} className="input-field text-xs py-1.5 md:py-0.5">
          <option value="slow">SLOW</option><option value="medium">MED</option><option value="fast">FAST</option><option value="manual">MANUAL</option>
        </select>
      </div>
    </div>
  );
}
