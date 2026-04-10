import React, { useState } from 'react';
import Toggle from '../shared/Toggle';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function TradingSchedule({ enabled, onToggle }) {
  const [schedule, setSchedule] = useState(DAYS.map((_, i) => ({ day_of_week: i, is_enabled: i < 5, windows: [{ start_time: '09:00', end_time: '17:00' }] })));
  const updateDay = (dayIdx, field, value) => { setSchedule((prev) => { const u = [...prev]; u[dayIdx] = { ...u[dayIdx], [field]: value }; return u; }); };
  const addWindow = (dayIdx) => { setSchedule((prev) => { const u = [...prev]; u[dayIdx] = { ...u[dayIdx], windows: [...u[dayIdx].windows, { start_time: '09:00', end_time: '17:00' }] }; return u; }); };
  const removeWindow = (dayIdx, winIdx) => { setSchedule((prev) => { const u = [...prev]; u[dayIdx] = { ...u[dayIdx], windows: u[dayIdx].windows.filter((_, i) => i !== winIdx) }; return u; }); };
  const updateWindow = (dayIdx, winIdx, field, value) => { setSchedule((prev) => { const u = [...prev]; const w = [...u[dayIdx].windows]; w[winIdx] = { ...w[winIdx], [field]: value }; u[dayIdx] = { ...u[dayIdx], windows: w }; return u; }); };
  return (
    <div className="card font-mono">
      <div className="flex items-center justify-between mb-4">
        <h3 className="panel-header">TRADING SCHEDULE</h3>
        <Toggle checked={enabled} onChange={onToggle} />
      </div>
      {enabled && (
        <div className="space-y-3">
          {schedule.map((day, dayIdx) => (
            <div key={dayIdx} className="border border-terminal-border-dim/50 p-3">
              <div className="flex items-center gap-3 mb-2">
                <input type="checkbox" checked={day.is_enabled} onChange={(e) => updateDay(dayIdx, 'is_enabled', e.target.checked)} className="border-terminal-border-dim" style={{ accentColor: '#D4A017' }} />
                <span className={`text-xs font-mono ${day.is_enabled ? 'text-terminal-amber' : 'text-terminal-amber-dim'}`}>{DAYS[dayIdx].toUpperCase()}</span>
                {day.is_enabled && (<button type="button" onClick={() => addWindow(dayIdx)} className="text-[10px] text-terminal-amber-bright hover:text-terminal-amber font-mono ml-auto">+ WINDOW</button>)}
              </div>
              {day.is_enabled && day.windows.map((win, winIdx) => (
                <div key={winIdx} className="flex items-center gap-2 ml-6 mb-1">
                  <input type="time" value={win.start_time} onChange={(e) => updateWindow(dayIdx, winIdx, 'start_time', e.target.value)} className="input-field text-xs py-0.5" />
                  <span className="text-xs text-terminal-amber-dim font-mono">TO</span>
                  <input type="time" value={win.end_time} onChange={(e) => updateWindow(dayIdx, winIdx, 'end_time', e.target.value)} className="input-field text-xs py-0.5" />
                  <button type="button" onClick={() => removeWindow(dayIdx, winIdx)} className="text-terminal-red-text hover:text-terminal-red-bright text-xs font-mono">[X]</button>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
