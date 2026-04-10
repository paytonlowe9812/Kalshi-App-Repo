import React, { useEffect, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import ApiKeyManager from './ApiKeyManager';
import ExportHistory from './ExportHistory';
import RiskControls from './RiskControls';
import TradingSchedule from './TradingSchedule';
import AppSettings from './AppSettings';
import ConfirmDialog from '../shared/ConfirmDialog';

export default function SettingsScreen() {
  const { firstLaunch, setPaperMode } = useAppStore();
  const [settings, setSettings] = useState({});
  const [showPanic, setShowPanic] = useState(false);
  const [dirty, setDirty] = useState(false);
  useEffect(() => { const f = async () => { const res = await fetch('/api/settings'); const data = await res.json(); setSettings(data); setPaperMode(data.paper_trading_mode === 'true'); }; f(); }, []);
  const updateSetting = (key, value) => { setSettings((p) => ({ ...p, [key]: value })); setDirty(true); if (key === 'paper_trading_mode') setPaperMode(value === 'true'); };
  const saveAll = async () => { await fetch('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ settings }) }); setDirty(false); };
  const handlePanic = async () => { await fetch('/api/settings/panic', { method: 'POST' }); };
  return (
    <div className="h-full overflow-y-auto relative">
      {dirty && (
        <div className="sticky top-0 z-10 flex justify-end px-4 py-2 bg-terminal-surface/90 backdrop-blur border-b border-terminal-border-dim">
          <button onClick={saveAll} className="btn-primary text-xs">SAVE ALL CONFIG</button>
        </div>
      )}
      <div className="max-w-3xl mx-auto px-3 md:px-4 py-4 md:py-6 space-y-4 md:space-y-6 pb-20 md:pb-6">
        <ApiKeyManager firstLaunch={firstLaunch} />
        <ExportHistory />
        <RiskControls settings={settings} onUpdate={updateSetting} onPanic={() => setShowPanic(true)} />
        <TradingSchedule enabled={settings.trading_schedule_enabled === 'true'} onToggle={(v) => updateSetting('trading_schedule_enabled', v ? 'true' : 'false')} />
        <AppSettings settings={settings} onUpdate={updateSetting} />
      </div>
      <ConfirmDialog open={showPanic} onClose={() => setShowPanic(false)} onConfirm={handlePanic} title="EMERGENCY STOP" message="This will close all open positions at market price and stop all running bots." confirmText="EMERGENCY STOP" danger />
    </div>
  );
}
